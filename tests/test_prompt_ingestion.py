from __future__ import annotations

from datetime import UTC, datetime
import math
from pathlib import Path
from unittest.mock import patch

from core.config import load_settings
from ingestion.crossref import (
    CrossrefSearchBatch,
    PaperRecord,
    load_raw_records,
    merge_raw_records,
    save_raw_records,
    search_crossref_by_prompt,
)
from pipelines.prompt_ingestion import run_prompt_ingestion
from retrieval.discovery import chunk_text, semantic_rerank_records
from retrieval.index import LocalEmbeddingIndex, SearchResult


class FakeEmbeddings:
    @staticmethod
    def _vector(text: str) -> list[float]:
        lowered = text.casefold()
        vector = [
            float(lowered.count("retrieval") + lowered.count("rag")),
            float(lowered.count("banana")),
            0.1,
        ]
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]


def _record(paper_id: str, title: str, summary: str) -> PaperRecord:
    return PaperRecord(
        paper_id=paper_id,
        title=title,
        summary=summary,
        authors=["Test Author"],
        categories=["Computer Science"],
        primary_category="Computer Science",
        published="2025-01-01",
        updated="2025-01-02",
        abs_url=f"https://doi.org/{paper_id.removeprefix('doi:')}",
        pdf_url="",
        comment="Test Publisher",
    )


def test_chunk_and_semantic_rerank() -> None:
    assert chunk_text(
        "one two three four five six seven",
        chunk_words=4,
        overlap_words=2,
    ) == ["one two three four", "three four five six", "five six seven"]

    banana = _record("doi:10.1/banana", "Banana Forecasting", "Banana harvest prediction.")
    rag = _record(
        "doi:10.1/rag",
        "Reliable Retrieval Systems",
        "Retrieval augmented generation and RAG evaluation.",
    )
    ranked = semantic_rerank_records(
        "papers about retrieval augmented generation",
        [banana, rag],
        FakeEmbeddings(),  # type: ignore[arg-type]
        limit=2,
    )

    assert ranked[0].record.paper_id == rag.paper_id
    assert ranked[0].semantic_score > ranked[1].semantic_score


def test_crossref_prompt_search_and_raw_merge(tmp_path: Path) -> None:
    payload = {
        "message": {
            "items": [
                {
                    "DOI": "10.1/rag",
                    "title": ["RAG Paper"],
                    "abstract": "A retrieval augmented generation abstract.",
                    "published": {"date-parts": [[2025, 1, 1]]},
                }
            ]
        }
    }

    class FakeResponse:
        @staticmethod
        def raise_for_status() -> None:
            return None

        @staticmethod
        def json() -> dict:
            return payload

    class FakeSession:
        def __init__(self) -> None:
            self.call = None

        def get(self, url, **kwargs):
            self.call = (url, kwargs)
            return FakeResponse()

    session = FakeSession()
    settings = load_settings(tmp_path)
    batch = search_crossref_by_prompt(
        settings,
        "reliable rag",
        rows=5,
        filter_query="has-abstract:true",
        session=session,  # type: ignore[arg-type]
    )

    assert len(batch.records) == 1
    assert session.call[1]["params"] == {
        "query": "reliable rag",
        "rows": 5,
        "filter": "has-abstract:true",
    }

    old = _record("doi:10.1/rag", "Old title", "Old summary")
    merged = merge_raw_records([old], batch.records)
    assert len(merged) == 1
    assert merged[0].title == "RAG Paper"
    save_raw_records(settings.paths.raw_records_json, merged)
    assert load_raw_records(settings.paths.raw_records_json) == merged


def test_prompt_pipeline_persists_source_clean_index_trace_and_answer(tmp_path: Path) -> None:
    settings = load_settings(tmp_path)
    existing = _record("doi:10.1/existing", "Existing Vision Paper", "Vision classification work.")
    save_raw_records(settings.paths.raw_records_json, [existing])

    banana = _record("doi:10.1/banana", "Banana Forecasting", "Banana harvest prediction.")
    rag = _record(
        "doi:10.1/rag",
        "Reliable Retrieval Systems",
        "Retrieval augmented generation improves factual answers. More evaluation follows.",
    )
    batch = CrossrefSearchBatch(
        prompt="retrieval augmented generation",
        payload={"message": {"items": []}},
        records=[banana, rag],
    )

    class StubIndex:
        def __init__(self, dataframe) -> None:
            self.documents = LocalEmbeddingIndex._build_documents(dataframe)

        def search(self, query: str, top_k=None) -> list[SearchResult]:
            document = next(doc for doc in self.documents if doc["paper_id"] == "doi:10.1/rag")
            return [
                SearchResult(
                    paper_id=document["paper_id"],
                    title=document["title"],
                    score=0.99,
                    content=document["content"],
                    metadata=document["metadata"],
                )
            ]

    with patch(
        "pipelines.prompt_ingestion.search_crossref_by_prompt",
        return_value=batch,
    ), patch(
        "pipelines.prompt_ingestion.MiniLMEmbeddings",
        return_value=FakeEmbeddings(),
    ), patch(
        "pipelines.prompt_ingestion.LocalEmbeddingIndex.build_for_state",
        side_effect=lambda dataframe, active_settings, state: StubIndex(dataframe),
    ) as build_index:
        result = run_prompt_ingestion(
            "retrieval augmented generation",
            question="What does the new RAG paper improve?",
            settings=settings,
            limit=1,
            candidate_count=2,
            use_llm_agent=False,
            run_date=datetime(2026, 8, 6, tzinfo=UTC),
        )

    assert result.selected_papers[0]["paper_id"] == rag.paper_id
    assert result.new_source_records == 1
    assert result.total_source_records == 2
    assert result.total_clean_records == 2
    assert result.retrieved_doc_ids == [rag.paper_id]
    assert result.answer == "Retrieval augmented generation improves factual answers."
    assert Path(result.raw_response_path).exists()
    assert settings.paths.raw_records_json.exists()
    assert settings.paths.clean_csv.exists()
    assert settings.paths.clean_json.exists()
    assert settings.paths.prompt_ingestion_result.exists()
    assert {record.paper_id for record in load_raw_records(settings.paths.raw_records_json)} == {
        existing.paper_id,
        rag.paper_id,
    }
    assert build_index.call_args.args[2] == "baseline"
