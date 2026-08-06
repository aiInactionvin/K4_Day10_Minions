from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
import re
from typing import Any

import pandas as pd

from core.config import Settings, load_settings, require_llm_credentials
from core.utils import safe_slug, write_json
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import (
    load_raw_records,
    merge_raw_records,
    save_raw_records,
    search_crossref_by_prompt,
)
from retrieval.agent import build_agent, run_agent_question_with_trace
from retrieval.discovery import semantic_rerank_records
from retrieval.embeddings import MiniLMEmbeddings
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


@dataclass(frozen=True)
class PromptIngestionResult:
    prompt: str
    question: str
    candidates_found: int
    selected_count: int
    new_source_records: int
    total_source_records: int
    total_clean_records: int
    embedding_model: str
    raw_response_path: str
    raw_records_path: str
    clean_csv_path: str
    clean_json_path: str
    index_manifest_path: str
    run_result_path: str
    selected_papers: list[dict[str, Any]]
    answer: str
    retrieved_doc_ids: list[str]
    used_llm_agent: bool
    tool_calls: list[dict[str, Any]]
    tool_outputs: list[dict[str, str]]


def _write_dataframe(df: pd.DataFrame, csv_path: Path, json_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)
    # Round-tripping through pandas JSON handles numpy scalar values and preserves
    # list-valued authors/categories in the JSON artifact.
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        df.to_json(orient="records", indent=2, force_ascii=False) + "\n",
        encoding="utf-8",
    )


