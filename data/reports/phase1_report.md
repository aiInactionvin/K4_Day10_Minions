# Phase 1 Baseline Report

## Source

- Source: Crossref REST API
- Query: agentic retrieval augmented generation large language model
- Filter: from-pub-date:2026-02-07,has-abstract:true
- Raw records: 24

## Evaluation Metrics

| State | retrieval_hit_rate | mean_token_f1 | judge_accuracy | mean_judge_score |
|---|---:|---:|---:|---:|
| Baseline | 1.0000 | 1.0000 | 0.9583 | 4.8333 |

- Samples: 24
- Ragas: {'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'}

## Data Quality

- Status: pass - all checks passed
- Total rows: 24
- Signals: {'row_count': 24, 'nulls': {'paper_id': 0, 'title': 0, 'summary': 0, 'published': 0}, 'duplicates': {'paper_id': 0, 'title': 0}, 'age_days': {'max': 175, 'stale_rows': 0, 'threshold_days': 180}, 'source_timestamp_column': 'published'}

## Freshness

- is_fresh=True, latest=2026-08-05, oldest=2026-02-12, stale_rows=0/24
- Timestamp source: published

## Conclusion

Baseline artifacts establish the clean-data reference point for later corrupted and repaired comparisons.
