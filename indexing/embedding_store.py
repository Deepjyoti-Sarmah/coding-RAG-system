import numpy as np

from chunking.symbol_chunker import SemanticChunk
from embeddings.provider import EmbeddingProvider


def embed_chunks(
    chunks: list[SemanticChunk],
    provider: EmbeddingProvider,
    cache: dict[str, np.ndarray],
) -> tuple[dict[str, np.ndarray], int]:
    embeddings_by_key: dict[str, np.ndarray] = {}
    missing: list[SemanticChunk] = []

    for chunk in chunks:
        cached = cache.get(chunk.content_hash)

        if cached is None:
            missing.append(chunk)
        else:
            embeddings_by_key[chunk.chunk_key] = cached

    if missing:
        vectors = provider.embed_batch([chunk.embedding_text for chunk in missing])

        for chunk, vector in zip(missing, vectors):
            embeddings_by_key[chunk.chunk_key] = vector

    return embeddings_by_key, len(missing)