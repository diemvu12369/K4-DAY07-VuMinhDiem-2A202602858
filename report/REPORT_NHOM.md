# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** DeltaX
**Thành viên:**
- Phạm Xuân Quý — 2A202602745 — Data Lead — chiến lược FixedSizeChunker
- Nguyễn Minh Thịnh — 2A202602556 — Benchmark Lead — chiến lược RecursiveChunker
- Vũ Minh Điềm — 2A202602858 — Strategy Lead — chiến lược HeadingChunker (chunk theo heading/mục)
- Nguyễn Hoàng Tuyên — 2A202602439 — Evaluation & Report Lead — chiến lược SentenceChunker

**Ngày:** 2026-09-20 (bản nháp — mỗi thành viên tự bổ sung điểm truy xuất riêng trước khi nộp)

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Chính sách đổi trả và hoàn tiền (Return/Refund) trên **Shopee** — nguồn công khai từ Trung tâm trợ giúp `help.shopee.vn`, gồm cả phía người mua (buyer) và nghĩa vụ/quyền của người bán (seller).

**Tại sao nhóm chọn chủ đề này?** Đây là chủ đề bắt buộc của lớp L3B (xem `K4_VARIANT.md`). Nhóm chọn cụ thể Shopee vì trang trợ giúp có cấu trúc theo mục (heading) rõ ràng, nêu số liệu/mốc thời gian cụ thể (24 giờ, 02 ngày lịch, 7-14 ngày làm việc...) dễ kiểm chứng gold answer, và tách rõ nội dung dành cho buyer vs. seller — phù hợp để thử nghiệm `metadata_filter={"audience": ...}`.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự (thân bài) | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | buyer-return-conditions | help.shopee.vn/portal/4/article/188931 | 2026-09-19 / not-stated | 6050 | audience=buyer, category, language |
| 2 | buyer-return-request-guide | help.shopee.vn/portal/4/article/79233 | 2026-09-19 / not-stated | ~2700 | audience=buyer, category, language |
| 3 | buyer-return-processing | help.shopee.vn/portal/4/article/190242 | 2026-09-19 / not-stated | 7846 | audience=buyer, category, language |
| 4 | buyer-refund-timeline | help.shopee.vn/portal/4/article/189473 | 2026-09-19 / not-stated | ~4200 | audience=buyer, category, language |
| 5 | seller-mall-return-obligations | help.shopee.vn/portal/4/article/77262 | 2026-09-19 / effective-2026-05-08 | 4101 | audience=seller, category, language |
| 6 | seller-rights-and-duties | help.shopee.vn/portal/4/article/77245 | 2026-09-19 / updated-2025-01-03 | ~4700 | audience=seller, category, language |

Chi tiết đầy đủ và khớp 1-1: `data/shopee-return-refund/sources.csv`.

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng (Trung tâm trợ giúp Shopee) và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực, `not-stated` nếu nguồn không nêu) trong metadata.
- [x] Đã chạy checklist CP2 của `docs/DATA_COLLECTION.md`: 6 file, đủ metadata bắt buộc, `sources.csv` khớp 1-1, `audience` có 2 giá trị (`buyer`: 4, `seller`: 2).

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| `audience` | string enum | `buyer` / `seller` | Trường lọc bắt buộc của L3B — tách hai đối tượng có câu trả lời khác nhau cho cùng một chủ đề (vd. thời hạn phản hồi khác nhau giữa buyer và seller), dùng cho `metadata_filter`. |
| `doc_id` | string | `buyer-refund-timeline` | Khoá để `delete_document` và để đối chiếu chunk trả về với đúng tài liệu gold trong benchmark. |
| `category` | string | `returns-policy`, `refund-timeline`, `warranty-policy` | Lọc phụ theo loại chính sách khi câu hỏi chỉ liên quan một nhóm chủ đề con. |
| `language` | string | `vi` | Cho phép mở rộng lọc theo ngôn ngữ nếu corpus sau này có thêm tài liệu tiếng Anh. |
| `document_version` | string | `not-stated`, `effective-2026-05-08` | Ghi minh bạch việc nguồn có nêu ngày hiệu lực hay không — không bịa số hiệu khi nguồn không có. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

