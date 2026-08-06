from __future__ import annotations

from functools import lru_cache
from typing import Any

from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from core.config import Settings, normalized_embedding_provider, require_embedding_credentials


@lru_cache(maxsize=4)
def _load_model(model_name: str) -> Any:
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


class MiniLMEmbeddings(Embeddings):
    def __init__(self, model_name: str):
        if not model_name or not model_name.strip():
            raise ValueError("model_name must be a non-empty string.")
        self.model = _load_model(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise ValueError("Every document passed to the embedding model must contain non-empty text.")
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("The embedding query must be a non-empty string.")
        embedding = self.model.encode(
            [text],
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embedding[0].tolist()


def build_embedding_client(settings: Settings) -> Embeddings:
    """Build the configured embedding client."""
    provider = normalized_embedding_provider(settings)
    if not settings.embedding_model or not settings.embedding_model.strip():
        raise ValueError("EMBEDDING_MODEL must be a non-empty string.")
    require_embedding_credentials(settings)

    if provider == "openai":
        return OpenAIEmbeddings(
            model=settings.embedding_model.strip(),
            api_key=settings.openai_api_key,
        )
    if provider == "minilm":
        return MiniLMEmbeddings(settings.embedding_model)
    raise RuntimeError(f"Unsupported embedding provider: {settings.embedding_provider}")
