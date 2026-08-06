from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import html
import json
import logging
from pathlib import Path
import re
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from core.config import Settings

logger = logging.getLogger(__name__)
CROSSREF_WORKS_URL = "https://api.crossref.org/works"
USER_AGENT = "MinionsDataObservabilityLab/1.0 (mailto:student@lab.local)"


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


@dataclass(frozen=True)
class CrossrefSearchBatch:
    """Raw and parsed results returned by one prompt-driven Crossref search."""

    prompt: str
    payload: dict[str, Any]
    records: list[PaperRecord]


def _clean_text(text: str | None) -> str:
    """Clean HTML/XML tags, unescape entities, and normalize whitespace."""
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_date(date_dict: dict[str, Any] | None) -> str:
    """Parse Crossref date-parts into YYYY-MM-DD string format."""
    if not isinstance(date_dict, dict):
        return ""
    date_parts = date_dict.get("date-parts")
    if isinstance(date_parts, list) and date_parts and isinstance(date_parts[0], list) and date_parts[0]:
        parts = date_parts[0]
        year = parts[0] if len(parts) > 0 and parts[0] is not None else 1970
        month = parts[1] if len(parts) > 1 and parts[1] is not None else 1
        day = parts[2] if len(parts) > 2 and parts[2] is not None else 1
        return f"{year:04d}-{month:02d}-{day:02d}"
    return ""


def parse_crossref_payload(payload: dict[str, Any]) -> list[PaperRecord]:
    """Parse Crossref payload into a list of standardized PaperRecord.

    Extracts DOI, title, abstract (summary), authors, subject categories,
    dates, and URLs from Crossref items payload.
    """
    message = payload.get("message", {})
    items = message.get("items", []) if isinstance(message, dict) else []
    records: list[PaperRecord] = []

    for item in items:
        if not isinstance(item, dict):
            continue

        doi = str(item.get("DOI", "")).strip()

        # Extract title
        titles = item.get("title", [])
        if isinstance(titles, list) and titles:
            title_text = str(titles[0])
        elif isinstance(titles, str):
            title_text = titles
        else:
            title_text = ""
        title = _clean_text(title_text)

        # Skip invalid records without a title
        if not title:
            continue

        # Extract summary / abstract
        summary = _clean_text(item.get("abstract", ""))

        # Extract authors
        authors: list[str] = []
        raw_authors = item.get("author", [])
        if isinstance(raw_authors, list):
            for author in raw_authors:
                if isinstance(author, dict):
                    given = str(author.get("given", "")).strip()
                    family = str(author.get("family", "")).strip()
                    name = str(author.get("name", "")).strip()
                    if given and family:
                        full_name = f"{given} {family}"
                    elif family:
                        full_name = family
                    elif given:
                        full_name = given
                    elif name:
                        full_name = name
                    else:
                        full_name = ""
                    if full_name:
                        authors.append(full_name)

        # Extract categories / subject
        categories: list[str] = []
        raw_subjects = item.get("subject", [])
        if isinstance(raw_subjects, list):
            for s in raw_subjects:
                cleaned_subj = _clean_text(str(s))
                if cleaned_subj:
                    categories.append(cleaned_subj)

        primary_category = categories[0] if categories else "Crossref"

        # Extract dates
        published = (
            _parse_date(item.get("published-online"))
            or _parse_date(item.get("published-print"))
            or _parse_date(item.get("published"))
            or _parse_date(item.get("issued"))
            or _parse_date(item.get("created"))
        )
        updated = (
            _parse_date(item.get("deposited"))
            or _parse_date(item.get("indexed"))
            or published
        )

        # Generate stable paper_id
        if doi:
            paper_id = f"doi:{doi}"
        else:
            hash_suffix = hashlib.md5(title.encode("utf-8")).hexdigest()[:12]
            paper_id = f"crossref:{hash_suffix}"

        # Extract URLs
        abs_url = str(item.get("URL", "")).strip()
        if not abs_url and doi:
            abs_url = f"https://doi.org/{doi}"

        pdf_url = ""
        links = item.get("link", [])
        if isinstance(links, list):
            for link in links:
                if isinstance(link, dict) and link.get("content-type") == "application/pdf":
                    pdf_url = str(link.get("URL", "")).strip()
                    break

        publisher = str(item.get("publisher", "")).strip()
        work_type = str(item.get("type", "")).strip()
        comment = publisher or work_type or "Crossref work"

        record = PaperRecord(
            paper_id=paper_id,
            title=title,
            summary=summary,
            authors=authors,
            categories=categories,
            primary_category=primary_category,
            published=published,
            updated=updated,
            abs_url=abs_url,
            pdf_url=pdf_url,
            comment=comment,
        )
        records.append(record)

    return records


