from importlib import import_module
from typing import Any

import numpy as np

from embeddings.provider import EmbeddingProvider


class LocalEmbeddingProvider(EmbeddingProvider):
    """Sentence-transformers backend. Optional — requires `pip install symbolgraph[local]`."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str | None = None,
    ) -> None:
        try:
            # This import is deliberately lazy: sentence-transformers is an
            # optional extra, so it is not installed in the base environment.
            # Dynamic loading also keeps static analyzers from requiring an
            # optional dependency that users may not have installed.
            sentence_transformers: Any = import_module("sentence_transformers")
            SentenceTransformer: Any = sentence_transformers.SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "Local embeddings require 'sentence-transformers'. "
                "Install with: pip install symbolgraph[local]"
            ) from exc
        self._model_name = model_name
        self._model = SentenceTransformer(model_name, device=device)
        dimension = self._model.get_embedding_dimension()
        if dimension is None:
            raise ValueError(f"Model {model_name!r} did not report an embedding dimension")
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_id(self) -> str:
        return f"local:{self._model_name}:{self._dimension}"

    def embed(self, text: str) -> np.ndarray:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self._dimension), dtype=np.float32)

        return self._model.encode(
            texts,
            batch_size=32,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 100,
        ).astype(np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        return self.embed(query)
