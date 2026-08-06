from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation import build_test_set, evaluate_pipeline
from ingestion import build_clean_dataframe, fetch_source_records, load_raw_records
from observability import build_freshness_report, generate_phase1_report, run_data_quality_checks
from retrieval.index import LocalEmbeddingIndex


def _save_dataframe(df: pd.DataFrame, csv_path: Path, json_path: Path) -> None:
    write_csv(df, csv_path)
    write_json(json_path, df.to_dict(orient="records"))


def _load_or_fetch_raw_records(settings) -> list[Any]:
    if settings.paths.raw_records_json.exists() and not settings.refresh_source:
        return load_raw_records(settings.paths.raw_records_json)
    return fetch_source_records(settings)


def _load_or_build_test_set(settings, clean_df: pd.DataFrame) -> list[dict[str, Any]]:
    if settings.paths.eval_testset.exists() and not settings.refresh_test_set:
        return read_json(settings.paths.eval_testset)
    return build_test_set(clean_df, settings.paths.eval_testset)


def main() -> None:
    """Run the clean-data baseline pipeline end-to-end."""
    settings = load_settings()
    run_date = now_utc()

    raw_records = _load_or_fetch_raw_records(settings)
    clean_df = build_clean_dataframe(raw_records, run_date=run_date)
    if clean_df.empty:
        raise RuntimeError("Cleaning produced an empty dataset; cannot build the baseline pipeline.")
    _save_dataframe(clean_df, settings.paths.clean_csv, settings.paths.clean_json)

    index = LocalEmbeddingIndex.build(
        clean_df,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )

    test_set = _load_or_build_test_set(settings, clean_df)
    evaluation = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )

    quality = run_data_quality_checks(clean_df, settings=settings, report_name="baseline_quality")
    freshness = build_freshness_report(
        clean_df,
        settings=settings,
        report_path=settings.paths.freshness_report,
    )

    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "max_results": settings.max_results,
        "raw_records": len(raw_records),
        "clean_records": len(clean_df),
        "test_samples": len(test_set),
        "collection_name": settings.baseline_collection_name,
        "raw_records_path": str(settings.paths.raw_records_json),
        "clean_csv_path": str(settings.paths.clean_csv),
        "embeddings_manifest_path": str(settings.paths.embeddings_json),
    }
    generate_phase1_report(
        settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=evaluation.summary,
        quality=quality,
        freshness=freshness,
    )

    print(f"Baseline pipeline complete: {len(clean_df)} clean records, {len(test_set)} eval samples.")
    print(f"Metrics: {settings.paths.baseline_metrics}")
    print(f"Report: {settings.paths.baseline_report}")
