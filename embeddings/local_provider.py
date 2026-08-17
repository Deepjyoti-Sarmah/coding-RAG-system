import numpy as np
from sentence_transformers import SentenceTransformer

from embeddings.provider import EmbeddingProvider


class LocalEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str | None = None,
    ) -> None:
        self._model = SentenceTransformer(model_name, device=device)
        self._dimension = self._model.get_sentence_embedding_dimension()

    @property
    def dimension(self) -> int:
        return self._dimension

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