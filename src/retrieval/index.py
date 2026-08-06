from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any, Literal

import chromadb
from chromadb.errors import NotFoundError
import pandas as pd

from core.config import Settings
from core.utils import normalize_whitespace, read_json, safe_slug, write_json
from retrieval.embeddings import MiniLMEmbeddings


IndexState = Literal["baseline", "corrupted", "repaired"]

REQUIRED_COLUMNS = (
    "paper_id",
    "title",
    "text_for_embedding",
    "published",
    "authors_joined",
    "categories_joined",
    "summary",
    "abs_url",
    "pdf_url",
)
REQUIRED_TEXT_COLUMNS = ("paper_id", "title", "text_for_embedding")
MANIFEST_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class SearchResult:
    paper_id: str
    title: str
    score: float
    content: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class IndexTarget:
    state: IndexState
    collection_name: str
    manifest_path: Path


def _lookup_key(value: str) -> str:
    return normalize_whitespace(value).casefold()


def _metadata_text(value: Any) -> str:
    """Convert pandas/numpy values into a Chroma-safe scalar string."""
    if value is None:
        return ""
    try:
        if bool(pd.isna(value)):
            return ""
    except (TypeError, ValueError):
        pass
    if hasattr(value, "isoformat"):
        try:
            return str(value.isoformat())
        except (TypeError, ValueError):
            pass
    return normalize_whitespace(str(value))


