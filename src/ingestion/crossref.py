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


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch records from Crossref works API with retry/backoff, save raw response and records.

    1. Builds query params from settings.
    2. Executes HTTP GET request with exponential retry backoff for 429, 503, etc.
    3. Saves raw API response JSON to `settings.paths.raw_api_response`.
    4. Parses payload into `PaperRecord` objects.
    5. Saves parsed raw records JSON to `settings.paths.raw_records_json`.
    """
    url = "https://api.crossref.org/works"
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    headers = {
        "User-Agent": "MinionsDataObservabilityLab/1.0 (mailto:student@lab.local)",
    }

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

    logger.info("Fetching Crossref records with query='%s', rows=%d", settings.source_query, settings.max_results)
    response = session.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()

    payload = response.json()

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
    records_data = [asdict(r) for r in records]
    with raw_records_path.open("w", encoding="utf-8") as f:
        json.dump(records_data, f, indent=2, ensure_ascii=False)
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

