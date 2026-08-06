from __future__ import annotations

from dataclasses import replace
import math
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from core.config import load_settings
from core.utils import read_json, write_json
from retrieval.agent import build_agent, run_agent_question, run_agent_question_with_trace
from retrieval.index import LocalEmbeddingIndex, SearchResult
from retrieval.llm import build_llm
from retrieval.qa import answer_question


class FakeEmbeddings:
    """Small deterministic embedding model for offline Chroma tests."""

    def __init__(self, model_name: str):
        self.model_name = model_name

    @staticmethod
    def _vector(text: str) -> list[float]:
        lowered = text.casefold()
        values = [
            float(lowered.count("retrieval") + lowered.count("rag")),
            float(lowered.count("banana")),
            float(lowered.count("vision") + lowered.count("image")),
            0.1,
        ]
        norm = math.sqrt(sum(value * value for value in values))
        return [value / norm for value in values]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


def sample_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "paper_id": "10.1000/rag",
                "title": "Reliable RAG Systems",
                "text_for_embedding": "Reliable retrieval augmented generation and RAG evaluation.",
                "published": "2025-01-01",
                "authors_joined": "An Nguyen, Binh Tran",
                "categories_joined": "Computer Science, Information Retrieval",
                "summary": "This paper studies reliable retrieval augmented generation. It evaluates failures.",
                "abs_url": "https://doi.org/10.1000/rag",
                "pdf_url": None,
            },
            {
                "paper_id": "10.1000/banana",
                "title": "Banana Crop Forecasting",
                "text_for_embedding": "Banana harvest and banana crop forecasting.",
                "published": pd.Timestamp("2025-02-02"),
                "authors_joined": "Chi Le",
                "categories_joined": "Agriculture",
                "summary": "This paper forecasts banana harvests.",
                "abs_url": "https://doi.org/10.1000/banana",
                "pdf_url": pd.NA,
            },
            {
                "paper_id": "10.1000/vision",
                "title": "Vision Models",
                "text_for_embedding": "Vision models for image classification.",
                "published": "2025-03-03",
                "authors_joined": "Dung Pham",
                "categories_joined": "Computer Vision",
                "summary": "This paper studies image classification.",
                "abs_url": "https://doi.org/10.1000/vision",
                "pdf_url": "https://example.test/vision.pdf",
            },
        ]
    )


class LocalEmbeddingIndexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.settings = load_settings(Path(self.temporary_directory.name))
        self.embedding_patch = patch(
            "retrieval.index.build_embedding_client",
            return_value=FakeEmbeddings(self.settings.embedding_model),
        )
        self.embedding_patch.start()
        self.addCleanup(self.embedding_patch.stop)

    def test_build_search_lookup_and_manifest_contract(self) -> None:
        index = LocalEmbeddingIndex.build_for_state(sample_dataframe(), self.settings, "baseline")

        self.assertEqual(index.collection_name, self.settings.baseline_collection_name)
        self.assertEqual(index.collection.count(), 3)
        self.assertEqual(index.search("banana harvest", top_k=1)[0].paper_id, "10.1000/banana")
        self.assertEqual(len(index.search("banana harvest", top_k=99)), 3)
        self.assertEqual(index.lookup("  RELIABLE   rag SYSTEMS  ")["paper_id"], "10.1000/rag")
        self.assertEqual(index.lookup("10.1000/RAG")["title"], "Reliable RAG Systems")
        self.assertEqual(index.lookup("missing"), None)

        for invalid_top_k in (0, -1, True, 1.5):
            with self.subTest(top_k=invalid_top_k), self.assertRaises(ValueError):
                index.search("retrieval", top_k=invalid_top_k)  # type: ignore[arg-type]

        manifest = read_json(self.settings.paths.embeddings_json)
        self.assertEqual(manifest["schema_version"], 2)
        self.assertEqual(manifest["embedding_provider"], "minilm")
        self.assertEqual(manifest["state"], "baseline")
        self.assertEqual(manifest["document_count"], 3)
        self.assertEqual(manifest["embedding_dimension"], 4)
        self.assertEqual(len(manifest["data_fingerprint"]), 64)
        self.assertEqual(manifest["documents"][1]["metadata"]["pdf_url"], "")
        self.assertEqual(manifest["documents"][1]["metadata"]["published"], "2025-02-02T00:00:00")

        loaded = LocalEmbeddingIndex.load_for_state(self.settings, "baseline")
        self.assertEqual(loaded.collection.count(), 3)

    def test_three_states_are_isolated_and_failed_rebuild_preserves_baseline(self) -> None:
        baseline_df = sample_dataframe()
        baseline = LocalEmbeddingIndex.build_for_state(baseline_df, self.settings, "baseline")
        baseline_manifest_before = self.settings.paths.embeddings_json.read_bytes()
        baseline_fingerprint = read_json(self.settings.paths.embeddings_json)["data_fingerprint"]
        baseline_ids = set(baseline.collection.get(include=[])["ids"])

        corrupted_df = baseline_df.iloc[:2].copy()
        corrupted_df.loc[0, "summary"] = ""
        corrupted_df.loc[0, "text_for_embedding"] = "noise noise noise"
        LocalEmbeddingIndex.build_for_state(corrupted_df, self.settings, "corrupted")
        LocalEmbeddingIndex.build_for_state(baseline_df, self.settings, "repaired")

        collection_names = {collection.name for collection in baseline.client.list_collections()}
        self.assertTrue(
            {
                self.settings.baseline_collection_name,
                self.settings.corrupted_collection_name,
                self.settings.repaired_collection_name,
            }.issubset(collection_names)
        )
        baseline_after = LocalEmbeddingIndex.load_for_state(self.settings, "baseline")
        self.assertEqual(baseline_after.collection.count(), 3)
        self.assertEqual(set(baseline_after.collection.get(include=[])["ids"]), baseline_ids)
        self.assertEqual(read_json(self.settings.paths.embeddings_json)["data_fingerprint"], baseline_fingerprint)
        self.assertEqual(self.settings.paths.embeddings_json.read_bytes(), baseline_manifest_before)

        invalid_df = baseline_df.copy()
        invalid_df.loc[0, "text_for_embedding"] = "  "
        with self.assertRaises(ValueError):
            LocalEmbeddingIndex.build_for_state(invalid_df, self.settings, "baseline")
        preserved = LocalEmbeddingIndex.load_for_state(self.settings, "baseline")
        self.assertEqual(preserved.collection.count(), 3)
        self.assertEqual(self.settings.paths.embeddings_json.read_bytes(), baseline_manifest_before)

    def test_dataframe_contract_rejects_empty_missing_and_blank_required_data(self) -> None:
        with self.assertRaises(ValueError):
            LocalEmbeddingIndex.build_for_state(pd.DataFrame(), self.settings, "baseline")

        missing = sample_dataframe().drop(columns=["authors_joined"])
        with self.assertRaisesRegex(ValueError, "authors_joined"):
            LocalEmbeddingIndex.build_for_state(missing, self.settings, "baseline")

        blank_id = sample_dataframe()
        blank_id.loc[0, "paper_id"] = None
        with self.assertRaisesRegex(ValueError, "paper_id"):
            LocalEmbeddingIndex.build_for_state(blank_id, self.settings, "baseline")

    def test_load_detects_manifest_collection_and_state_mismatches(self) -> None:
        index = LocalEmbeddingIndex.build_for_state(sample_dataframe(), self.settings, "baseline")
        manifest = read_json(self.settings.paths.embeddings_json)

        tampered_manifest = dict(manifest)
        tampered_manifest["document_count"] = 99
        write_json(self.settings.paths.embeddings_json, tampered_manifest)
        with self.assertRaisesRegex(ValueError, "document_count"):
            LocalEmbeddingIndex.load_for_state(self.settings, "baseline")

        write_json(self.settings.paths.embeddings_json, manifest)
        first_id = manifest["documents"][0]["record_id"]
        stored_vector = index.collection.get(ids=[first_id], include=["embeddings"])["embeddings"][0]
        index.collection.update(
            ids=[first_id],
            embeddings=[stored_vector.tolist()],
            documents=["tampered content"],
        )
        with self.assertRaisesRegex(RuntimeError, "content/metadata"):
            LocalEmbeddingIndex.load_for_state(self.settings, "baseline")

        # Restore the collection, then put the valid baseline manifest at the wrong state path.
        LocalEmbeddingIndex.build_for_state(sample_dataframe(), self.settings, "baseline")
        write_json(self.settings.paths.corrupted_embeddings_json, read_json(self.settings.paths.embeddings_json))
        with self.assertRaisesRegex(ValueError, "expected 'papers-corrupted'"):
            LocalEmbeddingIndex.load_for_state(self.settings, "corrupted")


