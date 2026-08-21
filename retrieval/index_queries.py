"""Retrieval assembled over a persisted index.

These functions wire the retrieval stack onto a database path. They live
here rather than in `storage` so that persistence stays a leaf: storage
knows how to read and write rows, and this module knows how to turn
those rows into a retriever.
"""

from chunking.symbol_chunker import SemanticChunk
from embeddings.provider import EmbeddingProvider
from retrieval.context_builder import ContextPack, build_context_pack
from retrieval.hybrid_retriever import HybridRetriever
from retrieval.numpy_vector_store import NumpyVectorStore
from storage.index_store import (
    load_chunk_vectors,
    load_index,
    search_lexical,
)


def load_vector_store(db_path: str) -> NumpyVectorStore:
    entries: list[tuple[SemanticChunk, object]] = load_chunk_vectors(db_path)

    return NumpyVectorStore(entries)


def build_hybrid_retriever(
    db_path: str,
    provider: EmbeddingProvider | None = None,
) -> HybridRetriever:
    result = load_index(db_path)

    vector_store = load_vector_store(db_path) if provider is not None else None
    embed = provider.embed_query if provider is not None else None

    return HybridRetriever(
        symbol_index=result.symbol_index,
        graph=result.graph,
        fts_search=lambda query, limit: search_lexical(
            db_path, query, limit=limit
        ),
        vector_store=vector_store,
        embed=embed,
        resolved_imports=result.resolved_import_references,
        exports=result.exports,
    )


def build_context_pack_from_index(
    db_path: str,
    query: str,
    *,
    token_budget: int,
    provider: EmbeddingProvider | None = None,
    top_k: int = 5,
) -> ContextPack:
    result = load_index(db_path)
    retriever = build_hybrid_retriever(db_path, provider=provider)

    retrieval = retriever.retrieve(query, top_k=top_k)

    return build_context_pack(
        retrieval.candidates,
        query=query,
        graph=result.graph,
        symbols_by_key={s.stable_key: s for s in result.symbols},
        token_budget=token_budget,
    )
