import hashlib

import numpy as np

from embeddings.provider import EmbeddingProvider


class FakeEmbeddingProvider(EmbeddingProvider):
    def __init__(self, dimension: int = 8, model_name: str = "fake") -> None:
        self._dimension = dimension
        self._model_name = model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_id(self) -> str:
        return f"fake:{self._model_name}:{self._dimension}"

    def embed(self, text: str) -> np.ndarray:
        return self._normalize(self._vector(text))

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self._dimension), dtype=np.float32)

        return self._normalize(np.stack([self._vector(text) for text in texts]))

    def embed_query(self, query: str) -> np.ndarray:
        return self.embed(query)

    def _vector(self, text: str) -> np.ndarray:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        bytes_ = np.frombuffer(digest, dtype=np.uint8).astype(np.float32)
        values = (bytes_ - 127.5) / 127.5

        if values.size < self._dimension:
            values = np.resize(values, self._dimension)

        return values[: self._dimension]

    def _normalize(self, vectors: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(vectors, axis=-1, keepdims=True)
        return vectors / np.maximum(norms, 1e-8)
