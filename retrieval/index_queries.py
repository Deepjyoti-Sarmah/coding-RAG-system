"""Retrieval assembled over a persisted index.

These functions wire the retrieval stack onto a database path. They live
here rather than in `storage` so that persistence stays a leaf: storage
knows how to read and write rows, and this module knows how to turn
those rows into a retriever.
"""

from analysis.build_result import BuildResult
from embeddings.provider import EmbeddingProvider
from retrieval.context_builder import ContextPack, build_context_pack
from retrieval.hybrid_retriever import HybridRetriever
from retrieval.index_cache import load_index_cached
from retrieval.numpy_vector_store import NumpyVectorStore
from retrieval.sqlite_vec_store import SqliteVecVectorStore, sqlite_vec_available
from retrieval.vector_store import VectorStore
from storage.index_store import (
    load_chunk_vectors,
    search_lexical,
)


def load_vector_store(db_path: str) -> VectorStore:
    """sqlite-vec when the extension is usable, in-memory numpy otherwise."""
    if sqlite_vec_available(db_path):
        return SqliteVecVectorStore(db_path)

    return NumpyVectorStore(load_chunk_vectors(db_path))


def build_hybrid_retriever(
    db_path: str,
    provider: EmbeddingProvider | None = None,
    *,
    result: BuildResult | None = None,
) -> HybridRetriever:
    if result is None:
        result = load_index_cached(db_path)

    vector_store = load_vector_store(db_path) if provider is not None else None
    embed = provider.embed_query if provider is not None else None

    # IDF corpus: basename-token document frequency over relative_paths
    from retrieval.reranker import build_basename_token_df

    # Prefer real documents; fallback to symbol relative_paths if documents absent
    if result.documents:
        relative_paths = [d.relative_path for d in result.documents]
    else:
        relative_paths = list({s.relative_path for s in result.symbols})
    basename_token_df = build_basename_token_df(relative_paths) if relative_paths else None
    total_docs = len(relative_paths) if relative_paths else None

    return HybridRetriever(
        symbol_index=result.symbol_index,
        graph=result.graph,
        fts_search=lambda query, limit: search_lexical(
            db_path, query, limit=limit
        ),
        vector_store=vector_store,
        embed=embed,
        basename_token_df=basename_token_df,
        total_docs=total_docs,
    )


def build_context_pack_from_index(
    db_path: str,
    query: str,
    *,
    token_budget: int,
    provider: EmbeddingProvider | None = None,
    top_k: int = 5,
) -> ContextPack:
    # One materialization serves both the retriever and the context pack.
    from retrieval.context_builder import estimate_tokens

    result = load_index_cached(db_path)
    retriever = build_hybrid_retriever(db_path, provider=provider, result=result)

    retrieval = retriever.retrieve(query, top_k=top_k)

    # Honest baseline: ground-truth is unknown here, use whole-index size
    # as informative denominator (not a savings claim).
    baseline_tokens = estimate_tokens("\n".join(d.content for d in result.documents)) if result.documents else 0

    return build_context_pack(
        retrieval.candidates,
        query=query,
        graph=result.graph,
        symbols_by_key={s.stable_key: s for s in result.symbols},
        token_budget=token_budget,
        baseline_tokens=baseline_tokens,
    )