`ChunkingStrategyComparator().compare(text, chunk_size=200)` trên 3 tài liệu (đã bỏ frontmatter YAML trước khi so sánh):

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| buyer-return-conditions (6050 ký tự) | FixedSizeChunker (`fixed_size`) | 31 | 195.2 | Không — cắt cứng theo ký tự, thường xuyên cắt ngang câu/số liệu |
| buyer-return-conditions | SentenceChunker (`by_sentences`) | 9 | 667.1 | Có, theo câu, nhưng chunk khá dài (gộp 3 câu) nên trộn nhiều ý |
| buyer-return-conditions | RecursiveChunker (`recursive`) | 37 | 161.6 | Tốt hơn fixed size — ưu tiên cắt ở `\n\n`/`. ` nên ít cắt ngang câu, nhưng chunk nhỏ hơn cả fixed size vì nhiều đoạn ngắn |
| buyer-return-processing (7846 ký tự) | fixed_size | 40 | 196.2 | Không |
| buyer-return-processing | by_sentences | 12 | 650.2 | Có |
| buyer-return-processing | recursive | 53 | 146.3 | Tốt hơn fixed size |
| seller-mall-return-obligations (4101 ký tự) | fixed_size | 21 | 195.3 | Không |
| seller-mall-return-obligations | by_sentences | 7 | 583.0 | Có |
| seller-mall-return-obligations | recursive | 27 | 150.3 | Tốt hơn fixed size |

Nhận xét chung: `fixed_size` luôn cho chunk đều nhau (~195-200 ký tự) nhưng cắt bất chấp ranh giới câu/mục — rủi ro cắt đúng vào số liệu (vd. "24 giờ") làm chunk mất nghĩa. `by_sentences` giữ trọn câu nhưng chunk dài nhất (583-667 ký tự trung bình), có thể vượt quá `chunk_size` mong muốn khi câu dài. `recursive` cho chunk ngắn nhất và bám sát ranh giới tự nhiên (đoạn/câu) tốt hơn `fixed_size`.

### Chiến lược của từng thành viên

**Thành viên 1 — Phạm Xuân Quý (Data Lead)**
- **Loại chiến lược:** FixedSizeChunker
- **Mô tả & lý do chọn cho chủ đề này:** *(Quý tự điền kết quả benchmark của mình vào đây)*

**Thành viên 2 — Nguyễn Minh Thịnh (Benchmark Lead)**
- **Loại chiến lược:** RecursiveChunker
- **Mô tả & lý do chọn:** *(Thịnh tự điền kết quả benchmark của mình vào đây)*

**Thành viên 3 — Vũ Minh Điềm (Strategy Lead)**
- **Loại chiến lược:** HeadingChunker (custom — chunk theo tiêu đề/mục Markdown)
- **Mô tả & lý do chọn cho chủ đề này:** Văn bản chính sách Shopee đã được viết theo mục có heading (`## 1. Nguyên tắc chung`, `### 1.2. Thời gian tối đa...`), mỗi mục là một đơn vị ngữ nghĩa trọn vẹn do người soạn chia sẵn — chunk theo heading tận dụng đúng cấu trúc đó thay vì cắt cơ học. Trên corpus 6 tài liệu (87 chunk), chiến lược này cho **top-1 đúng tài liệu ở cả 5/5 câu hỏi**, và câu cần `metadata_filter={"audience":"seller"}` đạt điểm tối đa (top-1 đúng mục, chứa đúng đáp án "02 ngày lịch"). Điểm yếu quan sát được: khi một mục dài bị hạ xuống `RecursiveChunker` (vd. bảng "Phương thức thanh toán và thời gian hoàn tiền"), các mảnh con cùng một mục có nội dung/điểm số rất gần nhau nên **mảnh con nào lọt top-3 gần như ngẫu nhiên** — 2/5 câu (Q3, Q4) đúng tài liệu, đúng mục nhưng chunk cụ thể lọt top-k lại thiếu đúng dòng số liệu cần trả lời (xem `ket_qua_benchmark.txt`, mục 4 báo cáo cá nhân của Điềm).
- **Code snippet:**
```python
class HeadingChunker:
    HEADING_RE = re.compile(r"^(#{1,6})\s+.*$", re.MULTILINE)

    def chunk(self, text: str) -> list[str]:
        headings = list(self.HEADING_RE.finditer(text))
        if not headings:
            return RecursiveChunker(chunk_size=self.chunk_size).chunk(text)
        # ... cắt theo từng đoạn giữa 2 heading liên tiếp, mục dài thì hạ xuống
        # RecursiveChunker và gắn lại heading vào mọi mảnh con (xem src/chunking.py)
```

