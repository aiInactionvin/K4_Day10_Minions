# Báo Cáo Cá Nhân - Sẻ Thế Hưng

## 1. Thông Tin Cá Nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Sẻ Thế Hưng |
| MSSV | 2A202601968 |
| Khóa/Lớp | K4/D305 |
| Tên nhóm | Minions |
| Vai trò chính | Ingestion Owner |
| Repository | https://github.com/aiInactionvin/K4_Day10_Minions |
| Ngày hoàn thành | 06/08/2026 |

## 2. Vai Trò Và Phạm Vi

| Module/deliverable | File/hàm phụ trách | Input | Output | Trạng thái |
| --- | --- | --- | --- | --- |
| Crossref ingestion | `src/ingestion/crossref.py` | Crossref REST API | Raw API response và raw records | Hoàn thành |
| Payload parsing | `parse_crossref_payload` | Crossref JSON payload | `PaperRecord` list | Hoàn thành |
| Raw snapshot loading | `load_raw_records` | `data/raw/crossref_records.json` | `PaperRecord` list cho cleaning/repair | Hoàn thành |

## 3. Kết Quả Theo Vai Trò

| Nhiệm vụ | Artifact liên quan | Kết quả | Cách xác minh |
| --- | --- | --- | --- |
| Fetch và parse Crossref | `data/raw/crossref_response.json` | Raw response được lưu | File JSON parse được |
| Lưu raw records | `data/raw/crossref_records.json` | 24 paper records | Kiểm list length = 24 |
| Tạo stable ID | `paper_id` | DOI được clean theo format `doi:...` | Clean/testset dùng ID này |

## 4. Giải Thích Kỹ Thuật

Ingestion module lấy dữ liệu từ Crossref API theo query và filter trong config. Hàm parse trích xuất DOI, title, abstract, authors, subject, published/updated date và URL. Các record không có title bị bỏ qua, text được clean HTML và whitespace. `paper_id` ưu tiên DOI để giữ document identity ổn định; nếu thiếu DOI thì fallback hash title.

Raw records là nguồn tin cậy cho cả baseline cleaning và repair flow.

## 5. Quyết Định Kỹ Thuật Quan Trọng

- Bối cảnh: Crossref payload có nhiều trường optional và date-parts không đồng nhất.
- Phương án: Parse ad hoc trong pipeline hoặc tạo `PaperRecord` schema.
- Lựa chọn: Tạo `PaperRecord` dataclass.
- Lý do: Module cleaning và repair có contract rõ ràng, dễ load lại snapshot.
- Bằng chứng: `load_raw_records` có thể rebuild repaired dataset từ raw.

## 6. Blocker Đã Xử Lý

- Triệu chứng: Một số records có abstract/date/author không đồng nhất.
- Nguyên nhân: Crossref metadata khác nhau giữa publishers.
- Cách xử lý: Normalize text, parse date từ nhiều trường, default category khi cần.
- Xác minh: Cleaning tạo đủ 24 rows hợp lệ.

## 7. Hiểu Biết End-to-End

Raw records từ ingestion là đầu vào cho cleaning. `paper_id` từ ingestion được dùng làm document ID cho embedding, evaluation ground truth và repair. Nếu ingestion sai ID hoặc date, cả retrieval hit và freshness report sẽ sai.

## 8. Phân Tích Kết Quả

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.5000 | 1.0000 | Raw source tốt giúp repair phục hồi |
| Quality checks | pass | fail | pass | Ingestion snapshot là nguồn repair đáng tin cậy |
| Freshness status | fresh | stale | fresh | Published date từ raw giúp tính freshness lại đúng |

## 9. Điều Học Được

1. Raw snapshot cần đủ thông tin để truy vết và repair.
2. Stable document ID là contract quan trọng cho evaluation.
3. API payload bên ngoài cần parse phòng thủ vì schema thay đổi.

## 10. Cam Kết

- [x] Báo cáo phản ánh đúng phần việc.
- [x] Kết luận có artifact/metric để đối chiếu.
- [x] Không chứa secret.

**Họ và tên:** Sẻ Thế Hưng  
**Ngày xác nhận:** 06/08/2026
