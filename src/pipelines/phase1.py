from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


def _save_dataframe(df: pd.DataFrame, csv_path: Path, json_path: Path) -> None:
    write_csv(df, csv_path)
    write_json(json_path, df.to_dict(orient="records"))


def _load_or_fetch_records(settings: Settings) -> list[Any]:
    if settings.paths.raw_records_json.exists() and not settings.refresh_source:
        return load_raw_records(settings.paths.raw_records_json)
    return fetch_source_records(settings)


def _load_or_build_test_set(settings: Settings, clean_df: pd.DataFrame) -> list[dict[str, Any]]:
    if settings.paths.eval_testset.exists() and not settings.refresh_test_set:
        return read_json(settings.paths.eval_testset)
    return build_test_set(clean_df, settings.paths.eval_testset)


def _source_summary(settings: Settings, raw_count: int, clean_count: int, test_count: int) -> dict[str, Any]:
    return {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "max_results": settings.max_results,
        "raw_records": raw_count,
        "clean_records": clean_count,
        "test_samples": test_count,
        "collection_name": settings.baseline_collection_name,
        "raw_api_response": str(settings.paths.raw_api_response),
        "raw_records_json": str(settings.paths.raw_records_json),
        "clean_csv_path": str(settings.paths.clean_csv),
        "embeddings_manifest_path": str(settings.paths.embeddings_json),
    }


def _write_demo_answers(settings: Settings, index: LocalEmbeddingIndex) -> None:
    if not settings.paths.eval_testset.exists():
        return
    samples = read_json(settings.paths.eval_testset)[:3]
    answers = []
    for item in samples:
        result = answer_question(item["question"], settings=settings, index=index)
        answers.append(
            {
                "id": item["id"],
                "question": result.question,
                "answer": result.answer,
                "retrieved_doc_ids": result.retrieved_doc_ids,
                "retrieved_titles": result.retrieved_titles,
            }
        )
    write_json(settings.paths.demo_answers, answers)


def main() -> None:
    """Run the clean-data baseline pipeline end-to-end."""
    settings = load_settings()
    run_date = now_utc()

    records = _load_or_fetch_records(settings)
    clean_df = build_clean_dataframe(records, run_date=run_date)
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
    freshness = build_freshness_report(clean_df, settings=settings, report_path=settings.paths.freshness_report)
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=_source_summary(
            settings,
            raw_count=len(records),
            clean_count=len(clean_df),
            test_count=len(test_set),
        ),
        metrics=evaluation.summary,
        quality=quality,
        freshness=freshness,
    )
    _write_demo_answers(settings, index)

    print(f"Baseline pipeline complete: {len(clean_df)} clean records, {len(test_set)} eval samples.")
    print(f"Metrics: {settings.paths.baseline_metrics}")
    print(f"Report: {settings.paths.baseline_report}")
