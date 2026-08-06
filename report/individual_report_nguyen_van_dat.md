# Individual Report - Nguyen Van Dat

## 1. Thông Tin Cá Nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Văn Đạt |
| MSSV | 2A202601968 |
| Khoa/Lớp | K4/D305 |
| Tên nhóm | Minions |
| Vai trò chính | Evaluation + Observability + Report Owner |
| Repository | https://github.com/aiInactionvin/K4_Day10_Minions |
| Ngày hoàn thành | 06/08/2026 |

## 2. Vai Trò Và Phạm Vi

| Module/deliverable | File/hàm phụ trách | Input | Output | Trạng thái |
| --- | --- | --- | --- | --- |
| Evaluation set | `src/evaluation/testset.py` | Clean dataframe | `data/eval/test_set.json` | Hoàn thành |
| Metrics | `src/evaluation/metrics.py` | Index + test set | `*_metrics.json`, `*_answers.json` | Hoàn thành |
| Quality/freshness | `src/observability/quality.py` | Dataframes | `data/quality/*.json` | Hoàn thành |
| Reports | `src/observability/reporting.py` | Metrics + quality + freshness | Markdown reports | Hoàn thành |

## 3. Kết Quả Theo Vai Trò

| Nhiệm vụ | Artifact liên quan | Kết quả | Cách xác minh |
| --- | --- | --- | --- |
| Tạo evaluation test set | `data/eval/test_set.json` | 24 câu, 4 question types | Kiểm JSON và `ground_truth_doc_ids` |
| Chạy metrics | `data/results/*_metrics.json` | Baseline/corrupted/repaired comparison | Kiểm bảng metrics |
| Tạo observability reports | `data/quality/*.json` | Quality/freshness signals | Kiểm pass/fail |
| Tạo final report | `data/reports/corruption_report.md` | Chứng minh data xấu làm RAG kém | Đọc report |

## 4. Giải Thích Kỹ Thuật

Evaluation set được tạo từ cleaned data thật, mỗi sample có `question`, `ground_truth`, `ground_truth_doc_ids`. ID ground truth lấy từ `paper_id`, không tự bịa. Câu hỏi được tạo từ title/metadata thật để ground truth rõ ràng. Metrics gồm retrieval hit, token F1, judge accuracy và judge score. Observability check row count, null, duplicate, summary length, `age_days` và source timestamp `published`. Reports gồm baseline report và corruption impact report.

Lệnh xác minh:

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

## 5. Quyết Định Kỹ Thuật Quan Trọng

- **Bối cảnh:** Evaluation set cần có ground truth rõ ràng và doc ID thật.
- **Phương án:** Viết tay câu hỏi hoặc sinh câu hỏi từ cleaned dataframe.
- **Lựa chọn:** Sinh câu hỏi từ title/metadata của paper thật.
- **Lý do:** Đảm bảo mỗi `ground_truth_doc_ids` lấy từ `paper_id` sạch, không bịa ID.
- **Bằng chứng:** `data/eval/test_set.json` có 24 câu và doc IDs khớp clean data.

## 6. Blocker Đã Xử Lý

- **Triệu chứng:** Cần chứng minh data quality ảnh hưởng RAG bằng artifact, không chỉ nói pipeline chạy.
- **Nguyên nhân:** Nếu không có comparison report thì metric bị rời rạc.
- **Cách xử lý:** Tạo `corruption_report.md` gồm metric, quality, freshness và impact.
- **Xác minh:** Report có bảng baseline/corrupted/repaired và kết luận nhân quả.

## 7. Hiểu Biết End-to-End

Dữ liệu từ Crossref được clean, embed và index. Evaluation set dùng ground-truth doc IDs để xem retrieval có lấy đúng paper không. Quality checks tập trung vào tính đúng/đủ/unique của data; freshness tập trung vào độ mới theo ngày publish. Dùng cùng test set cho ba trạng thái giúp so sánh công bằng. Repair thành công khi quality/freshness pass lại và metrics repaired quay về baseline.

## 8. Phân Tích Kết Quả

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.5000 | 1.0000 | Corrupted data làm retrieve đúng giảm gần một nửa |
| `mean_token_f1` | 1.0000 | 0.5168 | 1.0000 | Answer khớp ground truth kém hơn sau corruption |
| `judge_accuracy` | 1.0000 | 0.5000 | 1.0000 | Judge xác nhận chất lượng giảm |
| `mean_judge_score` | 5.0000 | 3.0000 | 5.0000 | Repair phục hồi chất lượng |
| Quality checks | pass | fail | pass | Observability detect lỗi data |
| Freshness status | fresh | stale | fresh | Stale rows 3/24 sau corruption |

## 9. Điều Học Được

1. Evaluation set phải lấy ground truth từ data thật và giữ ổn định.
2. Observability cần có tín hiệu cụ thể như null, duplicate, age_days.
3. Report tốt phải nói được mối quan hệ data corruption -> metric drop -> repair recovery.

## 10. Cam Kết

- [x] Báo cáo phản ánh đúng phần việc.
- [x] Kết luận có artifact/metric để đối chiếu.
- [x] Không chứa secret.

**Họ và tên:** Nguyễn Văn Đạt  
**Ngày xác nhận:** 06/08/2026