**Thành viên 4 — Nguyễn Hoàng Tuyên (Evaluation & Report Lead)**
- **Loại chiến lược:** SentenceChunker
- **Mô tả & lý do chọn:** *(Tuyên tự điền kết quả benchmark của mình vào đây — lưu ý: repo này đã từng chạy thử SentenceChunker trên corpus và đạt ~6/10 theo thang `docs/SCORING.md`, có thể dùng làm tham chiếu, xem lịch sử `bench.py`.)*

### So Sánh Giữa Các Thành Viên

| Thành viên | Chiến lược (Strategy) | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Phạm Xuân Quý | FixedSizeChunker | *(chờ Quý điền)* | Đơn giản, chunk đều nhau, tốc độ nạp nhanh | Cắt bất chấp ranh giới câu/số liệu |
| Nguyễn Minh Thịnh | RecursiveChunker | *(chờ Thịnh điền)* | Bám ranh giới đoạn/câu tự nhiên tốt hơn fixed size | Chunk nhỏ, một mục có thể bị chia thành nhiều chunk rời rạc |
| Vũ Minh Điềm | HeadingChunker | 5/10 (2đ Q1 + 1đ Q2 + 0đ Q3 + 0đ Q4 + 2đ Q5, theo `docs/SCORING.md`) | Đúng tài liệu 5/5 câu; câu cần metadata_filter đạt điểm tối đa | Mục dài bị hạ xuống recursive nên "sai section trong đúng mục" ở câu có số liệu nằm giữa bảng dài |
| Nguyễn Hoàng Tuyên | SentenceChunker | *(chờ Tuyên điền)* | Giữ trọn câu, không cắt ngang ý | Chunk dài (gộp 3 câu) dễ trộn nhiều ý không liên quan trong cùng chunk |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> *(Điền sau khi cả 4 thành viên có điểm số — nhưng nhận xét sơ bộ của Điềm: với văn bản chính sách có cấu trúc heading rõ ràng như Shopee, `HeadingChunker` có lợi thế "đúng tài liệu" gần như tuyệt đối vì mỗi mục là một đơn vị chủ đề, nhưng để đạt điểm tuyệt đối cần thêm bước giảm `chunk_size` cho các mục chứa bảng dài, tránh việc một mục quan trọng bị chẻ thành nhiều mảnh có điểm gần bằng nhau.)*

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy (cũng khai báo trong `bench.py`).

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | Với thực phẩm tươi sống và đông lạnh, người mua phải gửi yêu cầu Trả hàng/Hoàn tiền trong thời hạn bao lâu? | Trong vòng 24 giờ kể từ khi đơn hàng được cập nhật trạng thái "Giao hàng thành công", trừ trường hợp chưa nhận được hàng. | `buyer-return-conditions` |
| 2 | Shopee có hỗ trợ yêu cầu đổi hàng không, và người mua có thể làm gì nếu hàng nhận được có vấn đề? | Shopee chưa hỗ trợ đổi hàng. Người mua có thể từ chối nhận khi đồng kiểm hoặc gửi yêu cầu Trả hàng/Hoàn tiền sau khi nhận hàng. | `buyer-return-conditions` |
| 3 | Người mua có thể gửi yêu cầu Trả hàng/Hoàn tiền bằng những cách nào? | Gửi trực tiếp tại trang đơn hàng hoặc gửi tại mục Trò Chuyện Với Shopee rồi chọn "Khiếu nại trả hàng hoàn tiền". | `buyer-return-request-guide` |
| 4 | Sau khi Shopee chấp nhận hoàn tiền, tiền hoàn về thẻ tín dụng hoặc thẻ ghi nợ mất bao lâu? | Khoảng 7-14 ngày làm việc, tùy theo ngân hàng. | `buyer-refund-timeline` |
| 5 | Một yêu cầu hoàn tiền cần được phản hồi trong bao lâu? | Đối với Người Bán, yêu cầu "Hoàn Tiền Ngay" phải được phản hồi hoặc khiếu nại trong vòng 02 ngày lịch. Nếu không phản hồi, Người Bán được xem là đồng ý với quyết định của Shopee. | `seller-mall-return-obligations` — **cần `metadata_filter={"audience": "seller"}`** |

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).
> Hàng dưới đây là kết quả của **Vũ Minh Điềm (HeadingChunker)**; ba thành viên còn lại tự thêm cột/điểm của mình khi có kết quả.

