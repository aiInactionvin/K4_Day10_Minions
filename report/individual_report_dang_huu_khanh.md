# Báo Cáo Cá Nhân - Đặng Hữu Khánh

## 1. Thông Tin Cá Nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Đặng Hữu Khanh |
| MSSV | 2A202601104 |
| Khoa/Lớp | K4/D305 |
| Tên nhóm | Minions |
| Vai trò chính | Cleaning + Corruption + Repair Owner |
| Repository | https://github.com/aiInactionvin/K4_Day10_Minions |
| Ngày hoàn thành | 06/08/2026 |

## 2. Vai Trò Và Phạm Vi

| Module/deliverable | File/hàm phụ trách | Input | Output | Trạng thái |
| --- | --- | --- | --- | --- |
| Cleaning | `src/ingestion/cleaning.py` | Raw `PaperRecord` | Clean dataframe | Hoàn thành |
| Corruption | `src/ingestion/corruption.py` | Clean dataframe | Corrupted dataframe + log | Hoàn thành |
| Repair | `repair_clean_dataframe` | Raw records | Repaired clean dataframe | Hoàn thành |

## 3. Kết Quả Theo Vai Trò

| Nhiệm vụ | Artifact liên quan | Kết quả | Cách xác minh |
| --- | --- | --- | --- |
| Tạo clean schema | `data/clean/papers_clean.csv` | 24 rows, 16 columns | Kiểm CSV/JSON |
| Tạo corrupted data | `data/clean/papers_clean_corrupted.*` | 6 loại corruption | `data/results/corruption_log.json` |
| Repair từ raw | `data/clean/papers_clean_repaired.*` | Quality pass lại | `data/quality/repaired_quality.json` |

## 4. Giải Thích Kỹ Thuật

Cleaning chuẩn hóa text/list/date, tính `age_days`, tạo `authors_joined`, `categories_joined`, `summary_chars` và `text_for_embedding`. Duplicate được xử lý deterministic bằng key paper ID và title. Corruption flow tạo lỗi có chủ đích: drop latest records, blank summary, inject noise, truncate title, make stale date và duplicate rows. Repair không sửa trực tiếp corrupted rows mà rebuild dataset từ raw records bằng cleaning chuẩn.

Lệnh xác minh:

```bash
python script/run_corruption_flow.py
```

## 5. Quyết Định Kỹ Thuật Quan Trọng

- **Bối cảnh:** Cần chứng minh data xấu ảnh hưởng RAG.
- **Phương án:** Tạo một lỗi đơn lẻ hoặc nhiều lỗi có audit log.
- **Lựa chọn:** Tạo nhiều corruption scenarios và ghi event log.
- **Lý do:** Observability có thể phát hiện nhiều dimension: completeness, uniqueness, freshness, text integrity.
- **Bằng chứng:** `data/results/corruption_log.json` có 18 events.

## 6. Blocker Đã Xử Lý

- **Triệu chứng:** Corrupted data vẫn cần đủ rows để evaluate nhưng phải có lỗi rõ.
- **Nguyên nhân:** Drop rows quá nhiều có thể làm dataset quá nhỏ.
- **Cách xử lý:** Drop latest 3 rows nhưng append duplicate 3 rows để giữ output row count 24.
- **Xác minh:** `corrupted_quality.json` fail duplicate/null/freshness, metrics RAG giảm.

## 7. Hiểu Biết End-to-End

Cleaning là contract giữa ingestion và RAG. Corruption làm sai contract clean data, từ đó retrieval và answer quality giảm. Repair thành công khi rebuild từ raw records, quality pass và metrics repaired quay về baseline.

## 8. Phân Tích Kết Quả

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.5000 | 1.0000 | Drop/duplicate/noise làm retrieval giảm |
| `mean_token_f1` | 1.0000 | 0.5168 | 1.0000 | Blank/noisy summary làm answer kém |
| Quality checks | pass | fail | pass | Corruption bị detect đúng |
| Freshness status | fresh | stale | fresh | Stale date được repair |

## 9. Điều Học Được

1. Cleaning schema phải ổn định để các module sau dùng được.
2. Corruption cần có log để truy vết tác động.
3. Repair tốt nhất nên dựa vào raw source sạch, không chế lỗi ở corrupted data.

## 10. Cam Kết

- [x] Báo cáo phản ánh đúng phần việc.
- [x] Kết luận có artifact/metric để đối chiếu.
- [x] Không chứa secret.

**Họ và tên:** Đặng Hữu Khanh  
**Ngày xác nhận:** 06/08/2026