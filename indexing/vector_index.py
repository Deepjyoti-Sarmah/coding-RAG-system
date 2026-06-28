from chunking.symbol_chunker import SemanticChunk
from embeddings.encoder import EmbeddingEncoder

import numpy as np


class VectorInex:
    def __init__(self, encoder: EmbeddingEncoder) -> None:
        self.encoder = encoder
        self.chunks: list[SemanticChunk] = []
        self.matrix: np.ndarray | None = None

    def build(self, chunks: list[SemanticChunk]):
        self.chunks = chunks
        self.matrix = np.array(
            self.encoder.encode_texts([c.embedding_text for c in chunks])
        )

    def search(self, query: str, top_k: int = 5) -> list[tuple[SemanticChunk, float]]:
        if self.matrix is None or not self.chunks:
            return []

        q = np.array(self.encoder.encode_query(query=query))
        scores = (self.matrix @ q) / (
            np.linalg.norm(self.matrix, axis=1) * np.linalg.norm(q) + 1e-8
        )

        return sorted(zip(self.chunks, scores), key=lambda x: x[1], reverse=True)[
            :top_k
        ]