def _documents_fingerprint(documents: list[dict[str, Any]]) -> str:
    serialized = json.dumps(
        documents,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return sha256(serialized.encode("utf-8")).hexdigest()


class LocalEmbeddingIndex:
    def __init__(
        self,
        settings: Settings,
        collection_name: str,
        documents: list[dict[str, Any]],
        persist_path: Path,
    ):
        if not collection_name:
            raise ValueError("collection_name must not be empty.")
        if not documents:
            raise ValueError("An embedding index must contain at least one document.")

        self.settings = settings
        self.collection_name = collection_name
        self.documents = documents
        self.persist_path = persist_path
        self.embedding_backend = "chroma"
        self.embedding_model = MiniLMEmbeddings(settings.embedding_model)
        self.client = chromadb.PersistentClient(path=str(persist_path))
        self.collection = self.client.get_collection(name=collection_name)

        expected_ids = {str(document["record_id"]) for document in documents}
        stored_payload = self.collection.get(include=["documents", "metadatas"])
        stored_ids = set(stored_payload.get("ids", []))
        if stored_ids != expected_ids:
            raise RuntimeError(
                f"Chroma collection '{collection_name}' does not match its manifest: "
                f"expected {len(expected_ids)} record IDs, found {len(stored_ids)}."
            )
        stored_by_id = {
            record_id: (content, metadata)
            for record_id, content, metadata in zip(
                stored_payload.get("ids", []),
                stored_payload.get("documents") or [],
                stored_payload.get("metadatas") or [],
                strict=False,
            )
        }
        for document in documents:
            stored_content, stored_metadata = stored_by_id[document["record_id"]]
            if stored_content != document["content"] or stored_metadata != document["metadata"]:
                raise RuntimeError(
                    f"Chroma record '{document['record_id']}' does not match its manifest content/metadata."
                )
        collection_metadata = self.collection.metadata or {}
        expected_fingerprint = _documents_fingerprint(documents)
        if collection_metadata.get("embedding_model") != settings.embedding_model:
            raise RuntimeError(f"Chroma collection '{collection_name}' uses a different embedding model.")
        if collection_metadata.get("data_fingerprint") != expected_fingerprint:
            raise RuntimeError(f"Chroma collection '{collection_name}' has a different data fingerprint.")

        self.documents_by_paper_id: dict[str, dict[str, Any]] = {}
        self.documents_by_title: dict[str, dict[str, Any]] = {}
        for document in documents:
            # Keep the first occurrence deterministic when corruption introduces duplicates.
            self.documents_by_paper_id.setdefault(_lookup_key(document["paper_id"]), document)
            self.documents_by_title.setdefault(_lookup_key(document["title"]), document)

    @staticmethod
    def target_for_state(settings: Settings, state: IndexState) -> IndexTarget:
        targets = {
            "baseline": IndexTarget(
                state="baseline",
                collection_name=settings.baseline_collection_name,
                manifest_path=settings.paths.embeddings_json,
            ),
            "corrupted": IndexTarget(
                state="corrupted",
                collection_name=settings.corrupted_collection_name,
                manifest_path=settings.paths.corrupted_embeddings_json,
            ),
            "repaired": IndexTarget(
                state="repaired",
                collection_name=settings.repaired_collection_name,
                manifest_path=settings.paths.repaired_embeddings_json,
            ),
        }
        try:
            return targets[state]
        except KeyError as exc:
            raise ValueError("state must be one of: baseline, corrupted, repaired.") from exc

    @staticmethod
    def _build_documents(df: pd.DataFrame) -> list[dict[str, Any]]:
        if not isinstance(df, pd.DataFrame):
            raise TypeError("df must be a pandas DataFrame.")
        missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
        if missing_columns:
            raise ValueError(f"Clean dataframe is missing required columns: {', '.join(missing_columns)}")
        if df.empty:
            raise ValueError("Cannot build an embedding index from an empty dataframe.")

        records = df.to_dict(orient="records")
        documents: list[dict[str, Any]] = []
        for index, row in enumerate(records):
            required_values: dict[str, str] = {}
            for column in REQUIRED_TEXT_COLUMNS:
                value = _metadata_text(row[column])
                if not value:
                    raise ValueError(f"Row {index} has an empty required field: {column}.")
                required_values[column] = value

            paper_id = required_values["paper_id"]
            title = required_values["title"]
            content = required_values["text_for_embedding"]
            documents.append(
                {
                    "record_id": f"{paper_id}::{index}",
                    "paper_id": paper_id,
                    "title": title,
                    "content": content,
                    "metadata": {
                        "paper_id": paper_id,
                        "title": title,
                        "published": _metadata_text(row["published"]),
                        "authors_joined": _metadata_text(row["authors_joined"]),
                        "categories_joined": _metadata_text(row["categories_joined"]),
                        "summary": _metadata_text(row["summary"]),
                        "abs_url": _metadata_text(row["abs_url"]),
                        "pdf_url": _metadata_text(row["pdf_url"]),
                    },
                }
            )
        return documents

    @staticmethod
    def _derive_collection_name(settings: Settings, embeddings_output_path: Path | None) -> str:
        if embeddings_output_path is None:
            return settings.baseline_collection_name

        name_map = {
            settings.paths.embeddings_json.resolve(): settings.baseline_collection_name,
            settings.paths.corrupted_embeddings_json.resolve(): settings.corrupted_collection_name,
            settings.paths.repaired_embeddings_json.resolve(): settings.repaired_collection_name,
        }
        resolved_path = embeddings_output_path.resolve()
        if resolved_path in name_map:
            return name_map[resolved_path]
        return safe_slug(embeddings_output_path.stem)

    @staticmethod
    def _state_from_collection(settings: Settings, collection_name: str) -> str:
        state_by_collection = {
            settings.baseline_collection_name: "baseline",
            settings.corrupted_collection_name: "corrupted",
            settings.repaired_collection_name: "repaired",
        }
        return state_by_collection.get(collection_name, "custom")

    @staticmethod
    def _validate_embeddings(embeddings: list[list[float]], document_count: int) -> int:
        if len(embeddings) != document_count:
            raise RuntimeError(
                f"Embedding model returned {len(embeddings)} vectors for {document_count} documents."
            )
        dimensions = {len(vector) for vector in embeddings}
        if not dimensions or 0 in dimensions or len(dimensions) != 1:
            raise RuntimeError("Embedding vectors must have one consistent, non-zero dimension.")
        if any(not math.isfinite(float(value)) for vector in embeddings for value in vector):
            raise RuntimeError("Embedding vectors contain a non-finite value.")
        return dimensions.pop()

    @classmethod
    def build(
        cls,
        df: pd.DataFrame,
        settings: Settings,
        embeddings_output_path: Path | None = None,
    ) -> "LocalEmbeddingIndex":
        """Build an index, preserving the old collection if validation/embedding fails.

        Prefer ``build_for_state`` in pipeline code so the collection and manifest for
        baseline/corrupted/repaired cannot accidentally be mixed.
        """
        manifest_path = embeddings_output_path or settings.paths.embeddings_json
        collection_name = cls._derive_collection_name(settings, manifest_path)
        state = cls._state_from_collection(settings, collection_name)
        documents = cls._build_documents(df)

        # Finish all deterministic and model-dependent validation before replacing a
        # previously healthy collection.
        embedding_model = MiniLMEmbeddings(settings.embedding_model)
        embeddings = embedding_model.embed_documents([document["content"] for document in documents])
        embedding_dimension = cls._validate_embeddings(embeddings, len(documents))
        fingerprint = _documents_fingerprint(documents)

        persist_path = settings.paths.chroma_dir.resolve()
        persist_path.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(persist_path))
        try:
            client.get_collection(name=collection_name)
        except NotFoundError:
            pass
        else:
            client.delete_collection(name=collection_name)

        collection = client.create_collection(
            name=collection_name,
            metadata={
                "embedding_model": settings.embedding_model,
                "data_fingerprint": fingerprint,
                "index_state": state,
            },
            configuration={"hnsw": {"space": "cosine"}},
        )
        collection.add(
            ids=[document["record_id"] for document in documents],
            embeddings=embeddings,
            documents=[document["content"] for document in documents],
            metadatas=[document["metadata"] for document in documents],
        )
        if collection.count() != len(documents):
            raise RuntimeError(
                f"Chroma wrote {collection.count()} documents; expected {len(documents)}."
            )

        write_json(
            manifest_path,
            {
                "schema_version": MANIFEST_SCHEMA_VERSION,
                "backend": "chroma",
                "state": state,
                "embedding_model": settings.embedding_model,
                "embedding_dimension": embedding_dimension,
                "persist_path": str(persist_path),
                "collection_name": collection_name,
                "document_count": len(documents),
                "data_fingerprint": fingerprint,
                "documents": documents,
            },
        )
        return cls(
            settings=settings,
            collection_name=collection_name,
            documents=documents,
            persist_path=persist_path,
        )

    @classmethod
    def build_for_state(
        cls,
        df: pd.DataFrame,
        settings: Settings,
        state: IndexState,
    ) -> "LocalEmbeddingIndex":
        target = cls.target_for_state(settings, state)
        return cls.build(df=df, settings=settings, embeddings_output_path=target.manifest_path)

    @classmethod
    def load(cls, settings: Settings, embeddings_path: Path | None = None) -> "LocalEmbeddingIndex":
        manifest_path = embeddings_path or settings.paths.embeddings_json
        payload = read_json(manifest_path)
        required_keys = {
            "schema_version",
            "backend",
            "state",
            "embedding_model",
            "embedding_dimension",
            "persist_path",
            "collection_name",
            "document_count",
            "data_fingerprint",
            "documents",
        }
        missing_keys = sorted(required_keys.difference(payload))
        if missing_keys:
            raise ValueError(f"Embedding manifest is missing keys: {', '.join(missing_keys)}")
        if payload["schema_version"] != MANIFEST_SCHEMA_VERSION:
            raise ValueError(f"Unsupported embedding manifest schema: {payload['schema_version']}")
        if payload["backend"] != "chroma":
            raise ValueError(f"Unsupported embedding backend: {payload['backend']}")
        if payload["state"] not in {"baseline", "corrupted", "repaired", "custom"}:
            raise ValueError(f"Unsupported embedding index state: {payload['state']}")
        if payload["embedding_model"] != settings.embedding_model:
            raise ValueError(
                "Embedding model mismatch: manifest uses "
                f"'{payload['embedding_model']}', settings use '{settings.embedding_model}'."
            )
        documents = payload["documents"]
        if not isinstance(documents, list) or payload["document_count"] != len(documents):
            raise ValueError("Embedding manifest document_count does not match documents.")
        if payload["data_fingerprint"] != _documents_fingerprint(documents):
            raise ValueError("Embedding manifest fingerprint does not match its documents.")
        if not isinstance(payload["embedding_dimension"], int) or payload["embedding_dimension"] < 1:
            raise ValueError("Embedding manifest has an invalid embedding_dimension.")

        persist_path = Path(payload["persist_path"])
        if not persist_path.exists() and settings.paths.chroma_dir.exists():
            # Allow a repository/data directory to be moved after artifacts were built.
            persist_path = settings.paths.chroma_dir.resolve()
        index = cls(
            settings=settings,
            collection_name=payload["collection_name"],
            documents=documents,
            persist_path=persist_path,
        )
        stored_embeddings = index.collection.get(limit=1, include=["embeddings"]).get("embeddings")
        if stored_embeddings is None or len(stored_embeddings) != 1:
            raise RuntimeError("Chroma collection does not contain a verifiable embedding vector.")
        if len(stored_embeddings[0]) != payload["embedding_dimension"]:
            raise RuntimeError("Chroma embedding dimension does not match the manifest.")
        return index

    @classmethod
    def load_for_state(
        cls,
        settings: Settings,
        state: IndexState,
    ) -> "LocalEmbeddingIndex":
        target = cls.target_for_state(settings, state)
        index = cls.load(settings=settings, embeddings_path=target.manifest_path)
        if index.collection_name != target.collection_name:
            raise ValueError(
                f"The {state} manifest points to '{index.collection_name}', "
                f"expected '{target.collection_name}'."
            )
        return index

    def search(self, query: str, top_k: int | None = None) -> list[SearchResult]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Search query must be a non-empty string.")
        limit = self.settings.top_k if top_k is None else top_k
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("top_k must be an integer greater than or equal to 1.")
        collection_count = self.collection.count()
        if collection_count == 0:
            return []
        limit = min(limit, collection_count)

        query_embedding = self.embedding_model.embed_query(query.strip())
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            include=["documents", "metadatas", "distances"],
        )
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        scored: list[SearchResult] = []
        for record_id, content, metadata, distance in zip(ids, documents, metadatas, distances, strict=False):
            if not record_id or not metadata or content is None or distance is None:
                continue
            similarity = 1.0 - float(distance)
            scored.append(
                SearchResult(
                    paper_id=str(metadata["paper_id"]),
                    title=str(metadata["title"]),
                    score=max(0.0, min(1.0, similarity)),
                    content=str(content),
                    metadata=dict(metadata),
                )
            )
        return scored

    def lookup(self, value: str) -> dict[str, Any] | None:
        if not isinstance(value, str) or not value.strip():
            return None
        needle = _lookup_key(value)
        if needle in self.documents_by_paper_id:
            return self.documents_by_paper_id[needle]
        if needle in self.documents_by_title:
            return self.documents_by_title[needle]
        return None
