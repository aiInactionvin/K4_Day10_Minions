from __future__ import annotations

from typing import Any

from core.utils import write_text


METRIC_NAMES = ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score")


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    if value is None:
        return "n/a"
    return str(value)


def _metric_table(rows: list[tuple[str, dict[str, Any]]]) -> str:
    lines = ["| State | retrieval_hit_rate | mean_token_f1 | judge_accuracy | mean_judge_score |", "|---|---:|---:|---:|---:|"]
    for label, metrics in rows:
        values = [_fmt(metrics.get(name)) for name in METRIC_NAMES]
        lines.append(f"| {label} | {' | '.join(values)} |")
    return "\n".join(lines)


def _quality_summary(quality: dict[str, Any]) -> str:
    failed = quality.get("failed_checks") or []
    if not failed:
        return f"{quality.get('status', 'unknown')} - all checks passed"
    return f"{quality.get('status', 'unknown')} - failed: {', '.join(failed)}"


def _freshness_summary(freshness: dict[str, Any]) -> str:
    return (
        f"is_fresh={freshness.get('is_fresh')}, "
        f"latest={freshness.get('latest_published')}, "
        f"oldest={freshness.get('oldest_published')}, "
        f"stale_rows={freshness.get('stale_rows')}/{freshness.get('total_rows')}"
    )

def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the baseline evaluation and observability report."""
    lines = [
        "# Phase 1 Baseline Report",
        "",
        "## Source",
        "",
        f"- Source: {source_summary.get('source_api', source_summary.get('source', 'n/a'))}",
        f"- Query: {source_summary.get('source_query', source_summary.get('query', 'n/a'))}",
        f"- Filter: {source_summary.get('source_filter', source_summary.get('filter', 'n/a'))}",
        f"- Raw records: {source_summary.get('raw_records', source_summary.get('records', 'n/a'))}",
        "",
        "## Evaluation Metrics",
        "",
        _metric_table([("Baseline", metrics)]),
        "",
        f"- Samples: {metrics.get('samples', 'n/a')}",
        f"- Ragas: {_fmt(metrics.get('ragas'))}",
        "",
        "## Data Quality",
        "",
        f"- Status: {_quality_summary(quality)}",
        f"- Total rows: {quality.get('total_rows', 'n/a')}",
        f"- Signals: {_fmt(quality.get('signals'))}",
        "",
        "## Freshness",
        "",
        f"- {_freshness_summary(freshness)}",
        f"- Timestamp source: {freshness.get('source_timestamp_column', 'published')}",
        "",
        "## Conclusion",
        "",
        "Baseline artifacts establish the clean-data reference point for later corrupted and repaired comparisons.",
        "",
    ]
    write_text(report_path, "\n".join(lines))


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Write the baseline/corrupted/repaired comparison report."""
    lines = [
        "# Corruption Impact Report",
        "",
        "## Metric Comparison",
        "",
        _metric_table(
            [
                ("Baseline", baseline_metrics),
                ("Corrupted", corrupted_metrics),
                ("Repaired", repaired_metrics),
            ]
        ),
        "",
        "## Quality Signals",
        "",
        "| State | Quality | Freshness |",
        "|---|---|---|",
        f"| Corrupted | {_quality_summary(corrupted_quality)} | {_freshness_summary(corrupted_freshness)} |",
        f"| Repaired | {_quality_summary(repaired_quality)} | {_freshness_summary(repaired_freshness)} |",
        "",
        "## Impact",
        "",
        (
            f"- Retrieval hit rate changed from {_fmt(baseline_metrics.get('retrieval_hit_rate'))} "
            f"to {_fmt(corrupted_metrics.get('retrieval_hit_rate'))} after corruption, then "
            f"to {_fmt(repaired_metrics.get('retrieval_hit_rate'))} after repair."
        ),
        (
            f"- Mean token F1 changed from {_fmt(baseline_metrics.get('mean_token_f1'))} "
            f"to {_fmt(corrupted_metrics.get('mean_token_f1'))} after corruption, then "
            f"to {_fmt(repaired_metrics.get('mean_token_f1'))} after repair."
        ),
        (
            f"- Judge accuracy changed from {_fmt(baseline_metrics.get('judge_accuracy'))} "
            f"to {_fmt(corrupted_metrics.get('judge_accuracy'))} after corruption, then "
            f"to {_fmt(repaired_metrics.get('judge_accuracy'))} after repair."
        ),
        "",
        "## Conclusion",
        "",
        (
            "The same evaluation set is used across all states, so metric drops after corruption are evidence "
            "that bad data hurts RAG quality. Repaired metrics show whether rebuilding from clean source data "
            "restores retrieval and answer quality."
        ),
        "",
    ]
    write_text(report_path, "\n".join(lines))
