# Báo Cáo Nhóm - Day 10: Data Pipeline & Data Observability

## 1. Thông Tin Bài Nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4/D305 |
| Tên nhóm | Minions |
| Repository | https://github.com/aiInactionvin/K4_Day10_Minions |
| Ngày hoàn thành | 06/08/2026 |

### Thành Viên Và Phân Công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Hoàng Duy Hưng | 2A202601908 | Pipeline Integrator / Lead | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, tích hợp end-to-end |
| 2 | Sẻ Thế Hưng | 2A202601822 | Ingestion Owner | `src/ingestion/crossref.py`, raw response và raw records |
| 3 | Đặng Hữu Khanh | 2A202601104 | Cleaning + Corruption + Repair Owner | `src/ingestion/cleaning.py`, `src/ingestion/corruption.py`, clean/corrupted/repaired datasets |
| 4 | Nguyễn Đặng Thành Vinh | 2A202602021 | RAG / Embedding / Agent Owner | `src/retrieval/`, MiniLM embedding, Chroma index, QA/agent |
| 5 | Nguyễn Văn Đạt | 2A202601968 | Evaluation + Observability + Report Owner | `src/evaluation/`, `src/observability/`, metrics và reports |

## 2. Tóm Tắt Kết Quả

Nhóm đã hoàn thành pipeline RAG với dữ liệu paper từ Crossref theo ba trạng thái: baseline, corrupted và repaired. Baseline flow lấy raw records, clean thành dataset 24 papers, tạo embedding bằng `sentence-transformers/all-MiniLM-L6-v2`, build Chroma index, tạo evaluation set 24 câu hỏi và sinh quality/freshness reports. Corruption flow tạo lỗi có chủ đích như drop latest records, blank summary, inject noise, truncate title, stale publication date và duplicate rows. Sau corruption, RAG performance giảm rõ: `retrieval_hit_rate` từ 1.0000 xuống 0.5000, `mean_token_f1` từ 1.0000 xuống 0.5168, `judge_accuracy` từ 1.0000 xuống 0.5000. Repair flow rebuild dataset từ raw records sạch, chạy lại cleaning và re-index, đưa metrics về mức baseline. Báo cáo cuối chứng minh data quality xấu làm RAG kém đi và repair từ nguồn raw sạch giúp phục hồi chất lượng.

## 3. Kiến Trúc Và Luồng Dữ Liệu

```text
Crossref API
    -> data/raw/crossref_response.json
    -> data/raw/crossref_records.json
    -> cleaning và data modeling
    -> data/clean/papers_clean.*
    -> MiniLM embedding + ChromaDB index
    -> evaluation baseline
    -> quality/freshness reports
    -> corruption
    -> corrupted index + evaluation
    -> repair từ raw records
    -> repaired index + evaluation
    -> comparison report
```

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| --- | --- | --- | --- | --- |
| Ingestion | Crossref API | Fetch, retry, parse DOI/title/abstract/authors/date | `data/raw/` | Sẻ Thế Hưng |
| Cleaning | Raw records | Normalize text/list/date, dedupe, tạo `text_for_embedding`, tính `age_days` | `data/clean/papers_clean.*` | Đặng Hữu Khanh |
| Embedding/index | Clean dataframe | MiniLM embedding, Chroma collection, manifest validation | `data/embeddings/`, `data/chroma/` | Nguyễn Đặng Thành Vinh |
| Evaluation | Index + test set | Retrieval hit, token F1, judge score | `data/results/*_metrics.json`, `*_answers.json` | Nguyễn Văn Đạt |
| Observability | Clean/corrupted/repaired data | Row count, null, duplicate, summary length, freshness | `data/quality/` | Nguyễn Văn Đạt |
| Corruption/repair | Clean data, raw records | Tạo data lỗi, repair bằng raw records và cleaning chuẩn | corrupted/repaired datasets, `corruption_log.json` | Đặng Hữu Khanh |
| Orchestration | Các module trên | Chạy baseline và corruption flow end-to-end | `phase1_report.md`, `corruption_report.md` | Hoàng Duy Hưng |

