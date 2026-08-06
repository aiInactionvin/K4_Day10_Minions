from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


QUESTION_TYPES = ("summary", "authors", "date", "categories")


def _clean_value(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _pick_rows(df: pd.DataFrame, limit: int = 6) -> pd.DataFrame:
    required = {"paper_id", "title", "summary", "authors_joined", "categories_joined", "published"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Cleaned dataframe is missing required columns for test set: {sorted(missing)}")

    candidates = df.copy()
    for column in required:
        candidates[column] = candidates[column].map(_clean_value)
    candidates = candidates[
        (candidates["paper_id"] != "")
        & (candidates["title"] != "")
        & (candidates["summary"] != "")
        & (candidates["authors_joined"] != "")
        & (candidates["categories_joined"] != "")
        & (candidates["published"] != "")
    ].drop_duplicates(subset=["paper_id"])

    if len(candidates) < 3:
        raise ValueError("Need at least 3 valid cleaned papers to build a useful evaluation test set.")

    if "age_days" in candidates.columns:
        candidates = candidates.sort_values(["age_days", "title"], ascending=[True, True])
    else:
        candidates = candidates.sort_values("title")
    return candidates.head(limit)


def _question_rows(row: pd.Series, ordinal: int) -> list[dict[str, Any]]:
    paper_id = _clean_value(row["paper_id"])
    title = _clean_value(row["title"])
    doc_ids = [paper_id]

    return [
        {
            "id": f"q{ordinal:03d}-summary",
            "question_type": "summary",
            "question": f"What is the paper '{title}' about?",
            "ground_truth": first_sentence(_clean_value(row["summary"])),
            "ground_truth_doc_ids": doc_ids,
        },
        {
            "id": f"q{ordinal:03d}-authors",
            "question_type": "authors",
            "question": f"Who authored the paper '{title}'?",
            "ground_truth": _clean_value(row["authors_joined"]),
            "ground_truth_doc_ids": doc_ids,
        },
        {
            "id": f"q{ordinal:03d}-date",
            "question_type": "date",
            "question": f"When was the paper '{title}' published?",
            "ground_truth": _clean_value(row["published"]),
            "ground_truth_doc_ids": doc_ids,
        },
        {
            "id": f"q{ordinal:03d}-categories",
            "question_type": "categories",
            "question": f"What categories are listed for the paper '{title}'?",
            "ground_truth": _clean_value(row["categories_joined"]),
            "ground_truth_doc_ids": doc_ids,
        },
    ]

def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Create factual evaluation questions from the cleaned Crossref dataframe."""
    test_set: list[dict[str, Any]] = []
    for ordinal, (_, row) in enumerate(_pick_rows(df).iterrows(), start=1):
        test_set.extend(_question_rows(row, ordinal))

    for item in test_set:
        if item["question_type"] not in QUESTION_TYPES:
            raise ValueError(f"Unsupported question_type: {item['question_type']}")
        if not item["ground_truth_doc_ids"] or not all(item["ground_truth_doc_ids"]):
            raise ValueError(f"Missing ground_truth_doc_ids for {item['id']}")

    write_json(output_path, test_set)
    return test_set
