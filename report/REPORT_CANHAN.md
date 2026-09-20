# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Vũ Minh Điềm
**MSSV:** 2A202602858
**Nhóm:** DeltaX
**Vai trò trong nhóm:** Strategy Lead — chiến lược chunking theo heading/mục
**Ngày:** 2026-09-20

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Similarity cao (gần 1) nghĩa là hai vector embedding trỏ gần như cùng một hướng trong không gian nhiều chiều, tức hai đoạn văn bản mang **ý nghĩa/ngữ cảnh gần nhau**, kể cả khi từ vựng dùng khác nhau. Similarity gần 0 nghĩa là không liên quan, gần -1 nghĩa là đối lập nghĩa.

**Ví dụ có độ tương tự CAO** (đo bằng `LocalEmbedder` + `compute_similarity`, score = 0.747):
- Câu A: "Người mua có thể trả lại sản phẩm nếu không hài lòng."
- Câu B: "Khách hàng được hoàn trả hàng hoá khi cảm thấy chưa ưng ý."
- Tại sao tương đồng: hai câu dùng từ vựng gần như khác hoàn toàn ("người mua"/"khách hàng", "trả lại"/"hoàn trả", "không hài lòng"/"chưa ưng ý") nhưng cùng diễn đạt một chính sách đổi trả — chứng minh embedding học được ngữ nghĩa chứ không so khớp từ.

**Ví dụ có độ tương tự THẤP** (score = -0.081):
- Câu A: "Người mua có thể trả lại sản phẩm nếu không hài lòng."
- Câu B: "Hôm nay thời tiết rất đẹp và trong xanh."
- Tại sao khác: hai câu thuộc hai chủ đề hoàn toàn không liên quan (chính sách thương mại vs. thời tiết), không chia sẻ khái niệm nào.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Cosine chỉ đo **góc/hướng** giữa hai vector nên không bị ảnh hưởng bởi độ dài văn bản (câu dài tự nhiên có vector "to" hơn câu ngắn cùng nghĩa); Euclidean đo khoảng cách tuyệt đối nên hai câu cùng nghĩa nhưng độ dài khác nhau vẫn có thể bị coi là "xa nhau". Vì `EmbeddingStore` đã chuẩn hoá `||v||=1`, dot product cũng chính là cosine, nên `search()` dùng dot product cho gọn mà không mất tính đúng đắn.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> Công thức: `ceil((length - overlap) / (chunk_size - overlap))`
> = `ceil((10000 - 50) / (500 - 50))` = `ceil(9950 / 450)` = `ceil(22.11)` = **23 chunks**
> Đã kiểm lại bằng code thật: `len(FixedSizeChunker(chunk_size=500, overlap=50).chunk('a'*10000))` → `23`. Khớp công thức.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> `ceil((10000-100)/(500-100)) = ceil(9900/400) = 25 chunks` (đã kiểm lại bằng code, đúng 25) — nhiều hơn 2 chunk so với overlap=50, vì mỗi bước trượt (`step = chunk_size - overlap`) ngắn lại (450 → 400 ký tự) nên cần nhiều bước hơn để phủ hết văn bản. Overlap lớn hơn tốn thêm chunk (dữ liệu trùng lặp nhiều hơn) nhưng giảm rủi ro một thông tin quan trọng nằm đúng ranh giới cắt bị chia đôi và mất ngữ cảnh ở cả hai chunk — với văn bản chính sách chứa số liệu/mốc thời gian ngắn (ví dụ "24 giờ", "02 ngày lịch"), mất một câu do cắt ngang là rất dễ làm sai câu trả lời.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Dùng `re.split(r"(?<=[.!?])\s+|(?<=\.)\n", text)` — lookbehind giữ nguyên dấu câu ở cuối câu trước thay vì nuốt mất nó (nếu tách bằng `[.!?]\s+` thông thường, dấu câu sẽ bị `split` ăn mất và mọi câu bị cụt). Sau đó gom tối đa `max_sentences_per_chunk` câu liên tiếp thành một chunk bằng cách lặp theo bước nhảy. Edge case tôi biết mình **chưa** xử lý: viết tắt (`TS.`, `v.v.`) và số thập phân (`7.5%`) sẽ bị nhận nhầm là kết thúc câu vì regex chỉ dựa vào dấu chấm, không có danh sách từ viết tắt.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Thuật toán đệ quy hai chiều: (1) *xuống sâu* — thử tách theo separator ưu tiên `["\n\n", "\n", ". ", " ", ""]`, mảnh nào sau khi tách vẫn dài hơn `chunk_size` thì gọi đệ quy `_split` với danh sách separator còn lại; (2) *gom lên* — nối các mảnh nhỏ liền kề bằng buffer cho tới sát `chunk_size`, tránh sinh hàng loạt chunk vụn vài ký tự. Base case có 3 nhánh: mảnh đã đủ ngắn (`<= chunk_size`) trả về nguyên mảnh; hết separator (`remaining_separators == []`) hoặc separator hiện tại là chuỗi rỗng thì cắt cứng theo `chunk_size` (`_hard_cut`) — đây chính là nhánh `test_empty_separators_falls_back_gracefully` kiểm tra.

