from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
import html
import re
from typing import Any

import pandas as pd

from ingestion.crossref import PaperRecord


CLEAN_COLUMNS = [
    "paper_id",
    "title",
    "summary",
    "authors",
    "categories",
    "primary_category",
    "published",
    "updated",
    "age_days",
    "authors_joined",
    "categories_joined",
    "summary_chars",
    "text_for_embedding",
    "abs_url",
    "pdf_url",
    "comment",
]

_INVALID_TEXT_VALUES = {"n/a", "na", "none", "null", "unknown", "-"}


def normalize_text(value: Any) -> str:
    """Return a plain, single-line representation of a source text value."""
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    # Remove non-printing controls while preserving all normal Unicode text.
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_string_list(value: Any, *, default: Iterable[str] = ()) -> list[str]:
    """Normalize a list-like metadata field and remove duplicates stably."""
    if value is None:
        items: Iterable[Any] = default
    elif isinstance(value, str):
        # Semicolon and pipe are safe separators for names such as "Family, Given".
        items = re.split(r"\s*[;|]\s*", value)
    elif isinstance(value, Iterable) and not isinstance(value, (bytes, dict)):
        items = value
    else:
        items = [value]

    normalized: list[str] = []
    seen: set[str] = set()
    for item in items:
        cleaned = normalize_text(item)
        key = cleaned.casefold()
        if cleaned and key not in seen:
            normalized.append(cleaned)
            seen.add(key)
    return normalized


def build_text_for_embedding(
    title: Any,
    summary: Any,
    authors_joined: Any = "",
    categories_joined: Any = "",
) -> str:
    """Build the canonical text used by every clean/corrupted index."""
    fields = [
        ("Title", normalize_text(title)),
        ("Summary", normalize_text(summary)),
        ("Authors", normalize_text(authors_joined)),
        ("Categories", normalize_text(categories_joined)),
    ]
    return "\n".join(f"{label}: {value}" for label, value in fields if value)


def _normalize_paper_id(value: Any) -> str:
    paper_id = normalize_text(value)
    if paper_id.casefold().startswith("doi:"):
        return f"doi:{paper_id[4:].strip().lower()}"
    return paper_id


def _parse_date(value: Any) -> pd.Timestamp | pd.NaT:
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        return pd.NaT
    return parsed.normalize()


def _is_valid_required_text(value: str) -> bool:
    return bool(value) and value.casefold() not in _INVALID_TEXT_VALUES


def _empty_clean_dataframe() -> pd.DataFrame:
    return pd.DataFrame(columns=CLEAN_COLUMNS)


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Normalize raw Crossref records into a deterministic embedding-ready table.

    Invalid rows must have a usable id, title, summary and publication date. Duplicate
    ids and duplicate normalized titles are resolved by keeping the most recently
    updated, most complete record. The input records are never mutated.
    """
    run_timestamp = _parse_date(run_date)
    if pd.isna(run_timestamp):
        raise ValueError("run_date must be a valid datetime")

    cleaned_rows: list[dict[str, Any]] = []
    for record in records:
        paper_id = _normalize_paper_id(getattr(record, "paper_id", ""))
        title = normalize_text(getattr(record, "title", ""))
        summary = normalize_text(getattr(record, "summary", ""))
        published_ts = _parse_date(getattr(record, "published", ""))

        if not (
            _is_valid_required_text(paper_id)
            and _is_valid_required_text(title)
            and _is_valid_required_text(summary)
            and not pd.isna(published_ts)
        ):
            continue

        updated_ts = _parse_date(getattr(record, "updated", ""))
        if pd.isna(updated_ts):
            updated_ts = published_ts

        authors = normalize_string_list(getattr(record, "authors", []))
        raw_primary_category = normalize_text(getattr(record, "primary_category", ""))
        categories = normalize_string_list(
            getattr(record, "categories", []),
            default=[raw_primary_category] if raw_primary_category else ["Crossref"],
        )
        if not categories:
            categories = [raw_primary_category or "Crossref"]
        primary_category = raw_primary_category or categories[0]

        authors_joined = ", ".join(authors)
        categories_joined = ", ".join(categories)
        age_days = max(0, int((run_timestamp - published_ts).days))

        cleaned_rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": primary_category,
                "published": published_ts.strftime("%Y-%m-%d"),
                "updated": updated_ts.strftime("%Y-%m-%d"),
                "age_days": age_days,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "text_for_embedding": build_text_for_embedding(
                    title, summary, authors_joined, categories_joined
                ),
                "abs_url": normalize_text(getattr(record, "abs_url", "")),
                "pdf_url": normalize_text(getattr(record, "pdf_url", "")),
                "comment": normalize_text(getattr(record, "comment", "")),
                "_paper_id_key": paper_id.casefold(),
                "_title_key": re.sub(r"[^\w]+", " ", title.casefold()).strip(),
                "_published_ts": published_ts,
                "_updated_ts": updated_ts,
            }
        )

    if not cleaned_rows:
        return _empty_clean_dataframe()

    df = pd.DataFrame(cleaned_rows)
    # Put the strongest candidate first before resolving source duplicates.
    df = df.sort_values(
        ["_updated_ts", "_published_ts", "summary_chars", "paper_id"],
        ascending=[False, False, False, True],
        kind="stable",
    )
    df = df.drop_duplicates(subset=["_paper_id_key"], keep="first")
    df = df.drop_duplicates(subset=["_title_key"], keep="first")
    df = df.sort_values(
        ["_published_ts", "_updated_ts", "paper_id"],
        ascending=[False, False, True],
        kind="stable",
    )

    return df.loc[:, CLEAN_COLUMNS].reset_index(drop=True)