def _raw_response_path(settings: Settings, prompt: str, run_date: datetime) -> Path:
    aware_run_date = run_date if run_date.tzinfo is not None else run_date.replace(tzinfo=UTC)
    timestamp = aware_run_date.astimezone(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    prompt_slug = safe_slug(prompt)[:60]
    return settings.paths.prompt_search_dir / f"{timestamp}-{prompt_slug}.json"


def run_prompt_ingestion(
    prompt: str,
    *,
    question: str | None = None,
    settings: Settings | None = None,
    limit: int | None = None,
    candidate_count: int | None = None,
    crossref_filter: str = "has-abstract:true",
    use_llm_agent: bool = True,
    run_date: datetime | None = None,
) -> PromptIngestionResult:
    """Discover Crossref papers, ingest them, rebuild RAG, then answer a question."""
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Prompt must be a non-empty document description.")

    active_settings = settings or load_settings()
    selected_limit = active_settings.max_results if limit is None else limit
    if isinstance(selected_limit, bool) or not isinstance(selected_limit, int) or selected_limit < 1:
        raise ValueError("limit must be an integer greater than or equal to 1.")
    requested_candidates = (
        min(1000, max(selected_limit * 3, active_settings.max_results))
        if candidate_count is None
        else candidate_count
    )
    if (
        isinstance(requested_candidates, bool)
        or not isinstance(requested_candidates, int)
        or not 1 <= requested_candidates <= 1000
    ):
        raise ValueError("candidate_count must be an integer between 1 and 1000.")
    if requested_candidates < selected_limit:
        raise ValueError("candidate_count must be greater than or equal to limit.")
    if use_llm_agent:
        # Fail before network/data mutation when the requested final-answer mode is
        # not configured. The CLI documents --no-llm as the local fallback.
        require_llm_credentials(active_settings)

    effective_run_date = run_date or datetime.now(UTC)
    normalized_prompt = prompt.strip()
    final_question = (
        question.strip()
        if isinstance(question, str) and question.strip()
        else f"Using the indexed scholarly papers, respond to this request: {normalized_prompt}"
    )

    batch = search_crossref_by_prompt(
        active_settings,
        normalized_prompt,
        rows=requested_candidates,
        filter_query=crossref_filter,
    )
    embedding_backend = MiniLMEmbeddings(active_settings.embedding_model)
    unique_candidates = merge_raw_records([], batch.records)
    ranked_candidates = semantic_rerank_records(
        normalized_prompt,
        unique_candidates,
        embedding_backend,
        limit=requested_candidates,
    )

    # Only source rows which can survive cleaning. This prevents a high-scoring but
    # undated Crossref item from consuming one of the requested ingest slots.
    selected_ranked = []
    for ranked in ranked_candidates:
        if not build_clean_dataframe([ranked.record], effective_run_date).empty:
            selected_ranked.append(ranked)
        if len(selected_ranked) == selected_limit:
            break
    if not selected_ranked:
        raise RuntimeError("Crossref returned no embedding-ranked records that passed cleaning.")

    selected_records = [ranked.record for ranked in selected_ranked]
    existing_records = (
        load_raw_records(active_settings.paths.raw_records_json)
        if active_settings.paths.raw_records_json.exists()
        else []
    )
    existing_ids = {record.paper_id.strip().casefold() for record in existing_records}
    new_source_ids = {
        record.paper_id.strip().casefold()
        for record in selected_records
        if record.paper_id.strip().casefold() not in existing_ids
    }
    new_source_records = len(new_source_ids)
    merged_records = merge_raw_records(existing_records, selected_records)
    clean_df = build_clean_dataframe(merged_records, effective_run_date)
    if clean_df.empty:
        raise RuntimeError("The merged raw source produced an empty clean dataset.")

    raw_response_path = _raw_response_path(active_settings, normalized_prompt, effective_run_date)
    write_json(raw_response_path, batch.payload)
    save_raw_records(active_settings.paths.raw_records_json, merged_records)
    _write_dataframe(
        clean_df,
        active_settings.paths.clean_csv,
        active_settings.paths.clean_json,
    )
    index = LocalEmbeddingIndex.build_for_state(clean_df, active_settings, "baseline")

    if use_llm_agent:
        trace = run_agent_question_with_trace(
            build_agent(active_settings, index),
            final_question,
        )
        answer = trace.answer
        retrieved_doc_ids = []
        for tool_output in trace.tool_outputs:
            paper_ids = re.findall(
                r"^paper_id:\s*(.+?)\s*$",
                tool_output["content"],
                re.MULTILINE,
            )
            for paper_id in paper_ids:
                if paper_id not in retrieved_doc_ids:
                    retrieved_doc_ids.append(paper_id)
        tool_calls = trace.tool_calls
        tool_outputs = trace.tool_outputs
    else:
        deterministic = answer_question(final_question, active_settings, index)
        answer = deterministic.answer
        retrieved_doc_ids = deterministic.retrieved_doc_ids
        tool_calls = []
        tool_outputs = []

    result = PromptIngestionResult(
        prompt=normalized_prompt,
        question=final_question,
        candidates_found=len(batch.records),
        selected_count=len(selected_records),
        new_source_records=new_source_records,
        total_source_records=len(merged_records),
        total_clean_records=len(clean_df),
        embedding_model=active_settings.embedding_model,
        raw_response_path=str(raw_response_path),
        raw_records_path=str(active_settings.paths.raw_records_json),
        clean_csv_path=str(active_settings.paths.clean_csv),
        clean_json_path=str(active_settings.paths.clean_json),
        index_manifest_path=str(active_settings.paths.embeddings_json),
        run_result_path=str(active_settings.paths.prompt_ingestion_result),
        selected_papers=[
            {
                "rank": ranked.rank,
                "semantic_score": round(ranked.semantic_score, 6),
                "paper_id": ranked.record.paper_id,
                "title": ranked.record.title,
                "published": ranked.record.published,
                "source_url": ranked.record.abs_url or ranked.record.pdf_url,
            }
            for ranked in selected_ranked
        ],
        answer=answer,
        retrieved_doc_ids=retrieved_doc_ids,
        used_llm_agent=use_llm_agent,
        tool_calls=tool_calls,
        tool_outputs=tool_outputs,
    )
    write_json(active_settings.paths.prompt_ingestion_result, asdict(result))
    return result