**`HeadingChunker.chunk` (chiến lược riêng của tôi — Strategy Lead)** — hướng tiếp cận:
> Văn bản chính sách Shopee đã được tác giả chia sẵn theo mục (`## 1. Nguyên tắc chung`, `### 1.2. Thời gian tối đa...`), mỗi mục là một đơn vị ngữ nghĩa trọn vẹn. Tôi dùng regex `^(#{1,6})\s+.*$` (multiline) để tìm mọi dòng heading, cắt văn bản thành các đoạn `(heading, nội_dung_mục)` theo vị trí các heading liền kề. Mục nào ngắn hơn `chunk_size` giữ nguyên làm một chunk; mục dài hơn được hạ xuống `RecursiveChunker` để cắt tiếp, và **heading được gắn lại vào đầu mỗi mảnh con** (`f"{heading_line}\n{sub_chunk}"`) nếu mảnh đó chưa tự chứa heading — nếu không làm bước này, mảnh thứ hai trở đi của một mục dài (ví dụ bảng "Phương thức thanh toán và thời gian hoàn tiền" liệt kê nhiều dòng) sẽ mất ngữ cảnh "đây là mục nói về cái gì".

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> `add_documents` không tự chunk — mỗi `Document` truyền vào tương ứng đúng một record trong `self._store` (list dict), qua `_make_record` (copy `metadata`, luôn set `metadata["doc_id"]`, và embed `content` bằng `self._embedding_fn`). `search` gọi `_search_records(query, self._store, top_k)`: embed câu hỏi, tính dot product (đã chuẩn hoá = cosine) với từng record bằng `_dot` tái sử dụng từ `chunking.py`, sort giảm dần theo score và cắt `top_k`.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> Lọc **trước khi** search: xây danh sách `candidates` chỉ gồm record khớp mọi cặp key/value trong `metadata_filter`, rồi mới gọi `_search_records` trên tập đã lọc đó (dùng chung hàm với `search`, nên `test_no_filter_returns_all_candidates` tự động đúng). Lọc sau-rồi-mới-cắt-top-k sẽ sai vì k slot có thể đã bị tài liệu không khớp chiếm hết trước khi lọc. `delete_document` duyệt và giữ lại mọi record có `metadata["doc_id"] != doc_id`, trả về `True` nếu kích thước store giảm.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Ba nhịp: (1) nếu store rỗng trả thông báo ngay, không gọi LLM; (2) truy xuất top-k qua `search` hoặc `search_with_filter` (nếu có `metadata_filter`); (3) dựng prompt đánh số từng chunk `[1] [2] [3]` kèm `doc_id` nguồn, yêu cầu LLM **chỉ dùng ngữ cảnh được cung cấp**, nói rõ "không tìm thấy" nếu ngữ cảnh không đủ, và trích dẫn số chunk khi trả lời — phục vụ tiêu chí Source Traceability trong `docs/EVALUATION.md`.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
============================= test session starts =============================
platform win32 -- Python 3.13.12, pytest-9.1.1, pluggy-1.5.0
rootdir: C:\Users\Acer\Documents\GitHub\K4-L3B-Data-Foundations
collecting ... collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED [  2%]
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED [  4%]
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED [  7%]
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED [  9%]
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED [ 11%]
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED [ 14%]
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED [ 16%]
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED [ 19%]
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED [ 21%]
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED   [ 23%]
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED [ 26%]
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED [ 28%]
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED [ 30%]
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED    [ 33%]
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED [ 35%]
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED [ 38%]
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED [ 40%]
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED [ 42%]
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED   [ 45%]
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED [ 47%]
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED [ 50%]
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED [ 52%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED [ 54%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED [ 57%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED [ 59%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED [ 61%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED [ 64%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED [ 66%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED [ 69%]
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED [ 71%]
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED [ 73%]
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED [ 76%]
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED [ 78%]
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED [ 80%]
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED [ 83%]
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED [ 85%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED [ 88%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED [ 90%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED [ 92%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED [ 95%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED [ 97%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED [100%]

============================= 42 passed in 0.14s ==============================
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

Đo bằng `LocalEmbedder` (`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, đa ngữ, không dùng Mock vì Mock không mang ngữ nghĩa) + `compute_similarity`.

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | "Người mua có thể trả lại sản phẩm nếu không hài lòng." | "Khách hàng được hoàn trả hàng hoá khi cảm thấy chưa ưng ý." | cao | 0.747 | Đúng |
| 2 | "Thời gian hoàn tiền là bao lâu?" | "Mất bao lâu để nhận lại tiền sau khi trả hàng?" | cao | 0.577 | Đúng |
| 3 | "Người mua có thể trả lại sản phẩm nếu không hài lòng." | "Hôm nay thời tiết rất đẹp và trong xanh." | thấp | -0.081 | Đúng |
| 4 | "Người bán phải phản hồi khiếu nại trong 2 ngày." | "Con mèo đang ngủ trên ghế sofa." | thấp | -0.070 | Đúng |
| 5 | "Đổi trả hàng lỗi trong vòng 15 ngày." | "Sản phẩm bị lỗi được chấp nhận trả lại trong nửa tháng." | cao | 0.468 | Một phần |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Cặp 5 bất ngờ nhất: tôi dự đoán "cao" vì hai câu diễn đạt cùng một chính sách (15 ngày ≈ nửa tháng), nhưng điểm thực tế (0.468) thấp hơn hẳn cặp 1 (0.747) dù cùng là diễn giải lại. Điều này cho thấy embedding câu bắt tốt sự tương đồng **từ vựng/cấu trúc gần nghĩa** (đồng nghĩa trực tiếp) nhưng bắt yếu hơn phép **suy luận số học ẩn** ("15 ngày" = "nửa tháng" đòi hỏi quy đổi đơn vị, không phải khớp nghĩa từ-với-từ) — một giới hạn quan trọng cần nhớ khi dùng embedding để retrieval các câu hỏi có số liệu/mốc thời gian như trong corpus chính sách Shopee.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

**Chiến lược:** `HeadingChunker(chunk_size=1000)` — chunk theo tiêu đề/mục Markdown (`bench.py`), chạy trên corpus `data/shopee-return-refund/` (6 tài liệu, 55 chunk), embedder thật `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`. Chi tiết đầy đủ: `ket_qua_benchmark.txt`.

> **Ba vòng thử nghiệm, đo lại từng lần:**
> 1. `chunk_size=500`, không filter cho Q1-Q4 → 5/10.
> 2. `chunk_size=1000`, không filter cho Q1-Q4 → 6/10 (mục bảng dài không còn bị chẻ vụn, sửa Q4).
> 3. `chunk_size=1000` + `metadata_filter={"audience":"buyer"}` cho Q1-Q4 (thống nhất với `bench.py` chuẩn của nhóm — Quý phát hiện thiếu bước này) → **7/10**: loại hẳn `seller-mall-return-obligations` khỏi ứng viên của Q1-Q4 nên Q2 từ "đúng nhưng lạc xuống top-3" thành **đúng top-1**.

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Điểm theo SCORING.md |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Thời hạn gửi yêu cầu Trả hàng/Hoàn tiền cho thực phẩm tươi sống/đông lạnh? (filter `buyer`) | `buyer-return-conditions` — mục "1.2. Thời gian tối đa..." chứa đúng "24 giờ" | 0.708 | Có, đúng và chứa đáp án (top-1) | 2đ |
| 2 | Shopee có hỗ trợ đổi hàng không? (filter `buyer`) | `buyer-return-conditions` — mục "1.1. Nguyên tắc chung" chứa đúng "Shopee hiện chưa hỗ trợ yêu cầu đổi hàng" | 0.642 | Có, đúng và chứa đáp án (top-1) | 2đ |
| 3 | Người mua gửi yêu cầu bằng cách nào? (filter `buyer`) | `buyer-refund-timeline` (SAI tài liệu ở top-1, vẫn lọt vì cùng audience buyer) — đúng tài liệu (`buyer-return-request-guide`) ở top-2 nhưng vẫn sai mục | 0.695 | Đúng tài liệu (top-2), sai mục | 0đ |
| 4 | Hoàn tiền về thẻ tín dụng/ghi nợ mất bao lâu? (filter `buyer`) | `buyer-refund-timeline` — mục bảng phương thức hoàn tiền nguyên vẹn trong 1 chunk, chứa đúng "7-14 ngày làm việc" | 0.702 | Có, đúng và chứa đáp án (top-1) | 2đ |
| 5 | Yêu cầu hoàn tiền cần phản hồi trong bao lâu? (filter `seller`) | `seller-rights-and-duties` (SAI tài liệu ở top-1) — đáp án đúng ở top-2 (`seller-mall-return-obligations`, chứa "02 ngày lịch") | 0.490 | Đúng nhưng chỉ ở top-2 | 1đ |

**Tổng điểm benchmark theo `docs/SCORING.md`: 7/10** (2+2+0+2+1).

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 5 / 5 (đúng tài liệu gold luôn xuất hiện đâu đó trong top-3) — và **3/5** câu (Q1, Q2, Q4) đạt đủ 2 điểm (top-1 + chứa đáp án) sau khi thêm filter đúng đối tượng cho từng câu. Q3 là điểm yếu còn lại: đúng tài liệu ở top-2 nhưng chunk cụ thể không chứa câu trả lời, vì đoạn hướng dẫn "Trò Chuyện Với Shopee" quá ngắn/mang tính thao tác nên embedding không liên hệ tốt với câu hỏi tự nhiên (đã trace: chunk đó xếp hạng rất thấp trong toàn corpus, không sửa được bằng filter hay chunk_size).

**A/B bắt buộc (câu 5, có/không `metadata_filter={"audience":"seller"}`):** không lọc, top-3 đổi hoàn toàn thành 3 chunk của tài liệu buyer (`buyer-return-conditions`, `buyer-return-request-guide`) — chứng minh rõ ràng filter theo `audience` là bắt buộc để không lẫn giữa hai đối tượng, đúng ràng buộc #2 của K4_VARIANT.md.

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> *(điền sau buổi demo của nhóm DeltaX — so sánh HeadingChunker của tôi với FixedSize (Quý), Recursive (Thịnh), Sentence (Tuyên) trên cùng 5 câu hỏi)*

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 8 / 10 |
| **Tổng phần cá nhân** | **58 / 60** |
