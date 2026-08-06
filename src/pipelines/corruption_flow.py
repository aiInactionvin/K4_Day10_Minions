from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation import evaluate_pipeline
from ingestion import corrupt_clean_dataframe, load_raw_records, repair_clean_dataframe
from observability import build_freshness_report, generate_corruption_report, run_data_quality_checks
from retrieval.index import LocalEmbeddingIndex


def _save_dataframe(df: pd.DataFrame, csv_path: Path, json_path: Path) -> None:
    write_csv(df, csv_path)
    write_json(json_path, df.to_dict(orient="records"))


def _load_clean_dataframe(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing baseline clean dataset at {path}. Run script/run_phase1.py first."
        )
    return pd.read_csv(path)


def _require_file(path: Path, guidance: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing required artifact at {path}. {guidance}")


def main() -> None:
    """Run corruption, impact evaluation, raw repair and comparison reporting."""
    settings = load_settings()
    run_date = now_utc()

    _require_file(settings.paths.baseline_metrics, "Run the baseline pipeline before corruption flow.")
    _require_file(settings.paths.eval_testset, "Run the baseline pipeline to create the fixed test set.")
    _require_file(settings.paths.raw_records_json, "Raw records are needed for repair.")

    baseline_metrics = read_json(settings.paths.baseline_metrics)
    baseline_df = _load_clean_dataframe(settings.paths.clean_csv)
    if baseline_df.empty:
        raise RuntimeError("Baseline clean dataset is empty; cannot run corruption flow.")

    corrupted_df = corrupt_clean_dataframe(baseline_df, output_log_path=settings.paths.corruption_log)
    _save_dataframe(
        corrupted_df,
        settings.paths.corrupted_clean_csv,
        settings.paths.corrupted_clean_json,
    )
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df,
        settings=settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )
    corrupted_eval = evaluate_pipeline(
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
        report_path=settings.paths.quality_dir / "corrupted_freshness_report.json",
    )

    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = repair_clean_dataframe(raw_records, run_date=run_date)
    if repaired_df.empty:
        raise RuntimeError("Repair produced an empty dataset; cannot evaluate repaired state.")
    _save_dataframe(
        repaired_df,
        settings.paths.repaired_clean_csv,
        settings.paths.repaired_clean_json,
    )
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df,
        settings=settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )
    repaired_eval = evaluate_pipeline(
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
        report_path=settings.paths.quality_dir / "repaired_freshness_report.json",
    )

    generate_corruption_report(
        settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_eval.summary,
        repaired_metrics=repaired_eval.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )

    print("Corruption flow complete.")
    print(f"Corrupted metrics: {settings.paths.corrupted_metrics}")
    print(f"Repaired metrics: {settings.paths.repaired_metrics}")
    print(f"Comparison report: {settings.paths.comparison_report}")
