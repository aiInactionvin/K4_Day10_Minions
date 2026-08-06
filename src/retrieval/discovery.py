from __future__ import annotations

from dataclasses import dataclass
import math

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord
from retrieval.embeddings import MiniLMEmbeddings


@dataclass(frozen=True)
class RankedPaper:
    record: PaperRecord
    semantic_score: float
    rank: int


def chunk_text(text: str, *, chunk_words: int = 160, overlap_words: int = 30) -> list[str]:
    """Split text into deterministic word chunks suitable for semantic matching."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Text to chunk must be a non-empty string.")
    if isinstance(chunk_words, bool) or not isinstance(chunk_words, int) or chunk_words < 1:
        raise ValueError("chunk_words must be an integer greater than or equal to 1.")
    if (
        isinstance(overlap_words, bool)
        or not isinstance(overlap_words, int)
        or overlap_words < 0
        or overlap_words >= chunk_words
    ):
        raise ValueError("overlap_words must be an integer from 0 to chunk_words - 1.")

    words = normalize_whitespace(text).split(" ")
    step = chunk_words - overlap_words
    chunks: list[str] = []
    for start in range(0, len(words), step):
        chunk = " ".join(words[start : start + chunk_words]).strip()
        if chunk:
            chunks.append(chunk)
        if start + chunk_words >= len(words):
            break
    return chunks


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or len(left) != len(right):
        raise ValueError("Embedding vectors must have the same non-zero dimension.")
    left_norm = math.sqrt(sum(float(value) ** 2 for value in left))
    right_norm = math.sqrt(sum(float(value) ** 2 for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    dot_product = sum(float(a) * float(b) for a, b in zip(left, right, strict=True))
    return max(-1.0, min(1.0, dot_product / (left_norm * right_norm)))


def semantic_rerank_records(
    prompt: str,
    records: list[PaperRecord],
    embeddings: MiniLMEmbeddings,
    *,
    limit: int,
    prompt_chunk_words: int = 80,
    document_chunk_words: int = 160,
    overlap_words: int = 20,
) -> list[RankedPaper]:
    """Embed prompt/document chunks and rerank Crossref's lexical candidates.

    Each paper receives the best cosine similarity across every prompt/document
    chunk pair. This preserves a focused match when either the prompt or abstract is
    longer than the embedding model's practical context window.
    """
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be an integer greater than or equal to 1.")

    prompt_overlap = min(overlap_words, max(0, prompt_chunk_words - 1))
    prompt_chunks = chunk_text(
        prompt,
        chunk_words=prompt_chunk_words,
        overlap_words=prompt_overlap,
    )
    prompt_vectors = [embeddings.embed_query(chunk) for chunk in prompt_chunks]

    usable_records: list[PaperRecord] = []
    chunks_by_record: list[list[str]] = []
    flat_document_chunks: list[str] = []
    for record in records:
        title = normalize_whitespace(record.title)
        summary = normalize_whitespace(record.summary)
        if not title or not summary:
            continue
        document_text = f"Title: {title}\nSummary: {summary}"
        document_overlap = min(overlap_words, max(0, document_chunk_words - 1))
        chunks = chunk_text(
            document_text,
            chunk_words=document_chunk_words,
            overlap_words=document_overlap,
        )
        usable_records.append(record)
        chunks_by_record.append(chunks)
        flat_document_chunks.extend(chunks)

    if not usable_records:
        return []

    document_vectors = embeddings.embed_documents(flat_document_chunks)
    if len(document_vectors) != len(flat_document_chunks):
        raise RuntimeError("Embedding backend returned the wrong number of document vectors.")

    scored: list[tuple[PaperRecord, float]] = []
    vector_cursor = 0
    for record, chunks in zip(usable_records, chunks_by_record, strict=True):
        record_vectors = document_vectors[vector_cursor : vector_cursor + len(chunks)]
        vector_cursor += len(chunks)
        score = max(
            _cosine_similarity(prompt_vector, document_vector)
            for prompt_vector in prompt_vectors
            for document_vector in record_vectors
        )
        scored.append((record, score))

    scored.sort(
        key=lambda item: (
            -item[1],
            item[0].paper_id.casefold(),
            item[0].title.casefold(),
        )
    )
    return [
        RankedPaper(record=record, semantic_score=score, rank=rank)
        for rank, (record, score) in enumerate(scored[:limit], start=1)
    ]
