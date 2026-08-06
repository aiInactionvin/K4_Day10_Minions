import json
from pathlib import Path

from core.config import load_settings
from ingestion.crossref import (
    PaperRecord,
    fetch_source_records,
    load_raw_records,
    parse_crossref_payload,
)


def test_parse_crossref_payload():
    sample_payload = {
        "status": "ok",
        "message": {
            "items": [
                {
                    "DOI": "10.1016/j.artint.2024.1001",
                    "title": ["<jats:p>Agentic Retrieval-Augmented Generation</jats:p>"],
                    "abstract": "<jats:p>This paper presents an agentic RAG framework for complex querying &amp; search.</jats:p>",
                    "author": [
                        {"given": "Alice", "family": "Smith"},
                        {"given": "Bob", "family": "Jones"},
                    ],
                    "subject": ["Artificial Intelligence", "Computer Science"],
                    "published-online": {"date-parts": [[2024, 5, 12]]},
                    "deposited": {"date-parts": [[2024, 5, 15]]},
                    "URL": "https://doi.org/10.1016/j.artint.2024.1001",
                    "link": [
                        {"URL": "https://example.com/paper.pdf", "content-type": "application/pdf"}
                    ],
                    "publisher": "Elsevier",
                }
            ]
        },
    }

    records = parse_crossref_payload(sample_payload)
    assert len(records) == 1
    rec = records[0]

    assert rec.paper_id == "doi:10.1016/j.artint.2024.1001"
    assert rec.title == "Agentic Retrieval-Augmented Generation"
    assert rec.summary == "This paper presents an agentic RAG framework for complex querying & search."
    assert rec.authors == ["Alice Smith", "Bob Jones"]
    assert rec.categories == ["Artificial Intelligence", "Computer Science"]
    assert rec.primary_category == "Artificial Intelligence"
    assert rec.published == "2024-05-12"
    assert rec.updated == "2024-05-15"
    assert rec.abs_url == "https://doi.org/10.1016/j.artint.2024.1001"
    assert rec.pdf_url == "https://example.com/paper.pdf"
    assert rec.comment == "Elsevier"


def test_save_and_load_raw_records(tmp_path: Path):
    rec = PaperRecord(
        paper_id="doi:10.1000/182",
        title="Sample Title",
        summary="Sample Summary",
        authors=["Author One"],
        categories=["CS"],
        primary_category="CS",
        published="2024-01-01",
        updated="2024-01-02",
        abs_url="https://doi.org/10.1000/182",
        pdf_url="https://doi.org/10.1000/182.pdf",
        comment="Test publisher",
    )

    test_file = tmp_path / "test_records.json"
    with test_file.open("w", encoding="utf-8") as f:
        json.dump([rec.__dict__], f)

    loaded = load_raw_records(test_file)
    assert len(loaded) == 1
    assert loaded[0] == rec


def test_fetch_source_records_live():
    settings = load_settings()
    records = fetch_source_records(settings)
    assert len(records) > 0
    assert settings.paths.raw_api_response.exists()
    assert settings.paths.raw_records_json.exists()

    loaded_records = load_raw_records(settings.paths.raw_records_json)
    assert len(loaded_records) == len(records)
