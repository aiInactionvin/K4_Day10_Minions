from __future__ import annotations

from datetime import UTC, datetime
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from ingestion.cleaning import build_clean_dataframe, build_text_for_embedding
from ingestion.crossref import PaperRecord


_NOISE = "<<<CORRUPTED_NOISE>>> zxqv_000 NULL ???"


def _json_value(value: Any) -> Any:
    """Convert pandas/numpy values into values accepted by the stdlib JSON encoder."""
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item"):
        value = value.item()
    if value is None or isinstance(value, (str, int, float, bool, list, dict)):
        return value
    return str(value)


def _snapshot(row: pd.Series, fields: list[str] | None = None) -> dict[str, Any]:
    selected = fields or list(row.index)
    return {field: _json_value(row[field]) for field in selected if field in row.index}


def _operation_count(row_count: int) -> int:
    return max(1, math.ceil(row_count * 0.10)) if row_count else 0


def _positions(row_count: int, cursor: int, count: int) -> list[int]:
    if row_count == 0 or count == 0:
        return []
    return [(cursor + offset) % row_count for offset in range(min(count, row_count))]


def _append_event(
    events: list[dict[str, Any]],
    operation: str,
    row_position: int | None,
    paper_id: str,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
    **details: Any,
) -> None:
    event: dict[str, Any] = {
        "event_id": len(events) + 1,
        "operation": operation,
        "paper_id": paper_id,
        "row_position": row_position,
        "before": before,
        "after": after,
    }
    event.update(details)
    events.append(event)


