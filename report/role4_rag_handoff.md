# Role 4 — RAG & Agent Owner (nhóm 5 người)

## 1. Phạm vi sở hữu

Role 4 chịu trách nhiệm cho khối `src/retrieval/`:

- tạo embedding bằng `sentence-transformers/all-MiniLM-L6-v2`;
- lưu và truy vấn vector trong ChromaDB;
- exact lookup theo `paper_id` hoặc title;
- deterministic RAG QA dùng cho evaluation;
- LangChain agent dùng semantic-search/lookup tools trước khi trả lời;
- giữ ba trạng thái `baseline`, `corrupted`, `repaired` tách biệt và có thể audit.

Evaluation metrics trong `src/evaluation/metrics.py` gọi `answer_question()`, không gọi LangChain agent. Vì vậy cần gọi chính xác đây là **RAG QA evaluation**. Tool-use của agent được xác minh riêng bằng `run_agent_question_with_trace()`.

## 2. Contract nhận từ Role 2 (cleaning)

DataFrame đưa vào index phải có các cột:

| Cột | Điều kiện |
| --- | --- |
| `paper_id` | Không rỗng; giữ ổn định qua ba trạng thái |
| `title` | Không rỗng |
| `text_for_embedding` | Không rỗng; nội dung thực sự dùng để embed |
| `published` | Date/string; index chuẩn hóa thành ISO string |
| `authors_joined` | String hoặc null |
| `categories_joined` | String hoặc null |
| `summary` | String hoặc null; blank corruption được giữ để đo impact |
| `abs_url` | String hoặc null |
| `pdf_url` | String hoặc null |

`None`, `NaN`, `NaT` và `Timestamp` trong metadata được chuẩn hóa trước khi gửi vào Chroma. Ba trường `paper_id`, `title`, `text_for_embedding` không được null/blank.

## 3. API bàn giao cho Role 5 (pipeline integration)

Luôn dùng API có `state` rõ ràng:

```python
baseline_index = LocalEmbeddingIndex.build_for_state(clean_df, settings, "baseline")
corrupted_index = LocalEmbeddingIndex.build_for_state(corrupted_df, settings, "corrupted")
repaired_index = LocalEmbeddingIndex.build_for_state(repaired_df, settings, "repaired")
```

Load lại artifact:

```python
baseline_index = LocalEmbeddingIndex.load_for_state(settings, "baseline")
corrupted_index = LocalEmbeddingIndex.load_for_state(settings, "corrupted")
repaired_index = LocalEmbeddingIndex.load_for_state(settings, "repaired")
```

Mapping output:

| State | Collection | Manifest |
| --- | --- | --- |
| Baseline | `papers-baseline` | `data/embeddings/papers_embeddings.json` |
| Corrupted | `papers-corrupted` | `data/embeddings/papers_embeddings_corrupted.json` |
| Repaired | `papers-repaired` | `data/embeddings/papers_embeddings_repaired.json` |

Không dùng lời gọi mặc định `build(df, settings)` trong corruption/repair flow vì mặc định đó dành cho baseline.

## 4. Checklist theo checkpoint

### CP0 — Contract và cấu hình

- [x] Đọc `embeddings.py`, `index.py`, `llm.py`, `agent.py`, `qa.py`.
- [x] Chốt model MiniLM, `top_k=4`, collection names và metadata.
- [x] Xác định query cố định từ dữ liệu thật: `multistage retrieval augmented generation for oil and gas safety reports`.

### CP1 — Quality gate trước index

- [x] Validate đủ chín cột đầu vào.
- [x] Chặn dataframe rỗng và `paper_id`/`title`/`text_for_embedding` rỗng.
- [x] Chuẩn hóa metadata pandas thành Chroma-safe strings.
- [x] Chạy gate trên ba CSV thật: baseline/repaired không trùng ID; corrupted có ba duplicate đúng theo corruption log; không có embedding text rỗng.

### CP2 — Baseline index và smoke test