| # | Câu hỏi | Chiến lược tốt nhất cho câu này (tạm) | Có chunk liên quan trong top-3? (Điềm — Heading) | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | Thời hạn thực phẩm tươi sống | Heading (2đ) | Có, top-1, chứa đúng "24 giờ" | — |
| 2 | Có hỗ trợ đổi hàng? | *(chờ so sánh)* | Có nhưng chỉ top-2 (Heading: 1đ) | Top-1 lạc sang `seller-mall-return-obligations` |
| 3 | Cách gửi yêu cầu | *(chờ so sánh)* | Đúng tài liệu (top-1 & top-3) nhưng sai mục, không chứa đáp án (Heading: 0đ) | Minh chứng "đúng file, sai section" |
| 4 | Thời gian hoàn tiền thẻ tín dụng | *(chờ so sánh)* | Đúng tài liệu cả 3, nhưng mục dài (bảng) bị chẻ nhỏ nên dòng "7-14 ngày" rơi ra ngoài top-3 (Heading: 0đ) | Minh chứng "đúng mục, sai mảnh con" |
| 5 | Thời hạn phản hồi seller | Heading (2đ) | Có, top-1, chứa đúng "02 ngày lịch" — **chỉ khi có filter** | Không filter: top-3 toàn tài liệu `buyer-*`, mất hoàn toàn tài liệu seller đúng |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> Có, rõ rệt nhất ở **câu 5**: chạy A/B trên cùng câu hỏi với `HeadingChunker`, khi **có** `metadata_filter={"audience":"seller"}` thì top-1 là đúng chunk cần (chứa "02 ngày lịch"); khi **không** filter thì cả 3 vị trí top-3 đều bị tài liệu `buyer-return-conditions` (nói về "hoàn tiền" nói chung, cùng từ vựng) chiếm hết, tài liệu seller đúng biến mất hoàn toàn khỏi top-3. Đây là bằng chứng trực tiếp cho ràng buộc #2 của `K4_VARIANT.md`: không có filter, agent gần như chắc chắn sẽ trả lời sai đối tượng.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
> *(3 người còn lại bổ sung thêm sau khi có kết quả riêng)*
> - Chấm theo `doc_id` một mình thổi phồng kết quả: với `HeadingChunker`, 5/5 câu có đúng tài liệu ở top-3, nhưng chỉ 2/5 câu chunk lọt top-k thực sự chứa số liệu trả lời được — khoảng cách giữa hai cách chấm chính là phát hiện đáng giá nhất.
> - `metadata_filter={"audience": "seller"}` là bắt buộc chứ không phải tuỳ chọn: A/B trên câu 5 cho thấy không filter thì tài liệu đúng (seller) biến mất hoàn toàn khỏi top-3, bị thay bằng 3 tài liệu `buyer-*` cùng từ vựng "hoàn tiền".
> - Một mục (heading section) dài chứa bảng số liệu (vd. "Phương thức thanh toán và thời gian hoàn tiền") khi bị hạ xuống `RecursiveChunker` sẽ tạo nhiều mảnh con có điểm gần bằng nhau — mảnh nào lọt top-3 gần như ngẫu nhiên, nên chunk_size cho heading dài cần nhỏ hơn hoặc cần một bước chia theo hàng bảng thay vì theo separator chung.

**Bài học rút ra khi so sánh trong nhóm:**
> *(điền sau khi Quý/Thịnh/Tuyên có kết quả benchmark của mình — so `count`/`avg_length` ở Baseline Analysis mục 2 và điểm `docs/SCORING.md` mục 3 giữa 4 chiến lược trên cùng corpus)*

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> Từ góc nhìn `HeadingChunker`: nên giảm `chunk_size` cho các mục chứa bảng (vd. bảng phương thức hoàn tiền trong `buyer-refund-timeline`) hoặc tách bảng thành các dòng riêng trước khi crawl/làm sạch, để mỗi dòng số liệu (vd. "thẻ tín dụng — 7-14 ngày") là một đơn vị chunk độc lập thay vì bị gộp chung rồi cắt ngẫu nhiên bởi recursive fallback.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | 9 / 10 |
| Thiết kế chiến lược (Strategy Design) | *(chờ đủ 4 thành viên)* / 15 |
| Chất lượng truy xuất (Retrieval Quality) | *(chờ đủ 4 thành viên)* / 10 |
| Thuyết trình (Demo) | *(điền sau demo)* / 5 |
| **Tổng phần nhóm** | **/ 40** |