def _rebuild_derived_columns(df: pd.DataFrame) -> None:
    df["summary_chars"] = df["summary"].fillna("").astype(str).str.len()
    df["text_for_embedding"] = df.apply(
        lambda row: build_text_for_embedding(
            row.get("title", ""),
            row.get("summary", ""),
            row.get("authors_joined", ""),
            row.get("categories_joined", ""),
        ),
        axis=1,
    )


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: str | Path) -> pd.DataFrame:
    """Create a deterministic, multi-scenario corrupted copy and an audit log.

    The function deliberately violates freshness, completeness, textual integrity and
    uniqueness. It never mutates the caller's dataframe. Every change is represented
    as an event with explicit before/after values.
    """
    required = {
        "paper_id",
        "title",
        "summary",
        "published",
        "age_days",
        "authors_joined",
        "categories_joined",
        "text_for_embedding",
    }
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Clean dataframe is missing required columns: {', '.join(missing)}")

    corrupted = df.copy(deep=True).reset_index(drop=True)
    input_rows = len(corrupted)
    events: list[dict[str, Any]] = []

    # 1. Missing newest data: remove roughly 10%, but retain at least one row.
    published = pd.to_datetime(corrupted["published"], errors="coerce", utc=True)
    latest_positions = list(published.sort_values(ascending=False, na_position="last").index)
    drop_count = min(_operation_count(input_rows), max(0, input_rows - 1))
    positions_to_drop = latest_positions[:drop_count]
    for position in positions_to_drop:
        row = corrupted.loc[position]
        _append_event(
            events,
            "drop_latest_record",
            int(position),
            str(row["paper_id"]),
            _snapshot(row),
            None,
        )
    corrupted = corrupted.drop(index=positions_to_drop).reset_index(drop=True)

    remaining = len(corrupted)
    count = _operation_count(remaining)
    cursor = 0

    # 2. Completeness corruption: erase abstracts.
    for position in _positions(remaining, cursor, count):
        before = _snapshot(corrupted.loc[position], ["summary", "summary_chars", "text_for_embedding"])
        corrupted.at[position, "summary"] = ""
        _append_event(
            events,
            "blank_summary",
            position,
            str(corrupted.at[position, "paper_id"]),
            before,
            {"summary": ""},
        )
    cursor += count

    # 3. Content corruption: inject a conspicuous, reproducible noise marker.
    for position in _positions(remaining, cursor, count):
        before = _snapshot(corrupted.loc[position], ["summary", "summary_chars", "text_for_embedding"])
        original = str(corrupted.at[position, "summary"] or "")
        corrupted.at[position, "summary"] = f"{original} {_NOISE}".strip()
        _append_event(
            events,
            "inject_summary_noise",
            position,
            str(corrupted.at[position, "paper_id"]),
            before,
            {"summary": corrupted.at[position, "summary"]},
            noise=_NOISE,
        )
    cursor += count

    # 4. Text integrity corruption: truncate enough to be visible even for short titles.
    for position in _positions(remaining, cursor, count):
        original = str(corrupted.at[position, "title"] or "")
        keep_chars = min(24, max(1, len(original) // 2))
        truncated = original[:keep_chars].rstrip() + "…"
        corrupted.at[position, "title"] = truncated
        _append_event(
            events,
            "truncate_title",
            position,
            str(corrupted.at[position, "paper_id"]),
            {"title": original},
            {"title": truncated},
            original_length=len(original),
            corrupted_length=len(truncated),
        )
    cursor += count

    # 5. Freshness corruption: shift publication dates back five calendar years.
    for position in _positions(remaining, cursor, count):
        old_date = pd.to_datetime(corrupted.at[position, "published"], errors="coerce")
        if pd.isna(old_date):
            continue
        new_date = old_date - pd.DateOffset(years=5)
        delta_days = int((old_date - new_date).days)
        old_age = int(corrupted.at[position, "age_days"])
        corrupted.at[position, "published"] = new_date.strftime("%Y-%m-%d")
        corrupted.at[position, "age_days"] = old_age + delta_days
        _append_event(
            events,
            "make_publication_stale",
            position,
            str(corrupted.at[position, "paper_id"]),
            {"published": old_date.strftime("%Y-%m-%d"), "age_days": old_age},
            {
                "published": corrupted.at[position, "published"],
                "age_days": int(corrupted.at[position, "age_days"]),
            },
            shifted_years=5,
        )
    cursor += count

    # Recompute dependent text fields before taking duplicate snapshots.
    _rebuild_derived_columns(corrupted)

    # 6. Uniqueness corruption: append exact rows, including duplicate paper_id values.
    duplicate_positions = _positions(remaining, cursor, count)
    duplicate_rows = corrupted.iloc[duplicate_positions].copy(deep=True)
    first_new_position = len(corrupted)
    for offset, (_, row) in enumerate(duplicate_rows.iterrows()):
        new_position = first_new_position + offset
        _append_event(
            events,
            "duplicate_row",
            new_position,
            str(row["paper_id"]),
            None,
            _snapshot(row),
            source_row_position=duplicate_positions[offset],
        )
    if not duplicate_rows.empty:
        corrupted = pd.concat([corrupted, duplicate_rows], ignore_index=True)

    # Ensure all events which changed text include the actual final derived values.
    _rebuild_derived_columns(corrupted)
    for event in events:
        position = event.get("row_position")
        if event["operation"] in {"blank_summary", "inject_summary_noise", "truncate_title"}:
            if isinstance(position, int) and position < len(corrupted):
                fields = ["title", "summary", "summary_chars", "text_for_embedding"]
                event["after"] = _snapshot(corrupted.loc[position], fields)

    operation_counts: dict[str, int] = {}
    for event in events:
        name = str(event["operation"])
        operation_counts[name] = operation_counts.get(name, 0) + 1

    log_payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "input_row_count": input_rows,
        "output_row_count": len(corrupted),
        "operation_counts": operation_counts,
        "noise_marker": _NOISE,
        "events": events,
    }
    output_path = Path(output_log_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(log_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return corrupted.reset_index(drop=True)


def repair_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Repair a dataset only from the trusted raw snapshot, never from corrupted rows."""
    return build_clean_dataframe(records, run_date)
