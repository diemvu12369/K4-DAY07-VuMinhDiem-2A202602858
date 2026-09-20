# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** DeltaX
**Thành viên:** Phạm Xuân Quý (2A202602745), Nguyễn Minh Thịnh (2A202602556), Vũ Minh Điềm (2A202602858), Nguyễn Hoàng Tuyên (2A202602439)
**Ngày:** 2026-09-19

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Quy trình Trả hàng/Hoàn tiền trên Shopee Việt Nam dành cho Người mua và Người bán.

**Tại sao nhóm chọn chủ đề này?**
> Chủ đề có nhiều điều kiện, ngoại lệ, thời hạn và quy trình cụ thể nên phù hợp để đánh giá chất lượng retrieval. Việc có tài liệu dành cho cả người mua và người bán cũng giúp nhóm kiểm chứng tác dụng của metadata filtering, đặc biệt khi cùng một câu hỏi có thể truy xuất nhầm mốc thời gian của đối tượng khác.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | Quy định chung về trả hàng và hoàn tiền | [Shopee #188931](https://help.shopee.vn/portal/4/article/188931) | 2026-09-19 / `not-stated` | 6.050 | `audience: buyer`, `category: return-conditions`, `language: vi` |
| 2 | Hướng dẫn gửi yêu cầu trả hàng và hoàn tiền | [Shopee #79233](https://help.shopee.vn/portal/4/article/79233) | 2026-09-19 / `not-stated` | 2.272 | `audience: buyer`, `category: return-request-process`, `language: vi` |
| 3 | Quy trình xử lý yêu cầu trả hàng và hoàn tiền | [Shopee #190242](https://help.shopee.vn/portal/4/article/190242) | 2026-09-19 / `not-stated` | 7.846 | `audience: buyer`, `category: dispute-process`, `language: vi` |
| 4 | Thời gian nhận tiền hoàn và cách kiểm tra | [Shopee #189473](https://help.shopee.vn/portal/4/article/189473) | 2026-09-19 / `not-stated` | 3.632 | `audience: buyer`, `category: refund-timeline`, `language: vi` |
| 5 | Nghĩa vụ người bán Shopee Mall khi xử lý trả hàng | [Shopee #77262](https://help.shopee.vn/portal/4/article/77262) | 2026-09-19 / `effective-2026-05-08` | 4.101 | `audience: seller`, `category: seller-return-obligations`, `language: vi` |
| 6 | Quyền và nghĩa vụ người bán trên Shopee | [Shopee #77245](https://help.shopee.vn/portal/4/article/77245) | 2026-09-19 / `updated-2025-01-03` | 3.822 | `audience: seller`, `category: seller-rights-and-duties`, `language: vi` |

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| `doc_id` | String duy nhất | `buyer-return-conditions` | Liên kết chunk với tài liệu nguồn và hỗ trợ xóa toàn bộ chunk của một tài liệu. |
| `title` | String | `Quy định chung về trả hàng và hoàn tiền` | Giúp nhận diện tài liệu và hiển thị nguồn dễ hiểu trong kết quả. |
| `source_url` | URL | `https://help.shopee.vn/portal/4/article/188931` | Cho phép truy vết và kiểm chứng nội dung tại nguồn chính thức. |
| `retrieved_at` | Ngày `YYYY-MM-DD` | `2026-09-19` | Cho biết thời điểm nhóm thu thập dữ liệu và hỗ trợ đánh giá độ mới. |
| `document_version` | String | `effective-2026-05-08` | Phân biệt phiên bản hoặc ngày hiệu lực của chính sách; dùng `not-stated` khi nguồn không nêu. |
| `audience` | Enum | `buyer`, `seller` | Lọc đúng tài liệu dành cho người mua hoặc người bán, tránh nhầm điều kiện và thời hạn. |
| `category` | String | `refund-timeline` | Thu hẹp tìm kiếm theo loại thông tin như điều kiện, quy trình, thời hạn hoặc nghĩa vụ. |
| `language` | String | `vi` | Hỗ trợ lọc theo ngôn ngữ khi corpus được mở rộng. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare()` trên 2-3 tài liệu:

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| `buyer-return-conditions` | FixedSizeChunker (`fixed_size`) | 14 | 478,57 | Trung bình: kích thước ổn định nhưng có thể cắt giữa câu hoặc giữa một quy định. |
| `buyer-return-conditions` | SentenceChunker (`by_sentences`) | 9 | 667,11 | Khá tốt: giữ trọn câu, nhưng câu pháp lý dài làm chunk vượt ngưỡng 500 ký tự. |
| `buyer-return-conditions` | RecursiveChunker (`recursive`) | 14 | 428,43 | Tốt: ưu tiên ranh giới đoạn và dòng trước khi tách nhỏ hơn. |
| `buyer-return-request-guide` | FixedSizeChunker (`fixed_size`) | 5 | 494,40 | Trung bình: dễ kiểm soát số chunk nhưng đôi lúc tách rời bước hướng dẫn. |
| `buyer-return-request-guide` | SentenceChunker (`by_sentences`) | 7 | 321,14 | Tốt: các bước ngắn và câu hướng dẫn thường còn nguyên vẹn. |
| `buyer-return-request-guide` | RecursiveChunker (`recursive`) | 5 | 450,20 | Tốt: giữ được các đoạn hướng dẫn liền nhau và kích thước tương đối đều. |
| `seller-mall-return-obligations` | FixedSizeChunker (`fixed_size`) | 10 | 455,10 | Trung bình: có overlap hỗ trợ biên nhưng vẫn có thể cắt giữa nghĩa vụ. |
| `seller-mall-return-obligations` | SentenceChunker (`by_sentences`) | 7 | 583,00 | Khá tốt: giữ trọn câu, đổi lại một số chunk dài hơn ngưỡng. |
| `seller-mall-return-obligations` | RecursiveChunker (`recursive`) | 12 | 339,92 | Tốt: bám theo cấu trúc đoạn và dòng của tài liệu quy định. |

Số liệu được đo trên phần thân tài liệu sau khi bỏ frontmatter, cùng tham số mục tiêu `chunk_size=500`. SentenceChunker gom tối đa 3 câu nên có thể tạo chunk dài hơn 500 ký tự khi bản thân câu nguồn dài.

### Chiến lược của từng thành viên

> Mỗi thành viên sử dụng một chiến lược riêng trên cùng corpus, embedding và bộ câu hỏi benchmark.

**Thành viên 1 — Phạm Xuân Quý**
- **Loại chiến lược:** FixedSizeChunker (`chunk_size=1000`, `overlap=500`)
- **Mô tả & lý do chọn cho chủ đề này:** Chiến lược tạo kích thước đầu vào ổn định và dễ dùng làm mốc so sánh với ba chiến lược còn lại. Thử nghiệm tham số cho thấy cấu hình 1000/500 đạt 5/10, tốt hơn cấu hình baseline 500/50 đạt 2/10; overlap lớn giúp giữ các dòng trong bảng và quy định nằm gần ranh giới chunk. Trên 6 tài liệu, cấu hình cuối tạo 53 chunk.
- **Code snippet (nếu custom):** Không áp dụng; sử dụng `FixedSizeChunker` có sẵn trong `src/chunking.py`.

**Thành viên 2 — Nguyễn Minh Thịnh (2A202602556)**
- **Loại chiến lược:** RecursiveChunker (`chunk_size=1000`)
- **Mô tả & lý do chọn:** Ưu tiên tách theo đoạn, dòng, câu rồi từ, nhờ đó ít cắt ngang đơn vị ngữ nghĩa hơn FixedSize. Mảnh quá dài tiếp tục được chia nhỏ và các mảnh ngắn được gom lại gần ngưỡng 1000 ký tự; chiến lược tạo 32 chunk trên 6 tài liệu. Kết quả đã được xác minh trên repo của Thịnh với embedding thật `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`: 4/10.
- **Code snippet (nếu custom):** Không áp dụng; sử dụng `RecursiveChunker` trong `src/chunking.py`.

**Thành viên 3 — Vũ Minh Điềm (2A202602858)**
- **Loại chiến lược:** Custom HeadingChunker (`chunk_size=1000`)
- **Mô tả & lý do chọn:** Các tài liệu chính sách được biên soạn theo heading, nên mỗi section thường là một đơn vị ngữ nghĩa hoàn chỉnh. Section dài hơn 1000 ký tự được chia tiếp bằng RecursiveChunker và tiêu đề section được gắn vào từng mảnh con; chiến lược tạo 55 chunk. Kết quả đã được xác minh trên repo của Điềm với embedding thật `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`: 7/10.
- **Code snippet (nếu custom):**
```python
sections = re.split(r"(?m)(?=^#{1,6}\s+)", text.strip())
for section in sections:
    if len(section) <= chunk_size:
        chunks.append(section.strip())
    else:
        heading, _, body = section.partition("\n")
        for piece in RecursiveChunker(chunk_size=chunk_size - len(heading) - 1).chunk(body):
            chunks.append(f"{heading}\n{piece}".strip())
```

**Thành viên 4 — Nguyễn Hoàng Tuyên (2A202602439)**
- **Loại chiến lược:** SentenceChunker (`max_sentences_per_chunk=3`)
- **Mô tả & lý do chọn:** Gom các câu hoàn chỉnh giúp hạn chế cắt mất dấu câu và giữ nội dung dễ đọc. Tuyên chạy cấu hình SentenceChunker trên cùng corpus, cùng 5 query và embedding `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`; kết quả tạo 46 chunk, đạt **3/10** (truy xuất đúng tài liệu 4/5 câu, có bằng chứng trả lời trong top-3 ở 2/5 câu). Các câu pháp lý dài hoặc thông tin nằm ở nhiều mục vẫn có thể khiến chunk đúng không lọt top-3.
- **Code snippet (nếu custom):** Không áp dụng; sử dụng `SentenceChunker` trong `src/chunking.py`.

### So Sánh Giữa Các Thành Viên

| Thành viên | Chiến lược (Strategy) | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Phạm Xuân Quý | FixedSizeChunker (1000/500) | 5/10 — đã xác minh | Kích thước ổn định; overlap lớn giữ được bảng thời gian hoàn tiền và thông tin ở biên. | Có thể trộn nhiều ý trong chunk và trả đúng tài liệu nhưng sai mục. |
| Nguyễn Minh Thịnh | RecursiveChunker (1000) | 4/10 — đã xác minh | Giữ ranh giới đoạn/câu tốt hơn và dùng ít chunk nhất (32). | Không có overlap; một số bằng chứng ở biên chỉ có một cơ hội lọt top-3. |
| Vũ Minh Điềm | HeadingChunker (1000) | 7/10 — đã xác minh | Heading cung cấp ngữ cảnh chủ đề; điều khoản và tiêu đề thường đi cùng nhau. | Các câu hỏi cần tổng hợp nhiều section, như hai cách gửi yêu cầu, vẫn có thể thất bại. |
| Nguyễn Hoàng Tuyên | SentenceChunker (3 câu/chunk) | 3/10 — Tuyên đã chạy và xác minh | Giữ nguyên câu và dấu câu; chunk dễ đọc. | Câu pháp lý dài tạo chunk lớn, trong khi thông tin ở nhiều section khó được gom đủ vào top-3. |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> Trong các lượt chạy do từng thành viên thực hiện và đã xác minh trên cùng corpus, HeadingChunker của Điềm tốt nhất với **7/10**, cao hơn FixedSize của Quý (**5/10**), Recursive của Thịnh (**4/10**) và SentenceChunker của Tuyên (**3/10**). Cấu trúc heading của tài liệu Shopee đã thể hiện ranh giới ngữ nghĩa do người biên soạn đặt ra; giữ tiêu đề cùng nội dung giúp embedding phân biệt đúng điều khoản, đặc biệt ở các câu hỏi về thời hạn và nghĩa vụ.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy.

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | Với thực phẩm tươi sống và đông lạnh, người mua phải gửi yêu cầu Trả hàng/Hoàn tiền trong thời hạn bao lâu? | Trong vòng **24 giờ** kể từ khi đơn hàng được cập nhật trạng thái “Giao hàng thành công”, trừ trường hợp khiếu nại với lý do chưa nhận được hàng. | `buyer-return-conditions` — mục “Thời gian tối đa để gửi yêu cầu” |
| 2 | Shopee có hỗ trợ yêu cầu đổi hàng không, và người mua có thể làm gì nếu hàng nhận được có vấn đề? | Shopee hiện chưa hỗ trợ yêu cầu đổi hàng. Nếu hàng khác mô tả, hư hỏng hoặc có vấn đề, người mua có thể từ chối nhận khi đồng kiểm đối với đơn đủ điều kiện, hoặc gửi yêu cầu Trả hàng/Hoàn tiền sau khi nhận hàng. | `buyer-return-conditions` — mục “Nguyên tắc chung” |
| 3 | Người mua có thể gửi yêu cầu Trả hàng/Hoàn tiền bằng những cách nào? | Có hai cách: gửi trực tiếp tại trang đơn hàng, hoặc gửi tại mục **Trò Chuyện Với Shopee** rồi chọn **Khiếu nại trả hàng hoàn tiền**. | `buyer-return-request-guide` — mục “Cách 1” và “Cách 2” |
| 4 | Sau khi Shopee chấp nhận hoàn tiền, tiền hoàn về thẻ tín dụng hoặc thẻ ghi nợ mất bao lâu? | Tiền được hoàn về đúng thẻ tín dụng/ghi nợ đã sử dụng trong khoảng **7–14 ngày làm việc**, tùy ngân hàng. | `buyer-refund-timeline` — mục “Phương thức thanh toán và thời gian hoàn tiền” |
| 5 | Một yêu cầu hoàn tiền cần được phản hồi trong bao lâu? | Với tài liệu dành cho Người Bán, Người Bán phải phản hồi hoặc khiếu nại yêu cầu “Hoàn Tiền Ngay” trong vòng **02 ngày lịch** kể từ khi nhận được yêu cầu. Nếu không phản hồi, Người Bán được xem là đã đồng ý với quyết định của Shopee. | `seller-mall-return-obligations` — mục “Phản hồi yêu cầu Hoàn Tiền Ngay” |

> Query 1–4 được chạy với `metadata_filter={"audience": "buyer"}`, vì cả bốn câu đều hỏi về quy trình của người mua; bộ lọc này loại tài liệu người bán khỏi ứng viên, tránh các mốc thời gian của người bán chen vào top-3.
>
> Query 5 được chạy với `metadata_filter={"audience": "seller"}`. Câu hỏi cố ý không nêu rõ đối tượng; nếu không lọc, các tài liệu dành cho người mua có mốc 3–5 ngày và 1–14 ngày có thể chiếm top-k, tạo ra một đáp án khác.

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | Thời hạn cho thực phẩm tươi sống/đông lạnh | FixedSize, Heading và Sentence | Có — top-1 | Cả ba đều lấy đúng chunk chứa mốc 24 giờ và đạt 2 điểm. |
| 2 | Có hỗ trợ đổi hàng không? | Recursive và Heading | Có — top-1 | Hai chiến lược giữ trọn mục “Nguyên tắc chung” và đạt 2 điểm. |
| 3 | Hai cách gửi yêu cầu | Chưa chiến lược nào đạt | Không | Cách 1 và Cách 2 nằm ở các section khác nhau; không chiến lược nào đưa đủ bằng chứng vào top-3. |
| 4 | Thời gian hoàn về thẻ tín dụng/ghi nợ | FixedSize và Heading | Có — top-1 | Bảng phương thức thanh toán chứa đúng mốc 7–14 ngày, đạt 2 điểm. |
| 5 | Thời hạn phản hồi yêu cầu hoàn tiền | Recursive và Heading | Có — top-2 | Sau khi lọc `audience=seller`, đoạn “Hoàn Tiền Ngay” xuất hiện ở top-2, đạt 1 điểm. |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> Có, rõ nhất ở câu 5. Khi không lọc, cả ba kết quả top-3 đều nghiêng về tài liệu người mua; khi lọc `audience=seller`, cả ba kết quả chuyển sang tài liệu người bán. Tuy vậy, filter chỉ tăng độ chính xác về đối tượng chứ chưa bảo đảm đúng mục: FixedSize vẫn bỏ lỡ đoạn “Hoàn Tiền Ngay” có mốc 02 ngày trong top-3.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
> - Không thể chỉ chấm theo `doc_id`: FixedSize lấy đúng tài liệu ở 4/5 câu nhưng chỉ có bằng chứng trả lời thật ở 3/5 câu.
> - Tăng kích thước/overlap từ baseline 500/50 lên 1000/500 cải thiện điểm theo nội dung từ 2/10 lên 5/10, nhưng cũng tạo các chunk chứa nhiều mốc thời gian cạnh tranh nhau.
> - Metadata filter loại đúng đối tượng, nhưng vẫn cần chunking theo heading hoặc reranking để chọn đúng điều khoản trong tài liệu.

**Failure case cụ thể — câu 5:**
> Với câu “Một yêu cầu hoàn tiền cần được phản hồi trong bao lâu?”, filter `audience=seller` đã loại tài liệu người mua nhưng top-3 lần lượt chứa các mốc 07 ngày nhận hàng hoàn, 02 ngày khiếu nại hàng hư hại và 05 ngày xử lý. Đoạn đúng về “Hoàn Tiền Ngay” không có đủ bằng chứng trong top-3 vì FixedSize cắt tiêu đề và nội dung liên quan sang các chunk khác nhau. Cách sửa đề xuất là tách theo heading, gắn lại heading vào mọi chunk con, rồi dùng reranker hoặc kết hợp từ khóa “phản hồi” với cosine.

**Bài học rút ra khi so sánh trong nhóm:**
> Trên cùng corpus và embedding thật trong các lượt chạy do từng thành viên thực hiện, HeadingChunker đạt 7/10 vì tận dụng cấu trúc có sẵn của tài liệu, trong khi FixedSize đạt 5/10 nhờ overlap, Recursive đạt 4/10 và SentenceChunker của Tuyên đạt 3/10. Kết quả cho thấy ít chunk hơn hoặc giữ nguyên câu chưa chắc retrieval tốt hơn; ranh giới chunk có khớp với đơn vị ý nghĩa của tài liệu hay không mới là yếu tố quyết định.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> Nhóm nên giữ metadata `audience` nhưng bổ sung `section_title` và `policy_type` cho từng chunk. Với tài liệu quy định có cấu trúc rõ, tách theo heading trước rồi dùng RecursiveChunker cho section quá dài sẽ giữ điều khoản và mốc thời gian gần nhau hơn FixedSize thuần túy.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | 10 / 10 |
| Thiết kế chiến lược (Strategy Design) | 15 / 15 |
| Chất lượng truy xuất (Retrieval Quality) | 7 / 10 |
| Thuyết trình (Demo) | 4 / 5 |
| **Tổng phần nhóm** | **36 / 40** |
