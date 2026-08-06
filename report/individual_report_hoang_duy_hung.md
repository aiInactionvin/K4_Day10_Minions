# Báo Cáo Cá Nhân - Hoàng Duy Hưng

## 1. Thông Tin Cá Nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Hoàng Duy Hưng |
| MSSV | 2A202601908 |
| Khóa/Lớp | K4/D305 |
| Tên nhóm | Minions |
| Vai trò chính | Pipeline Integrator / Lead |
| Repository | https://github.com/aiInactionvin/K4_Day10_Minions |
| Ngày hoàn thành | 06/08/2026 |

## 2. Vai Trò Và Phạm Vi

| Module/deliverable | File/hàm phụ trách | Input | Output | Trạng thái |
| --- | --- | --- | --- | --- |
| Baseline orchestration | `src/pipelines/phase1.py` | Raw records, cleaning, embedding, evaluation modules | Baseline clean data, index, metrics, report | Hoàn thành |
| Corruption orchestration | `src/pipelines/corruption_flow.py` | Baseline artifacts, corruption/repair modules | Corrupted/repaired metrics và comparison report | Hoàn thành |
| Integration evidence | `script/run_phase1.py`, `script/run_corruption_flow.py` | Full project | Reproducible artifacts trong `data/` | Hoàn thành |

## 3. Kết Quả Theo Vai Trò

| Nhiệm vụ | Artifact liên quan | Kết quả | Cách xác minh |
| --- | --- | --- | --- |
| Chạy baseline end-to-end | `data/results/baseline_metrics.json` | Baseline metrics được tạo | `python script/run_phase1.py` |
| Chạy corruption flow | `data/reports/corruption_report.md` | So sánh baseline/corrupted/repaired | `python script/run_corruption_flow.py` |
| Đảm bảo artifact khớp provider/model | `data/embeddings/*.json` | MiniLM embedding manifest schema 2 | Kiểm `embedding_provider=minilm` |

## 4. Giải Thích Kỹ Thuật

Vai trò pipeline integrator nối các module độc lập thành luồng chạy có thứ tự. Baseline flow load/fetch raw records, clean data, build Chroma index, tạo/load test set, evaluate, chạy quality/freshness và sinh report. Corruption flow đảm bảo baseline artifact tồn tại và khớp embedding provider hiện tại, sau đó tạo corrupted data, rebuild index, evaluate, repair từ raw records, evaluate repaired và tạo comparison report.

Input chính là `data/raw/crossref_records.json` và config trong `.env`. Output chính là các artifact trong `data/results/`, `data/quality/`, `data/reports/`.

## 5. Quyết Định Kỹ Thuật Quan Trọng

- Bối cảnh: Artifact embedding cũ có thể không khớp với provider/model hiện tại.
- Phương án: Luôn rebuild hoặc validate manifest trước khi dùng.
- Lựa chọn: Validate manifest/provider và auto-run baseline nếu artifact không khớp.
- Lý do: Tránh so sánh metrics trên index sai model.
- Bằng chứng: `data/embeddings/papers_embeddings.json` có `embedding_provider=minilm`, `embedding_dimension=384`.

## 6. Blocker Đã Xử Lý

- Triệu chứng: Pipeline có thể lỗi khi embedding manifest cũ không khớp config.
- Nguyên nhân: Provider/model embedding thay đổi hoặc artifact bị rebuild một phần.
- Cách xử lý: Thêm validation và rebuild index trong flow.
- Xác minh: Baseline/corruption flow tạo đủ metrics và reports.

## 7. Hiểu Biết End-to-End

Dữ liệu đi từ Crossref raw records sang cleaned dataframe, sau đó thành vector index để RAG retrieve. Evaluation set dùng `ground_truth_doc_ids` từ `paper_id` thật để tính retrieval hit. Quality checks phát hiện null/duplicate/summary/freshness, còn freshness tập trung vào tuổi dữ liệu theo `published` và `age_days`. Ba trạng thái dùng cùng test set để so sánh công bằng. Repair thành công khi quality pass, freshness fresh và metrics repaired quay về baseline.

## 8. Phân Tích Kết Quả

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.5000 | 1.0000 | Corruption làm retrieval giảm rõ |
| `mean_token_f1` | 1.0000 | 0.5168 | 1.0000 | Answer quality phục hồi sau repair |
| `judge_accuracy` | 1.0000 | 0.5000 | 1.0000 | Judge xác nhận tác động |
| `mean_judge_score` | 5.0000 | 3.0000 | 5.0000 | Repaired về mức baseline |
| Quality checks | pass | fail | pass | Observability bắt được lỗi |
| Freshness status | fresh | stale | fresh | Repair xóa stale rows |

## 9. Điều Học Được

1. Pipeline cần validate artifact trước khi reuse.
2. Metrics chỉ có ý nghĩa khi ba trạng thái dùng cùng test set.
3. Data quality fail có thể biểu hiện trực tiếp thành RAG quality drop.

## 10. Cam Kết

- [x] Báo cáo phản ánh đúng phần việc.
- [x] Kết luận có artifact/metric để đối chiếu.
- [x] Không chứa secret.

**Họ và tên:** Hoàng Duy Hưng  
**Ngày xác nhận:** 06/08/2026