## 4. Cách Tái Hiện Kết Quả

### Cấu Hình Không Chứa Secret

| Biến/cấu hình | Giá trị sử dụng |
| --- | --- |
| `LLM_PROVIDER` | theo `.env` |
| `LLM_MODEL` | theo `.env` |
| `EMBEDDING_PROVIDER` | `minilm` |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 ngày |
| Ragas | Skipped mặc định, bật bằng `RUN_RAGAS=1` nếu cần |

Không đưa API key hoặc nội dung `.env` vào báo cáo.

### Lệnh Cài Đặt Và Chạy

```bash
python -m pip install -e .
python script/run_phase1.py
python script/run_corruption_flow.py
```

## 5. Ingestion, Cleaning Và Data Contract

Nguồn dữ liệu là Crossref REST API với query `agentic retrieval augmented generation large language model` và filter `has-abstract:true`. Raw records được lưu trong `data/raw/crossref_records.json`.

| Trường | Bắt buộc | Ý nghĩa |
| --- | --- | --- |
| `paper_id` | Có | Document ID ổn định, ưu tiên DOI clean |
| `title` | Có | Tiêu đề paper đã normalize |
| `summary` | Có | Abstract/summary dùng cho answer và embedding |
| `authors_joined` | Có | Danh sách tác giả nối bằng dấu phẩy |
| `categories_joined` | Có | Subject/categories |
| `published` | Có | Ngày publish chuẩn `YYYY-MM-DD` |
| `age_days` | Có | Độ tuổi dữ liệu tính từ run date |
| `text_for_embedding` | Có | Text canonical để tạo vector |

Cleaning loại record thiếu ID/title/summary/published, normalize HTML/whitespace, deduplicate theo `paper_id` và title, sắp xếp deterministic.

## 6. Evaluation Setup

| Thành phần | Cấu hình thực tế |
| --- | --- |
| Số câu hỏi | 24 |
| Question types | `summary`, `authors`, `date`, `categories` |
| Ground truth doc ID | Lấy từ `paper_id` trong cleaned dataframe |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store | ChromaDB, collections `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Retrieval `top_k` | 4 |
| LLM judge | Cấu hình theo `.env`, fallback token-F1 heuristic nếu LLM unavailable |
| Test set | `data/eval/test_set.json`, dùng chung cho 3 trạng thái |

Test set được tạo từ cleaned data thật, gồm các câu hỏi summary/authors/date/categories dựa trên title và metadata thật của paper.

## 7. Kết Quả Baseline

| Artifact | Đường dẫn | Trạng thái |
| --- | --- | --- |
| Raw response/records | `data/raw/` | Có |
| Cleaned dataset | `data/clean/papers_clean.csv`, `.json` | Có |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json`, `data/chroma/` | Có |
| Evaluation set | `data/eval/test_set.json` | Có |
| Baseline metrics | `data/results/baseline_metrics.json` | Có |
| Quality/freshness | `data/quality/baseline_quality.json`, `freshness_report.json` | Có |
| Baseline report | `data/reports/phase1_report.md` | Có |

| Metric | Giá trị | Diễn giải |
| --- | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | Retrieve đúng ground-truth doc cho 24/24 câu |
| `mean_token_f1` | 1.0000 | Câu trả lời khớp ground truth |
| `judge_accuracy` | 1.0000 | Judge đánh giá đúng toàn bộ câu trả lời |
| `mean_judge_score` | 5.0000 | Điểm chất lượng trung bình 5/5 |
| Ragas | Skipped | Chưa bật `RUN_RAGAS=1` để tránh pass chậm và tốn chi phí |

## 8. Data Quality Và Freshness

Quality checks gồm: row count, `paper_id` not null/unique, `title` not null, `summary` not null và đủ dài, `published` not null, `age_days` freshness, duplicate title signal.

| Signal | Kết quả |
| --- | --- |
| Quality status | pass |
| Total rows | 24 |
| Nulls | `paper_id=0`, `title=0`, `summary=0`, `published=0` |
| Duplicates | `paper_id=0`, `title=0` |
| Freshness | `is_fresh=True`, stale rows `0/24` |
| Latest/oldest published | `2026-08-05` / `2026-02-12` |

