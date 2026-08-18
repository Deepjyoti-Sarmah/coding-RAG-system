import numpy as np

from chunking.symbol_chunker import SemanticChunk
from retrieval.vector_store import VectorSearchHit, VectorStore


class NumpyVectorStore(VectorStore):
    def __init__(
        self,
        entries: list[tuple[SemanticChunk, np.ndarray]] | None = None,
    ) -> None:
        self._chunks: list[SemanticChunk] = []
        self._matrix: np.ndarray | None = None

        if entries:
            self._chunks = [chunk for chunk, _ in entries]
            self._matrix = np.stack([_as_vector(vector) for _, vector in entries])

    def search(
        self,
        query_vector: np.ndarray,
        *,
        top_k: int = 5,
        relative_path: str | None = None,
    ) -> list[VectorSearchHit]:
        if self._matrix is None or not self._chunks:
            return []

        query = _as_vector(query_vector).reshape(1, -1)
        scores = (self._matrix @ query.T).ravel() / (
            np.linalg.norm(self._matrix, axis=1) * np.linalg.norm(query) + 1e-8
        )

        if relative_path is not None:
            scores = np.where(
                np.array(
                    [chunk.relative_path == relative_path for chunk in self._chunks]
                ),
                scores,
                -np.inf,
            )

        order = np.argsort(scores)[::-1][:top_k]

        hits: list[VectorSearchHit] = []

        for index in order:
            if scores[index] == -np.inf:
                continue

            hits.append(
                VectorSearchHit(
                    chunk_key=self._chunks[index].chunk_key,
                    relative_path=self._chunks[index].relative_path,
                    score=float(scores[index]),
                    chunk=self._chunks[index],
                )
            )

        return hits


def _as_vector(vector: np.ndarray) -> np.ndarray:
    return np.asarray(vector, dtype=np.float32).reshape(-1)