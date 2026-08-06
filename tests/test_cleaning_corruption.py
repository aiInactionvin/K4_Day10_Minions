from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

import pandas as pd

from ingestion.cleaning import CLEAN_COLUMNS, build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe, repair_clean_dataframe
from ingestion.crossref import PaperRecord


RUN_DATE = datetime(2026, 8, 6, tzinfo=UTC)


def _record(index: int, **overrides) -> PaperRecord:
    values = {
        "paper_id": f"doi:10.1000/{index}",
        "title": f"  Useful   retrieval paper {index}  ",
        "summary": f"A complete abstract for retrieval experiment number {index}.",
        "authors": [" Alice  Smith ", "Alice Smith", f"Author {index}"],
        "categories": [" Artificial Intelligence ", "Artificial Intelligence"],
        "primary_category": "Artificial Intelligence",
        "published": (RUN_DATE - timedelta(days=index + 1)).date().isoformat(),
        "updated": (RUN_DATE - timedelta(days=index)).date().isoformat(),
        "abs_url": f"https://doi.org/10.1000/{index}",
        "pdf_url": "",
        "comment": " Test publisher ",
    }
    values.update(overrides)
    return PaperRecord(**values)


def test_cleaning_normalizes_filters_and_deduplicates() -> None:
    records = [
        _record(1),
        _record(2, title="<b>Second title</b>", summary="Summary &amp; details"),
        _record(3, title="Second   title"),  # duplicate normalized title
        _record(1, updated="2026-08-06", summary="Newest duplicate wins"),
        _record(4, summary=""),
        _record(5, published="not-a-date"),
    ]

    clean = build_clean_dataframe(records, RUN_DATE)

    assert list(clean.columns) == CLEAN_COLUMNS
    assert len(clean) == 2
    assert clean["paper_id"].is_unique
    assert clean.loc[clean["paper_id"] == "doi:10.1000/1", "summary"].item() == "Newest duplicate wins"

    second = clean.loc[clean["paper_id"] == "doi:10.1000/2"].iloc[0]
    assert second["title"] == "Second title"
    assert second["summary"] == "Summary & details"
    assert second["authors"] == ["Alice Smith", "Author 2"]
    assert second["categories"] == ["Artificial Intelligence"]
    assert second["age_days"] == 3
    assert second["summary_chars"] == len(second["summary"])
    assert "Title: Second title" in second["text_for_embedding"]
    assert "Summary: Summary & details" in second["text_for_embedding"]


def test_corruption_is_logged_and_repair_restores_raw(tmp_path: Path) -> None:
    records = [_record(index) for index in range(1, 25)]
    baseline = build_clean_dataframe(records, RUN_DATE)
    baseline_copy = baseline.copy(deep=True)
    log_path = tmp_path / "corruption_log.json"

    corrupted = corrupt_clean_dataframe(baseline, log_path)
    repaired = repair_clean_dataframe(records, RUN_DATE)
    log = json.loads(log_path.read_text(encoding="utf-8"))

    pd.testing.assert_frame_equal(baseline, baseline_copy)
    pd.testing.assert_frame_equal(repaired, baseline)
    assert set(log["operation_counts"]) == {
        "drop_latest_record",
        "blank_summary",
        "inject_summary_noise",
        "truncate_title",
        "make_publication_stale",
        "duplicate_row",
    }
    assert all("before" in event and "after" in event for event in log["events"])
    assert corrupted["paper_id"].duplicated().any()
    assert corrupted["summary"].eq("").any()
    assert corrupted["summary"].str.contains("CORRUPTED_NOISE", regex=False).any()
    assert (corrupted["summary_chars"] == corrupted["summary"].str.len()).all()
    assert all(
        row["title"] in row["text_for_embedding"]
        for row in corrupted[["title", "text_for_embedding"]].to_dict(orient="records")
    )