## 9. Corruption Scenarios Và Repair

| Corruption | Cách tạo | Record tác động | Quality signal kỳ vọng | Repair |
| --- | --- | ---: | --- | --- |
| Drop latest records | Xóa 3 latest papers | 3 | Missing ground-truth docs, retrieval drop | Rebuild từ raw records |
| Blank summary | Set summary rỗng | 3 | `summary_not_null`, `summary_length` fail | Chạy lại cleaning từ raw |
| Inject noise | Chèn marker noise vào summary | 3 | Answer/retrieval degrade | Chạy lại cleaning từ raw |
| Truncate title | Cắt ngắn title | 3 | Text integrity và retrieval degrade | Chạy lại cleaning từ raw |
| Make stale date | Lùi published date 5 năm | 3 | `freshness_age_days` fail | Chạy lại cleaning từ raw |
| Duplicate rows | Thêm duplicate rows | 3 | `paper_id_unique`, duplicate title fail | Chạy lại cleaning từ raw |

Corruption log: `data/results/corruption_log.json`, có 18 events và operation counts đầy đủ.

Repair không sửa trực tiếp corrupted data. Flow repair load `data/raw/crossref_records.json`, chạy lại `build_clean_dataframe`, rebuild MiniLM embedding index và evaluate lại bằng cùng test set.

## 10. So Sánh Baseline, Corrupted Và Repaired

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.5000 | 1.0000 | Corruption làm retrieval giảm mạnh, repair phục hồi |
| `mean_token_f1` | 1.0000 | 0.5168 | 1.0000 | Câu trả lời kém khớp hơn sau corruption |
| `judge_accuracy` | 1.0000 | 0.5000 | 1.0000 | Đúng/sai bị ảnh hưởng rõ |
| `mean_judge_score` | 5.0000 | 3.0000 | 5.0000 | Điểm judge giảm rồi hồi phục |
| Quality checks | pass | fail | pass | Observability phát hiện lỗi data |
| Freshness status | fresh | stale | fresh | Stale rows từ 0 lên 3 rồi về 0 |

Kết luận nhân quả:

1. Blank summary, duplicate ID, stale date và dropped latest records làm quality/freshness fail, đồng thời `retrieval_hit_rate` giảm từ 1.0000 xuống 0.5000.
2. Repair từ raw records sạch làm quality/freshness pass lại và metric RAG phục hồi về mức baseline.

## 11. Vấn Đề Tích Hợp Quan Trọng

- Triệu chứng: Khi tái sử dụng artifact embedding cũ, pipeline cần đảm bảo index đang dùng đúng provider/model hiện tại.
- Nguyên nhân: Chroma index và manifest có thể bị lệch nếu thay đổi embedding config hoặc rebuild một phần artifact.
- Cách xử lý: Thêm `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, embedding factory và manifest schema có `embedding_provider`; pipeline validate/rebuild index khi artifact không khớp.
- Cách xác minh: `data/embeddings/papers_embeddings.json` có `embedding_provider=minilm`, `embedding_dimension=384`.

## 12. Giới Hạn Và Hướng Cải Thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện |
| --- | --- | --- |
| Ragas chưa bật mặc định | Chưa có Ragas metrics | Chạy `RUN_RAGAS=1` khi cần benchmark sâu hơn |
| Test set 24 câu | Chưa bao phủ hết topic/câu hỏi khó | Tăng số câu hỏi và thêm adversarial/noisy user queries |
| Tải/cache model embedding có thể tốn thời gian | Lần đầu cần có cache/model local | Cache model và chỉ rebuild index khi data/model thay đổi |

## 13. Checklist Trước Khi Nộp

- [x] Phân công khớp với module và artifact thực tế.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Metrics khớp `data/results/`.
- [x] Quality/freshness conclusions khớp `data/quality/`.
- [x] Report cuối có tại `data/reports/corruption_report.md`.
- [x] Không đưa `.env`, API key, token hoặc secret vào báo cáo.
