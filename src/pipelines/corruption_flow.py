from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.corruption import corrupt_clean_dataframe, repair_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def _save_dataframe(df: pd.DataFrame, csv_path: Path, json_path: Path) -> None:
    write_csv(df, csv_path)
    write_json(json_path, df.to_dict(orient="records"))


def _ensure_baseline_artifacts(settings: Settings) -> None:
    required = [
        settings.paths.clean_csv,
        settings.paths.eval_testset,
        settings.paths.baseline_metrics,
        settings.paths.embeddings_json,
    ]
    if all(path.exists() for path in required):
        try:
            LocalEmbeddingIndex.load_for_state(settings, "baseline")
            return
        except Exception:
            pass

    from pipelines.phase1 import main as run_phase1

    run_phase1()


def _freshness_path(settings: Settings, name: str) -> Path:
    return settings.paths.quality_dir / f"{name}_freshness_report.json"


def main() -> None:
    """Run corruption, impact evaluation, raw repair and comparison reporting."""
    settings = load_settings()
    _ensure_baseline_artifacts(settings)

    baseline_metrics = read_json(settings.paths.baseline_metrics)
    clean_df = pd.read_csv(settings.paths.clean_csv)
    if clean_df.empty:
        raise RuntimeError("Baseline clean dataset is empty; cannot run corruption flow.")

    corrupted_df = corrupt_clean_dataframe(clean_df, output_log_path=settings.paths.corruption_log)
    _save_dataframe(corrupted_df, settings.paths.corrupted_clean_csv, settings.paths.corrupted_clean_json)
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df,
        settings=settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )
    corrupted_evaluation = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    corrupted_quality = run_data_quality_checks(
        corrupted_df,
        settings=settings,
        report_name="corrupted_quality",
    )
    corrupted_freshness = build_freshness_report(
        corrupted_df,
        settings=settings,
        report_path=_freshness_path(settings, "corrupted"),
    )

    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = repair_clean_dataframe(raw_records, run_date=now_utc())
    if repaired_df.empty:
        raise RuntimeError("Repair produced an empty dataset; cannot evaluate repaired state.")
    _save_dataframe(repaired_df, settings.paths.repaired_clean_csv, settings.paths.repaired_clean_json)
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df,
        settings=settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )
    repaired_evaluation = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_quality = run_data_quality_checks(
        repaired_df,
        settings=settings,
        report_name="repaired_quality",
    )
    repaired_freshness = build_freshness_report(
        repaired_df,
        settings=settings,
        report_path=_freshness_path(settings, "repaired"),
    )

    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_evaluation.summary,
        repaired_metrics=repaired_evaluation.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )

    print("Corruption flow complete.")
    print(f"Corrupted metrics: {settings.paths.corrupted_metrics}")
    print(f"Repaired metrics: {settings.paths.repaired_metrics}")
    print(f"Comparison report: {settings.paths.comparison_report}")
