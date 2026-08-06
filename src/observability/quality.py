from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


MIN_SUMMARY_CHARS = 80


def _missing_count(df: pd.DataFrame, column: str) -> int:
    if column not in df.columns:
        return len(df)
    values = df[column]
    return int(values.isna().sum() + values[values.notna()].astype(str).str.strip().eq("").sum())


def _status(passed: bool) -> str:
    return "pass" if passed else "fail"


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run lightweight data quality checks and save a JSON report."""
    row_count = int(len(df))
    min_expected_rows = max(3, min(settings.max_results, 10))
    paper_id_nulls = _missing_count(df, "paper_id")
    title_nulls = _missing_count(df, "title")
    summary_nulls = _missing_count(df, "summary")
    published_nulls = _missing_count(df, "published")

    duplicate_paper_ids = 0
    if "paper_id" in df.columns:
        duplicate_paper_ids = int(df["paper_id"].fillna("").astype(str).str.strip().duplicated().sum())

    duplicate_titles = 0
    if "title" in df.columns:
        duplicate_titles = int(df["title"].fillna("").astype(str).str.strip().str.lower().duplicated().sum())

    short_summaries = 0
    if "summary" in df.columns:
        short_summaries = int(df["summary"].fillna("").astype(str).str.strip().str.len().lt(MIN_SUMMARY_CHARS).sum())

    stale_rows = 0
    max_age_days = None
    if "age_days" in df.columns:
        numeric_age = pd.to_numeric(df["age_days"], errors="coerce")
        stale_rows = int(numeric_age.gt(settings.freshness_threshold_days).sum())
        max_age_days = None if numeric_age.dropna().empty else int(numeric_age.max())

    checks = {
        "row_count": {
            "status": _status(row_count >= min_expected_rows),
            "value": row_count,
            "minimum": min_expected_rows,
        },
        "paper_id_not_null": {
            "status": _status(paper_id_nulls == 0),
            "null_count": paper_id_nulls,
        },
        "paper_id_unique": {
            "status": _status(duplicate_paper_ids == 0),
            "duplicate_count": duplicate_paper_ids,
        },
        "title_not_null": {
            "status": _status(title_nulls == 0),
            "null_count": title_nulls,
        },
        "summary_not_null": {
            "status": _status(summary_nulls == 0),
            "null_count": summary_nulls,
        },
        "summary_length": {
            "status": _status(short_summaries == 0),
            "short_summary_count": short_summaries,
            "minimum_chars": MIN_SUMMARY_CHARS,
        },
        "published_not_null": {
            "status": _status(published_nulls == 0),
            "null_count": published_nulls,
        },
        "freshness_age_days": {
            "status": _status(stale_rows == 0),
            "stale_rows": stale_rows,
            "max_age_days": max_age_days,
            "threshold_days": settings.freshness_threshold_days,
        },
        "title_duplicate_signal": {
            "status": _status(duplicate_titles == 0),
            "duplicate_count": duplicate_titles,
        },
    }
    failed_checks = [name for name, result in checks.items() if result["status"] != "pass"]
    payload = {
        "report_name": report_name,
        "status": "pass" if not failed_checks else "fail",
        "total_rows": row_count,
        "failed_checks": failed_checks,
        "signals": {
            "row_count": row_count,
            "nulls": {
                "paper_id": paper_id_nulls,
                "title": title_nulls,
                "summary": summary_nulls,
                "published": published_nulls,
            },
            "duplicates": {
                "paper_id": duplicate_paper_ids,
                "title": duplicate_titles,
            },
            "age_days": {
                "max": max_age_days,
                "stale_rows": stale_rows,
                "threshold_days": settings.freshness_threshold_days,
            },
            "source_timestamp_column": "published",
        },
        "checks": checks,
    }
    write_json(settings.paths.quality_dir / f"{report_name}.json", payload)
    return payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Summarize publication-date freshness and save a JSON report."""
    total_rows = int(len(df))
    published = pd.to_datetime(df.get("published"), errors="coerce", utc=True) if "published" in df.columns else pd.Series([])
    latest = None if published.dropna().empty else published.max().date().isoformat()
    oldest = None if published.dropna().empty else published.min().date().isoformat()

    stale_rows = 0
    max_age_days = None
    if "age_days" in df.columns:
        numeric_age = pd.to_numeric(df["age_days"], errors="coerce")
        stale_rows = int(numeric_age.gt(settings.freshness_threshold_days).sum())
        max_age_days = None if numeric_age.dropna().empty else int(numeric_age.max())

    payload = {
        "latest_published": latest,
        "oldest_published": oldest,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "is_fresh": stale_rows == 0 and total_rows > 0,
        "threshold_days": settings.freshness_threshold_days,
        "max_age_days": max_age_days,
        "source_timestamp_column": "published",
    }
    write_json(report_path, payload)
    return payload
