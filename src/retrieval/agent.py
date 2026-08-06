from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain.agents import create_agent
from langchain.tools import tool

from core.config import Settings
from retrieval.index import LocalEmbeddingIndex
from retrieval.llm import build_llm


@dataclass(frozen=True)
class AgentRunResult:
    question: str
    answer: str
    tool_calls: list[dict[str, Any]]
    tool_outputs: list[dict[str, str]]

    @property
    def used_tools(self) -> bool:
        return bool(self.tool_calls and self.tool_outputs)


def _format_source(
    *,
    paper_id: str,
    title: str,
    content: str,
    metadata: dict[str, Any],
    score: float | None = None,
) -> str:
    fields = [
        f"paper_id: {paper_id}",
        f"citation_token: [{paper_id}]",
        f"title: {title}",
    ]
    if score is not None:
        fields.append(f"similarity_score: {score:.4f}")
    fields.extend(
        [
            f"authors: {metadata.get('authors_joined') or 'not available'}",
            f"published: {metadata.get('published') or 'not available'}",
            f"categories: {metadata.get('categories_joined') or 'not available'}",
            f"source_url: {metadata.get('abs_url') or metadata.get('pdf_url') or 'not available'}",
            f"indexed_content: {content}",
        ]
    )
    return "\n".join(fields)


def build_agent(settings: Settings, index: LocalEmbeddingIndex):
    @tool
    def semantic_search_papers(query: str, top_k: int = settings.top_k) -> str:
        """Search the local paper corpus with embeddings and return the most relevant papers."""
        results = index.search(query, top_k=top_k)
        if not results:
            return "No papers were found in the indexed corpus for this query."
        sources = []
        for result in results:
            sources.append(
                _format_source(
                    paper_id=result.paper_id,
                    title=result.title,
                    score=result.score,
                    content=result.content,
                    metadata=result.metadata,
                )
            )
        return "\n\n--- next source ---\n\n".join(sources)

    @tool
    def lookup_paper(paper_id_or_title: str) -> str:
        """Look up a paper by exact paper_id or exact title from the local corpus."""
        record = index.lookup(paper_id_or_title)
        if not record:
            return "No exact paper match found."
        return _format_source(
            paper_id=record["paper_id"],
            title=record["title"],
            content=record["content"],
            metadata=record["metadata"],
        )

    llm = build_llm(settings=settings, temperature=0.0)
    return create_agent(
        model=llm,
        tools=[semantic_search_papers, lookup_paper],
        system_prompt=(
            "Answer only about the indexed scholarly-paper corpus sourced from Crossref. "
            "For every factual question, call lookup_paper when an exact paper ID/title is available; "
            "otherwise call semantic_search_papers. Never answer a factual question from memory alone. "
            "The final answer must copy each supporting source's citation_token exactly, including square "
            "brackets. Do not cite a paper that a tool did not return. "
            "If the tool output does not support an answer, say that the indexed corpus does not contain "
            "enough evidence. Do not invent authors, dates, categories, titles, URLs, or paper IDs."
        ),
        name="paper_corpus_agent",
    )


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, (list, tuple)):
        chunks: list[str] = []
        for block in content:
            if isinstance(block, str):
                chunks.append(block)
                continue
            if isinstance(block, dict):
                text = block.get("text")
            else:
                text = getattr(block, "text", None)
            if isinstance(text, str):
                chunks.append(text)
        return "\n".join(chunk for chunk in chunks if chunk)
    return "" if content is None else str(content)


def run_agent_question_with_trace(agent: Any, question: str) -> AgentRunResult:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Agent question must be a non-empty string.")
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    if not isinstance(result, dict):
        return AgentRunResult(question=question, answer="", tool_calls=[], tool_outputs=[])
    messages = result.get("messages", [])
    if not messages:
        return AgentRunResult(question=question, answer="", tool_calls=[], tool_outputs=[])

    tool_calls: list[dict[str, Any]] = []
    tool_outputs: list[dict[str, str]] = []
    answer = ""
    for message in messages:
        raw_tool_calls = getattr(message, "tool_calls", None)
        if isinstance(raw_tool_calls, list):
            for call in raw_tool_calls:
                if isinstance(call, dict):
                    tool_calls.append(
                        {
                            "name": str(call.get("name") or ""),
                            "args": call.get("args") or {},
                            "id": str(call.get("id") or ""),
                        }
                    )

        message_type = getattr(message, "type", "")
        if message_type == "tool" or message.__class__.__name__ == "ToolMessage":
            tool_outputs.append(
                {
                    "name": str(getattr(message, "name", "") or ""),
                    "tool_call_id": str(getattr(message, "tool_call_id", "") or ""),
                    "content": _content_to_text(getattr(message, "content", "")),
                }
            )
        elif message_type in {"ai", "assistant"} or hasattr(message, "tool_calls"):
            candidate = _content_to_text(getattr(message, "content", ""))
            if candidate:
                answer = candidate

    if not answer:
        answer = _content_to_text(getattr(messages[-1], "content", messages[-1]))
    return AgentRunResult(
        question=question,
        answer=answer,
        tool_calls=tool_calls,
        tool_outputs=tool_outputs,
    )


def run_agent_question(agent: Any, question: str) -> str:
    return run_agent_question_with_trace(agent=agent, question=question).answer