- [x] MiniLM thật trả vector 384 chiều, norm `1.0`.
- [x] Chroma semantic search, exact lookup và manifest validation chạy qua test.
- [x] Manifest có schema version, model, dimension, document count và SHA-256 fingerprint.
- [x] Build `papers-baseline` từ 24 dòng cleaned dataset thật.

### CP3 — Baseline và agent

- [x] Tool output chứa ID, citation token, title, score, authors, date, categories và URL.
- [x] Agent prompt yêu cầu dùng tool, không trả lời từ memory và không bịa nguồn.
- [x] Live smoke test dùng OpenAI đã gọi `lookup_paper`; trace có một tool call và một tool output.
- [x] Chạy verifier và live agent trên baseline artifact thật; agent gọi `lookup_paper` và trích đúng tác giả/ID SafeRAG.

### CP4 — Query so sánh

- [x] Khóa query `multistage retrieval augmented generation for oil and gas safety reports` cho cả ba trạng thái.

### CP5 — Corrupted index

- [x] API state tạo collection/manifest riêng và không mutate baseline.
- [x] Smoke test thật: corrupted query chuyển top-1 từ paper RAG sang paper khác.
- [x] Build `papers-corrupted` từ 24 dòng thật; paper SafeRAG bị drop và duplicate xuất hiện hai lần trong top-3.

### CP6 — Repaired index

- [x] API state tạo collection/manifest repaired riêng.
- [x] Smoke test thật: repaired phục hồi đúng top-1 và score baseline; fingerprint baseline không đổi.
- [x] Verifier xác nhận đủ ba collection/manifest thật; repaired có fingerprint và ranking giống baseline.

Các ô chưa đánh dấu là dependency tích hợp, không phải TODO còn lại trong `src/retrieval/`.

## 5. Bằng chứng đã xác minh

Unit/integration tests offline:

```bash
uv run --extra dev pytest -q
```

Kết quả test riêng Role 4: `10 passed, 10 subtests passed`. Sau khi pull code của nhóm, toàn bộ suite đạt `15 passed, 10 subtests passed`.

Test dùng MiniLM và Chroma thật trên dữ liệu vừa pull:

```text
baseline  -> doi:10.2118/234689-pa                 score 0.464043
corrupted -> doi:10.20944/preprints202604.0339.v1 score 0.359579
repaired  -> doi:10.2118/234689-pa                 score 0.464043
collections = papers-baseline, papers-corrupted, papers-repaired
baseline fingerprint = repaired fingerprint
```

Live agent smoke test:

```text
used_tools = true
tool_calls = [lookup_paper]
tool_outputs = 1
answer = Qianwen Cao, Chiyu Zhang, Junxiong Ning, Gongru Li [doi:10.2118/234689-pa]
```

Không ghi API key hoặc nội dung `.env` vào artifact/report.

## 6. Xác minh artifact thật sau khi tích hợp

Baseline:

```bash
uv run python script/verify_rag_artifacts.py \
  --state baseline \
  --query "multistage retrieval augmented generation for oil and gas safety reports"
```

Ba trạng thái:

```bash
uv run python script/verify_rag_artifacts.py \
  --state all \
  --query "multistage retrieval augmented generation for oil and gas safety reports"
```

Agent và trace tool-use:

```bash
uv run python script/verify_rag_artifacts.py \
  --state baseline \
  --query "multistage retrieval augmented generation for oil and gas safety reports" \
  --agent-question "Who authored SafeRAG? Cite its paper ID."
```

Verifier phải báo đúng collection, document count, embedding model/dimension, fingerprint và ranked results. Chỉ đánh dấu các checkpoint tích hợp hoàn tất sau khi các lệnh trên chạy trên artifact thật.

## 7. Blocker ngoài phạm vi Role 4 tại thời điểm bàn giao

Raw, clean, corrupted và repaired datasets đã có. Ba embedding manifest và Chroma collections chính thức cũng đã được tạo. Hai module orchestration `src/pipelines/phase1.py` và `src/pipelines/corruption_flow.py` vẫn còn `NotImplementedError`, nên chưa thể tạo bộ metrics/report end-to-end chính thức bằng hai entrypoint của nhóm.
