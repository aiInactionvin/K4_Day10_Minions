# Individual Report - Nguyễn Đặng Thành Vinh

## 1. Thông Tin Cá Nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Đặng Thành Vinh |
| MSSV | 2A202602021 |
| Khoa/Lớp | K4/D305 |
| Tên nhóm | Minions |
| Vai trò chính | RAG / Embedding / Agent Owner |
| Repository | https://github.com/aiInactionvin/K4_Day10_Minions |
| Ngày hoàn thành | 06/08/2026 |

## 2. Vai Trò Và Phạm Vi

| Module/deliverable | File/hàm phụ trách | Input | Output | Trạng thái |
| --- | --- | --- | --- | --- |
| Embedding provider | `src/retrieval/embeddings.py` | `text_for_embedding` | Vectors từ MiniLM embedding | Hoàn thành |
| Vector index | `src/retrieval/index.py` | Clean/corrupted/repaired dataframe | Chroma collections và manifests | Hoàn thành |
| QA/agent behavior | `src/retrieval/qa.py`, `agent.py` | User question + index | Answer, retrieved doc IDs/context | Hoàn thành |

## 3. Kết Quả Theo Vai Trò

| Nhiệm vụ | Artifact liên quan | Kết quả | Cách xác minh |
| --- | --- | --- | --- |
| Dùng MiniLM embedding | `data/embeddings/papers_embeddings.json` | `embedding_provider=minilm` | Kiểm manifest |
| Build 3 indexes | `data/embeddings/*` | baseline/corrupted/repaired manifests | Kiểm `document_count=24` |
| Trả lời câu hỏi | `data/results/*_answers.json` | Có retrieved IDs và contexts | Evaluate pipeline |

## 4. Giải Thích Kỹ Thuật

Embedding layer được thiết kế có provider factory. Với artifact hiện tại, pipeline dùng `MiniLMEmbeddings` với model `sentence-transformers/all-MiniLM-L6-v2`. Index manifest ghi provider, model, dimension, fingerprint và collection name để tránh dùng nhầm artifact cũ. QA flow search top-k trong Chroma, sau đó extract answer theo question type.

Lệnh xác minh:

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

## 5. Quyết Định Kỹ Thuật Quan Trọng

- **Bối cảnh:** Embedding index phải truy vết được model đã dùng để tạo vector.
- **Phương án:** Chỉ lưu collection Chroma hoặc lưu thêm manifest có metadata.
- **Lựa chọn:** Lưu manifest có provider, model, dimension và data fingerprint.
- **Lý do:** Tránh dùng nhầm index khi data/model thay đổi, giúp reproduce và debug tốt hơn.
- **Bằng chứng:** Manifest có `embedding_provider=minilm`, `embedding_model=sentence-transformers/all-MiniLM-L6-v2`, `embedding_dimension=384`.

## 6. Blocker Đã Xử Lý

- **Triệu chứng:** Nếu index cũ lệch manifest/config, retrieval có thể sai hoặc không load được.
- **Nguyên nhân:** Embedding artifact phụ thuộc vào provider, model và data fingerprint.
- **Cách xử lý:** Thêm manifest validation và embedding client factory.
- **Xác minh:** Build/load index thành công, manifest document count là 24 và dimension là 384.

## 7. Hiểu Biết End-to-End

RAG dùng `text_for_embedding` từ cleaning để tạo vectors. Evaluation dùng retrieved doc IDs để tính hit rate. Nếu index build sai provider/model, so sánh baseline/corrupted/repaired sẽ không công bằng. Vì vậy manifest validation là một phần quan trọng của RAG reliability.

## 8. Phân Tích Kết Quả

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.5000 | 1.0000 | MiniLM embedding retrieve tốt trên clean data |
| `mean_token_f1` | 1.0000 | 0.5168 | 1.0000 | Context sai làm answer sai |
| `judge_accuracy` | 1.0000 | 0.5000 | 1.0000 | RAG chất lượng phụ thuộc data |
| `mean_judge_score` | 5.0000 | 3.0000 | 5.0000 | Repair phục hồi index/answer |

## 9. Điều Học Được

1. Embedding provider phải được ghi vào artifact để truy vết.
2. Retrieval hit rate là chỉ số trực tiếp cho chất lượng index.
3. Data corruption có thể làm RAG kém ngay cả khi model/agent không đổi.

## 10. Cam Kết

- [x] Báo cáo phản ánh đúng phần việc.
- [x] Kết luận có artifact/metric để đối chiếu.
- [x] Không chứa secret.

**Họ và tên:** Nguyễn Đặng Thành Vinh  
**Ngày xác nhận:** 06/08/2026