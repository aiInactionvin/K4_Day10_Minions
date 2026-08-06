from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from core.config import load_settings
from core.utils import read_json
from retrieval.agent import build_agent, run_agent_question_with_trace
from retrieval.index import IndexState, LocalEmbeddingIndex


STATES: tuple[IndexState, ...] = ("baseline", "corrupted", "repaired")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate RAG manifests/Chroma collections and run one reproducible query."
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=None,
        help="Project/artifact root; defaults to this repository.",
    )
    parser.add_argument(
        "--state",
        choices=("all", *STATES),
        default="all",
        help="Index state to verify (default: all).",
    )
    parser.add_argument(
        "--query",
        default="retrieval augmented generation",
        help="Semantic query used for the smoke test.",
    )
    parser.add_argument("--top-k", type=int, default=None, help="Override retrieval top-k.")
    parser.add_argument(
        "--agent-question",
        help="Optionally run the configured LLM agent and include its tool-use trace summary.",
    )
    return parser.parse_args()


def _verify_state(settings, state: IndexState, query: str, top_k: int | None) -> dict[str, Any]:
    target = LocalEmbeddingIndex.target_for_state(settings, state)
    if not target.manifest_path.exists():
        raise FileNotFoundError(f"Missing {state} embedding manifest: {target.manifest_path}")

    manifest = read_json(target.manifest_path)
    index = LocalEmbeddingIndex.load_for_state(settings, state)
    results = index.search(query, top_k=top_k)
    return {
        "state": state,
        "manifest_path": str(target.manifest_path),
        "collection_name": index.collection_name,
        "document_count": index.collection.count(),
        "embedding_model": manifest["embedding_model"],
        "embedding_dimension": manifest["embedding_dimension"],
        "data_fingerprint": manifest["data_fingerprint"],
        "query": query,
        "results": [
            {
                "rank": rank,
                "paper_id": result.paper_id,
                "title": result.title,
                "score": round(result.score, 6),
            }
            for rank, result in enumerate(results, start=1)
        ],
        "index": index,
    }


def main() -> None:
    args = _parse_args()
    settings = load_settings(args.project_dir)
    selected_states: tuple[IndexState, ...] = STATES if args.state == "all" else (args.state,)

    reports: list[dict[str, Any]] = []
    indexes: dict[IndexState, LocalEmbeddingIndex] = {}
    for state in selected_states:
        report = _verify_state(settings, state, args.query, args.top_k)
        indexes[state] = report.pop("index")
        reports.append(report)

    output: dict[str, Any] = {"indexes": reports}
    if args.agent_question:
        if len(selected_states) != 1:
            raise ValueError("--agent-question requires one explicit --state.")
        state = selected_states[0]
        agent = build_agent(settings, indexes[state])
        trace = run_agent_question_with_trace(agent, args.agent_question)
        output["agent"] = {
            "state": state,
            "question": trace.question,
            "answer": trace.answer,
            "used_tools": trace.used_tools,
            "tool_calls": [call["name"] for call in trace.tool_calls],
            "tool_output_count": len(trace.tool_outputs),
        }
        if not trace.used_tools:
            raise RuntimeError("Agent answered without a complete tool-call/tool-output trace.")

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
