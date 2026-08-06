# Corruption Impact Report

## Metric Comparison

| State | retrieval_hit_rate | mean_token_f1 | judge_accuracy | mean_judge_score |
|---|---:|---:|---:|---:|
| Baseline | 1.0000 | 1.0000 | 1.0000 | 5 |
| Corrupted | 0.5000 | 0.5168 | 0.5000 | 3 |
| Repaired | 1.0000 | 1.0000 | 1.0000 | 5 |

## Quality Signals

| State | Quality | Freshness |
|---|---|---|
| Corrupted | fail - failed: paper_id_unique, summary_not_null, summary_length, freshness_age_days, title_duplicate_signal | is_fresh=False, latest=2026-07-03, oldest=2021-05-22, stale_rows=3/24 |
| Repaired | pass - all checks passed | is_fresh=True, latest=2026-08-05, oldest=2026-02-12, stale_rows=0/24 |

## Impact

- Retrieval hit rate changed from 1.0000 to 0.5000 after corruption, then to 1.0000 after repair.
- Mean token F1 changed from 1.0000 to 0.5168 after corruption, then to 1.0000 after repair.
- Judge accuracy changed from 1.0000 to 0.5000 after corruption, then to 1.0000 after repair.

## Conclusion

The same evaluation set is used across all states, so metric drops after corruption are evidence that bad data hurts RAG quality. Repaired metrics show whether rebuilding from clean source data restores retrieval and answer quality.
