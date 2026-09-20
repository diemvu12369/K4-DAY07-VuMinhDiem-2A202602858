"""Benchmark harness for K4-L3B — nhóm DeltaX.

Chiến lược của Vũ Minh Điềm (Strategy Lead): HeadingChunker — chunk theo
tiêu đề/mục (##, ###) của văn bản chính sách gốc.

Đọc corpus data/shopee-return-refund/, chunk từng file, nạp vào EmbeddingStore,
chạy 5 benchmark query chung của nhóm qua search_with_filter(), in top-3 kèm
score và doc_id để đối chiếu với gold answer trong report/REPORT_NHOM.md.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from dotenv import load_dotenv

from src.chunking import FixedSizeChunker, HeadingChunker, RecursiveChunker, SentenceChunker
from src.embeddings import (
    EMBEDDING_PROVIDER_ENV,
    GEMINI_EMBEDDING_MODEL,
    LOCAL_EMBEDDING_MODEL,
    OPENAI_EMBEDDING_MODEL,
    GeminiEmbedder,
    LocalEmbedder,
    OpenAIEmbedder,
    _mock_embed,
)
from src.models import Document
from src.store import EmbeddingStore

CORPUS_DIR = Path("data/shopee-return-refund")

# Mỗi thành viên chỉ đổi DÒNG NÀY sang chiến lược của mình để so sánh công bằng.
# chunk_size=1000 (thay vì 500 mặc định): đo thực nghiệm cho 6/10 thay vì 5/10 —
# mục "Phương thức thanh toán..." (~900 ký tự) giờ lọt gọn 1 chunk thay vì bị
# RecursiveChunker chẻ vụn thành nhiều mảnh cùng điểm số (xem REPORT_NHOM.md mục 2).
CHUNKER = HeadingChunker(chunk_size=1000)
# CHUNKER = FixedSizeChunker(chunk_size=500, overlap=50)  # Phạm Xuân Quý
# CHUNKER = RecursiveChunker(chunk_size=500)               # Nguyễn Minh Thịnh
# CHUNKER = SentenceChunker(max_sentences_per_chunk=3)      # Nguyễn Hoàng Tuyên

QUERIES = [
    {
        "question": (
            "Với thực phẩm tươi sống và đông lạnh, người mua phải gửi yêu cầu "
            "Trả hàng/Hoàn tiền trong thời hạn bao lâu?"
        ),
        "gold_answer": (
            "Trong vòng 24 giờ kể từ khi đơn hàng được cập nhật trạng thái "
            "“Giao hàng thành công”, trừ trường hợp chưa nhận được hàng."
        ),
        "gold_doc_id": "buyer-return-conditions",
        "answer_fragment": "trong vòng 24 giờ kể từ lúc",
        "metadata_filter": None,
    },
    {
        "question": (
            "Shopee có hỗ trợ yêu cầu đổi hàng không, và người mua có thể làm gì "
            "nếu hàng nhận được có vấn đề?"
        ),
        "gold_answer": (
            "Shopee chưa hỗ trợ đổi hàng. Người mua có thể từ chối nhận khi đồng "
            "kiểm hoặc gửi yêu cầu Trả hàng/Hoàn tiền sau khi nhận hàng."
        ),
        "gold_doc_id": "buyer-return-conditions",
        "answer_fragment": "shopee hiện chưa hỗ trợ yêu cầu đổi hàng",
        "metadata_filter": None,
    },
    {
        "question": "Người mua có thể gửi yêu cầu Trả hàng/Hoàn tiền bằng những cách nào?",
        "gold_answer": (
            "Gửi trực tiếp tại trang đơn hàng hoặc gửi tại mục Trò Chuyện Với "
            "Shopee rồi chọn “Khiếu nại trả hàng hoàn tiền”."
        ),
        "gold_doc_id": "buyer-return-request-guide",
        "answer_fragment": "trò chuyện với shopee",
        "metadata_filter": None,
    },
    {
        "question": (
            "Sau khi Shopee chấp nhận hoàn tiền, tiền hoàn về thẻ tín dụng hoặc "
            "thẻ ghi nợ mất bao lâu?"
        ),
        "gold_answer": "Khoảng 7-14 ngày làm việc, tùy theo ngân hàng.",
        "gold_doc_id": "buyer-refund-timeline",
        "answer_fragment": "7 - 14 ngày làm việc",
        "metadata_filter": None,
    },
    {
        "question": "Một yêu cầu hoàn tiền cần được phản hồi trong bao lâu?",
        "gold_answer": (
            "Đối với Người Bán, yêu cầu “Hoàn Tiền Ngay” phải được phản "
            "hồi hoặc khiếu nại trong vòng 02 ngày lịch. Nếu không phản hồi, Người "
            "Bán được xem là đồng ý với quyết định của Shopee."
        ),
        "gold_doc_id": "seller-mall-return-obligations",
        "answer_fragment": "trong vòng 02 ngày lịch kể từ ngày nhận được yêu cầu",
        # Bắt buộc: không lọc thì buyer-refund-timeline / buyer-return-request-guide
        # (cũng nói về "hoàn tiền") có thể lấn top-3 dù không phải đối tượng seller.
        "metadata_filter": {"audience": "seller"},
    },
]


def parse_markdown(path: Path) -> tuple[dict, str]:
    """Split a corpus .md file into (frontmatter metadata, body content)."""
    text = path.read_text(encoding="utf-8")
    _, front_matter, body = text.split("---", 2)
    metadata: dict[str, str] = {}
    for line in front_matter.strip().splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip().strip('"')
        metadata[key.strip()] = value
    return metadata, body.strip()


def load_embedder():
    load_dotenv(override=False)
    provider = os.getenv(EMBEDDING_PROVIDER_ENV, "mock").strip().lower()
    try:
        if provider == "local":
            return LocalEmbedder(model_name=os.getenv("LOCAL_EMBEDDING_MODEL", LOCAL_EMBEDDING_MODEL))
        if provider == "openai":
            return OpenAIEmbedder(model_name=os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL))
        if provider == "gemini":
            return GeminiEmbedder(model_name=os.getenv("GEMINI_EMBEDDING_MODEL", GEMINI_EMBEDDING_MODEL))
    except Exception as error:  # noqa: BLE001 - fall back to mock, same as main.py
        print(f"Could not initialize '{provider}' embedder ({error}); falling back to mock.")
    return _mock_embed


def build_documents() -> list[Document]:
    documents: list[Document] = []
    for path in sorted(CORPUS_DIR.glob("*.md")):
        metadata, body = parse_markdown(path)
        chunks = CHUNKER.chunk(body)
        for index, chunk_text in enumerate(chunks):
            documents.append(
                Document(
                    id=f"{path.stem}#{index}",
                    content=chunk_text,
                    metadata={**metadata, "doc_id": path.stem},
                )
            )
    return documents


def contains_answer_fragment(text: str, fragment: str) -> bool:
    """Content-level check: does this chunk contain the literal string that answers the query?

    docs/SCORING.md rồi day7-lab-data-foundations.md mục "Chấm hai mức" cảnh báo
    kiểm doc_id không thôi sẽ thổi phồng kết quả — chunk đúng file vẫn có thể
    không chứa số liệu/đáp án. Kiểm chuỗi đặc trưng (đã xác nhận có thật trong
    nguồn) mới phản ánh đúng liệu top-k có "trả lời được" hay không.
    """
    needle = re.sub(r"\s+", " ", fragment.lower())
    haystack = re.sub(r"\s+", " ", text.lower())
    return needle in haystack


def main() -> None:
    embedder = load_embedder()
    print(f"Embedding backend: {getattr(embedder, '_backend_name', embedder.__class__.__name__)}")
    print(f"Chunking strategy: {CHUNKER.__class__.__name__}")

    store = EmbeddingStore(collection_name="bench", embedding_fn=embedder)
    documents = build_documents()
    store.add_documents(documents)
    print(f"Loaded {len(documents)} chunks from {len(list(CORPUS_DIR.glob('*.md')))} files in {CORPUS_DIR}\n")

    for i, item in enumerate(QUERIES, start=1):
        print(f"=== Query {i}: {item['question']}")
        print(f"Gold answer : {item['gold_answer']}")
        print(f"Gold doc_id : {item['gold_doc_id']}")
        print(f"Filter      : {item['metadata_filter']}")

        results = store.search_with_filter(item["question"], top_k=3, metadata_filter=item["metadata_filter"])
        for rank, result in enumerate(results, start=1):
            doc_id = result["metadata"].get("doc_id")
            hit_gold_doc = "<-- gold doc" if doc_id == item["gold_doc_id"] else ""
            has_answer = contains_answer_fragment(result["content"], item["answer_fragment"])
            print(
                f"  top-{rank} score={result['score']:.3f} doc_id={doc_id} "
                f"chua_dap_an={has_answer} {hit_gold_doc}"
            )
            preview = result["content"][:160].replace("\n", " ")
            print(f"          {preview}...")

        if item["metadata_filter"]:
            unfiltered = store.search(item["question"], top_k=3)
            print("  --- A/B: cùng câu hỏi KHÔNG dùng metadata_filter ---")
            for rank, result in enumerate(unfiltered, start=1):
                doc_id = result["metadata"].get("doc_id")
                print(f"  no-filter top-{rank} score={result['score']:.3f} doc_id={doc_id}")
        print()


if __name__ == "__main__":
    main()