def _build_crossref_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=True,
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def _get_crossref_payload(
    *,
    query: str,
    rows: int,
    filter_query: str | None,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Crossref query must be a non-empty string.")
    if isinstance(rows, bool) or not isinstance(rows, int) or not 1 <= rows <= 1000:
        raise ValueError("Crossref rows must be an integer between 1 and 1000.")

    params: dict[str, Any] = {
        "query": query.strip(),
        "rows": rows,
    }
    if filter_query and filter_query.strip():
        params["filter"] = filter_query.strip()

    client = session or _build_crossref_session()
    response = client.get(
        CROSSREF_WORKS_URL,
        params=params,
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Crossref returned a non-object JSON payload.")
    return payload


def search_crossref_by_prompt(
    settings: Settings,
    prompt: str,
    *,
    rows: int | None = None,
    filter_query: str = "has-abstract:true",
    session: requests.Session | None = None,
) -> CrossrefSearchBatch:
    """Search Crossref with prompt text without mutating the persisted source.

    Crossref accepts lexical text queries rather than embedding vectors. Semantic
    embedding reranking is intentionally performed after this candidate-fetch step.
    """
    requested_rows = rows if rows is not None else min(1000, max(settings.max_results * 3, 24))
    payload = _get_crossref_payload(
        query=prompt,
        rows=requested_rows,
        filter_query=filter_query,
        session=session,
    )
    return CrossrefSearchBatch(
        prompt=prompt.strip(),
        payload=payload,
        records=parse_crossref_payload(payload),
    )


def merge_raw_records(
    existing: list[PaperRecord],
    incoming: list[PaperRecord],
) -> list[PaperRecord]:
    """Merge new source records by stable paper id; newer input wins in place."""
    merged: dict[str, PaperRecord] = {}
    for record in [*existing, *incoming]:
        key = record.paper_id.strip().casefold()
        if key:
            merged[key] = record
    return list(merged.values())


def save_raw_records(path: Path, records: list[PaperRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump([asdict(record) for record in records], file, indent=2, ensure_ascii=False)
        file.write("\n")


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch records from Crossref works API with retry/backoff, save raw response and records.

    1. Builds query params from settings.
    2. Executes HTTP GET request with exponential retry backoff for 429, 503, etc.
    3. Saves raw API response JSON to `settings.paths.raw_api_response`.
    4. Parses payload into `PaperRecord` objects.
    5. Saves parsed raw records JSON to `settings.paths.raw_records_json`.
    """
    logger.info("Fetching Crossref records with query='%s', rows=%d", settings.source_query, settings.max_results)
    payload = _get_crossref_payload(
        query=settings.source_query,
        rows=settings.max_results,
        filter_query=settings.source_filter,
    )

    # Save raw API response JSON
    raw_api_path = settings.paths.raw_api_response
    raw_api_path.parent.mkdir(parents=True, exist_ok=True)
    with raw_api_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    logger.info("Saved raw Crossref API response to %s", raw_api_path)

    # Parse payload
    records = parse_crossref_payload(payload)

    # Save raw records JSON
    raw_records_path = settings.paths.raw_records_json
    raw_records_path.parent.mkdir(parents=True, exist_ok=True)
    save_raw_records(raw_records_path, records)
    logger.info("Saved %d parsed records to %s", len(records), raw_records_path)

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load JSON raw records snapshot and map back into PaperRecord instances."""
    if not path.exists():
        raise FileNotFoundError(f"Raw records file not found at {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected JSON list in {path}, got {type(data).__name__}")

    return [PaperRecord(**item) for item in data]