class DeterministicQATests(unittest.TestCase):
    @staticmethod
    def _document(paper_id: str, title: str, summary: str) -> dict:
        return {
            "record_id": f"{paper_id}::0",
            "paper_id": paper_id,
            "title": title,
            "content": f"Title: {title}. Summary: {summary}",
            "metadata": {
                "paper_id": paper_id,
                "title": title,
                "published": "2025-04-05",
                "authors_joined": "A. Researcher",
                "categories_joined": "Information Retrieval",
                "summary": summary,
                "abs_url": "https://example.test/paper",
                "pdf_url": "",
            },
        }

    def test_exact_detection_handles_apostrophe_double_quotes_ids_and_boundaries(self) -> None:
        short = self._document("id-ai", "AI", "Short-title paper.")
        guide = self._document("id-guide", "A Researcher's Guide to RAG", "Guide summary. More detail.")

        class StubIndex:
            documents = [short, guide]

            @staticmethod
            def search(question: str, top_k=None) -> list[SearchResult]:
                if "chair" in question.casefold():
                    return [
                        SearchResult(
                            "id-guide",
                            guide["title"],
                            0.7,
                            guide["content"],
                            guide["metadata"],
                        )
                    ]
                return [SearchResult("id-ai", "AI", 0.7, short["content"], short["metadata"])]

        settings = SimpleNamespace(top_k=4)
        quoted = answer_question('What is "A Researcher\'s Guide to RAG" about?', settings, StubIndex())
        self.assertEqual(quoted.retrieved_doc_ids[0], "id-guide")
        self.assertEqual(quoted.answer, "Guide summary.")

        by_id = answer_question("Who authored id-guide?", settings, StubIndex())
        self.assertEqual(by_id.retrieved_doc_ids[0], "id-guide")
        self.assertEqual(by_id.answer, "A. Researcher")

        no_false_short_match = answer_question("What is chair design about?", settings, StubIndex())
        self.assertEqual(no_false_short_match.retrieved_doc_ids[0], "id-guide")
        self.assertEqual(len(no_false_short_match.retrieved_doc_ids), 1)


class AgentTests(unittest.TestCase):
    def test_agent_tools_return_auditable_metadata_and_explicit_no_hit(self) -> None:
        result = SearchResult(
            paper_id="10.1000/rag",
            title="Reliable RAG Systems",
            score=0.91,
            content="Indexed RAG content.",
            metadata={
                "authors_joined": "An Nguyen",
                "published": "2025-01-01",
                "categories_joined": "Information Retrieval",
                "abs_url": "https://doi.org/10.1000/rag",
                "pdf_url": "",
            },
        )

        class StubIndex:
            no_hits = False

            def search(self, query: str, top_k: int) -> list[SearchResult]:
                return [] if self.no_hits else [result]

            @staticmethod
            def lookup(value: str):
                return {
                    "paper_id": result.paper_id,
                    "title": result.title,
                    "content": result.content,
                    "metadata": result.metadata,
                }

        settings = SimpleNamespace(top_k=7)
        stub_index = StubIndex()
        with patch("retrieval.agent.build_llm", return_value=object()), patch(
            "retrieval.agent.create_agent", return_value="compiled-agent"
        ) as create_agent_mock:
            self.assertEqual(build_agent(settings, stub_index), "compiled-agent")

        tools = {tool.name: tool for tool in create_agent_mock.call_args.kwargs["tools"]}
        semantic_output = tools["semantic_search_papers"].invoke({"query": "rag", "top_k": 1})
        for expected in (
            "paper_id: 10.1000/rag",
            "citation_token: [10.1000/rag]",
            "authors: An Nguyen",
            "published: 2025-01-01",
            "categories: Information Retrieval",
            "source_url: https://doi.org/10.1000/rag",
        ):
            self.assertIn(expected, semantic_output)

        stub_index.no_hits = True
        no_hit_output = tools["semantic_search_papers"].invoke({"query": "unknown", "top_k": 1})
        self.assertIn("No papers were found", no_hit_output)
        self.assertIn("Never answer a factual question from memory alone", create_agent_mock.call_args.kwargs["system_prompt"])

    def test_run_agent_question_normalizes_provider_content_blocks(self) -> None:
        class StubAgent:
            @staticmethod
            def invoke(payload):
                return {
                    "messages": [
                        SimpleNamespace(
                            content=[
                                {"type": "text", "text": "Answer with citation"},
                                {"type": "text", "text": "[10.1000/rag]"},
                            ]
                        )
                    ]
                }

        self.assertEqual(
            run_agent_question(StubAgent(), "What is RAG?"),
            "Answer with citation\n[10.1000/rag]",
        )
        with self.assertRaises(ValueError):
            run_agent_question(StubAgent(), " ")

    def test_agent_trace_proves_tool_use(self) -> None:
        tool_message = type(
            "ToolMessage",
            (),
            {
                "type": "tool",
                "name": "semantic_search_papers",
                "tool_call_id": "call-1",
                "content": "paper_id: 10.1000/rag",
            },
        )()

        class StubAgent:
            @staticmethod
            def invoke(payload):
                return {
                    "messages": [
                        SimpleNamespace(
                            type="ai",
                            content="",
                            tool_calls=[
                                {
                                    "name": "semantic_search_papers",
                                    "args": {"query": "rag"},
                                    "id": "call-1",
                                }
                            ],
                        ),
                        tool_message,
                        SimpleNamespace(
                            type="ai",
                            content="RAG answer [10.1000/rag]",
                            tool_calls=[],
                        ),
                    ]
                }

        trace = run_agent_question_with_trace(StubAgent(), "What is RAG?")
        self.assertTrue(trace.used_tools)
        self.assertEqual(trace.tool_calls[0]["name"], "semantic_search_papers")
        self.assertEqual(trace.tool_outputs[0]["tool_call_id"], "call-1")
        self.assertEqual(trace.answer, "RAG answer [10.1000/rag]")


class LLMProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.settings = load_settings(Path(self.temporary_directory.name))

    def test_all_supported_provider_adapters_receive_their_own_configuration(self) -> None:
        cases = [
            (
                "gemini",
                "retrieval.llm.ChatGoogleGenerativeAI",
                {"google_api_key": "gemini-key"},
                {"google_api_key": "gemini-key"},
            ),
            (
                "openai",
                "retrieval.llm.ChatOpenAI",
                {"openai_api_key": "openai-key"},
                {"api_key": "openai-key"},
            ),
            (
                "anthropic",
                "retrieval.llm.ChatAnthropic",
                {"anthropic_api_key": "anthropic-key"},
                {"api_key": "anthropic-key"},
            ),
            (
                "openrouter",
                "retrieval.llm.ChatOpenAI",
                {"openrouter_api_key": "router-key"},
                {"api_key": "router-key", "base_url": self.settings.openrouter_base_url},
            ),
            (
                "ollama",
                "retrieval.llm.ChatOllama",
                {},
                {"base_url": self.settings.ollama_base_url},
            ),
            (
                "custom",
                "retrieval.llm.ChatOpenAI",
                {"custom_llm_base_url": "https://llm.example.test/v1", "custom_llm_api_key": None},
                {"api_key": "unused", "base_url": "https://llm.example.test/v1"},
            ),
        ]

        for provider, constructor_path, overrides, expected_kwargs in cases:
            with self.subTest(provider=provider):
                configured = replace(
                    self.settings,
                    llm_provider=provider,
                    model_name=f"model-{provider}",
                    **overrides,
                )
                sentinel = object()
                with patch(constructor_path, return_value=sentinel) as constructor:
                    self.assertIs(build_llm(configured, temperature=0.25), sentinel)
                call_kwargs = constructor.call_args.kwargs
                self.assertEqual(call_kwargs["model"], f"model-{provider}")
                self.assertEqual(call_kwargs["temperature"], 0.25)
                for key, value in expected_kwargs.items():
                    self.assertEqual(call_kwargs[key], value)

    def test_missing_model_or_credentials_fail_with_clear_error(self) -> None:
        missing_model = replace(
            self.settings,
            llm_provider="openai",
            model_name="",
            openai_api_key="key",
        )
        with self.assertRaisesRegex(RuntimeError, "LLM_MODEL"):
            build_llm(missing_model)

        missing_key = replace(
            self.settings,
            llm_provider="openai",
            model_name="gpt-test",
            openai_api_key=None,
        )
        with self.assertRaisesRegex(RuntimeError, "OPENAI_API_KEY"):
            build_llm(missing_key)


if __name__ == "__main__":
    unittest.main()
