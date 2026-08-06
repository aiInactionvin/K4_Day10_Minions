from __future__ import annotations

from dataclasses import dataclass
import re

from core.config import Settings
from core.utils import first_sentence, normalize_whitespace
from retrieval.index import LocalEmbeddingIndex, SearchResult


@dataclass(frozen=True)
class AnswerResult:
    question: str
    answer: str
    retrieved_doc_ids: list[str]
    retrieved_contexts: list[str]
    retrieved_titles: list[str]


def _extract_answer(question: str, top_result: SearchResult) -> str:
    lowered = question.casefold()
    metadata = top_result.metadata
    if any(phrase in lowered for phrase in ("who authored", "list the authors", "who wrote", "author")):
        answer = metadata.get("authors_joined", "")
    elif any(phrase in lowered for phrase in ("when was", "publication date", "published on", "publish date")):
        answer = metadata.get("published", "")
    elif any(phrase in lowered for phrase in ("what categories", "category", "categories", "subject", "topics")):
        answer = metadata.get("categories_joined", "")
    else:
        summary = str(metadata.get("summary") or "")
        answer = first_sentence(summary) if summary else ""
    return str(answer).strip() or "I don't know from the indexed corpus."


def _find_exact_document(question: str, index: LocalEmbeddingIndex) -> dict | None:
    """Find a known ID/title in the question without fragile quote parsing."""
    normalized_question = normalize_whitespace(question).casefold()
    candidates: list[tuple[str, dict]] = []
    for document in index.documents:
        candidates.append((normalize_whitespace(document["paper_id"]).casefold(), document))
        candidates.append((normalize_whitespace(document["title"]).casefold(), document))
    for candidate, document in sorted(candidates, key=lambda item: len(item[0]), reverse=True):
        if candidate and re.search(rf"(?<!\w){re.escape(candidate)}(?!\w)", normalized_question):
            return document
    return None


def answer_question(question: str, settings: Settings, index: LocalEmbeddingIndex, top_k: int | None = None) -> AnswerResult:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question must be a non-empty string.")
    exact = _find_exact_document(question, index)
    retrieved = index.search(question, top_k=top_k)
    if exact:
        exact_result = SearchResult(
            paper_id=exact["paper_id"],
            title=exact["title"],
            score=1.0,
            content=exact["content"],
            metadata=exact["metadata"],
        )
        exact_id = exact_result.paper_id.casefold()
        deduped = [exact_result] + [item for item in retrieved if item.paper_id.casefold() != exact_id]
        retrieved = deduped[: (top_k or settings.top_k)]
    if not retrieved:
        answer = "I don't know from the indexed corpus."
    else:
        answer = _extract_answer(question, retrieved[0])
    return AnswerResult(
        question=question,
        answer=answer,
        retrieved_doc_ids=[item.paper_id for item in retrieved],
        retrieved_contexts=[item.content for item in retrieved],
        retrieved_titles=[item.title for item in retrieved],
    )
