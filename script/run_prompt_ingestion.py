from __future__ import annotations

import argparse

from pipelines.prompt_ingestion import run_prompt_ingestion


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Find papers from a natural-language prompt, ingest them into the local "
            "Crossref source, rebuild the RAG index, and answer from the updated corpus."
        )
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        help="Natural-language description of the papers to discover.",
    )
    parser.add_argument(
        "--question",
        help="Question for the updated RAG corpus. Defaults to the discovery prompt.",
    )
    parser.add_argument("--limit", type=int, help="Maximum papers to ingest.")
    parser.add_argument(
        "--candidates",
        type=int,
        help="Number of lexical Crossref candidates to fetch before embedding rerank.",
    )
    parser.add_argument(
        "--filter",
        default="has-abstract:true",
        dest="crossref_filter",
        help="Crossref filter expression (default: has-abstract:true).",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Use deterministic local retrieval output instead of an external LLM agent.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    prompt = args.prompt or input("Mô tả tài liệu cần tìm: ").strip()
    result = run_prompt_ingestion(
        prompt,
        question=args.question,
        limit=args.limit,
        candidate_count=args.candidates,
        crossref_filter=args.crossref_filter,
        use_llm_agent=not args.no_llm,
    )

    print(f"Crossref candidates: {result.candidates_found}")
    print(f"Selected / newly added: {result.selected_count} / {result.new_source_records}")
    print(f"Source / clean records: {result.total_source_records} / {result.total_clean_records}")
    print("Selected papers:")
    for paper in result.selected_papers:
        print(
            f"  {paper['rank']}. {paper['title']} "
            f"(score={paper['semantic_score']:.4f}, id={paper['paper_id']})"
        )
    print("\nRAG answer:\n")
    print(result.answer)
    print(f"\nRun artifact: {result.run_result_path}")


if __name__ == "__main__":
    main()
