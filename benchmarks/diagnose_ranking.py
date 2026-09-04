"""Where does a target file's chunks get lost during retrieval?

For a repo (an already-indexed sqlite db) + a query + a target relative
path, reports the earliest rank at which any chunk belonging to that file
appears at each stage of retrieval.hybrid_retriever.HybridRetriever's
hybrid-search path:

  fts        - retrieval.index_queries' FTS5 search, top_k*3 hits
  vector     - vector_store.search, top_k*3 hits (only if embeddings ran)
  fused      - retrieval.ranking.reciprocal_rank_fusion output, sorted
  reranked   - retrieval.reranker.rerank_candidates output (post-boost)
  final      - the file-deduped top-10 the eval harness scores recall on
               (evaluation.external._dedupe_files, reused directly)

A file absent from `fts` and `vector` never entered the candidate pool at
all - the reranker never saw it, regardless of its features. A file
present in `fused`/`reranked` but missing from `final` was demoted by
ranking or lost to the per-file cap / file-dedup truncation. This script
does not reimplement search: it instruments the real HybridRetriever by
wrapping its fts_search callable, its vector_store.search method, and the
module-level reciprocal_rank_fusion/rerank_candidates it calls, recording
what passes through each without altering behavior.

Usage:
  python benchmarks/diagnose_ranking.py --db /path/to/index.sqlite \
      --query "How does fiber implement Server-Sent Events?" \
      --target ctx.go [--embed]

  # Or build a fresh index first:
  python benchmarks/diagnose_ranking.py --repo /tmp/sg_audit/fiber \
      --query "..." --target ctx.go --embed
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
# Unconditional: a stale editable-install copy of config.py can sit ahead
# of ROOT in sys.path even when ROOT is technically already present
# further back - see benchmarks/run_external.py for the full story.
sys.path.insert(0, str(ROOT))

import retrieval.hybrid_retriever as hr_module
from embeddings.provider import EmbeddingProvider
from evaluation.external import _dedupe_files
from indexing.indexer import reindex_index
from retrieval.index_queries import build_hybrid_retriever


def build_index(repo_dir: str, db_path: str, *, embed: bool) -> EmbeddingProvider | None:
    reindex_index(db_path, repo_dir)

    if not embed:
        return None

    from embeddings.local_provider import LocalEmbeddingProvider
    from indexing.embedding_queue import run_embedding_worker

    provider = LocalEmbeddingProvider()
    run_embedding_worker(db_path, provider)
    return provider


def _first_rank(items, key_fn, target: str) -> int | None:
    for rank, item in enumerate(items):
        if key_fn(item) == target:
            return rank
    return None


def diagnose(db_path: str, provider: EmbeddingProvider | None, query: str, target: str, *, top_k: int = 30) -> dict[str, object]:
    retriever = build_hybrid_retriever(db_path, provider=provider)

    raw_fts: list[Any] = []  # type: ignore[type-arg]
    raw_vector: list[Any] = []  # type: ignore[type-arg]
    fused_holder: dict[Any, Any] = {}  # type: ignore[type-arg]
    reranked_holder: list[Any] = []  # type: ignore[type-arg]

    orig_fts_search = retriever.fts_search

    def spy_fts(q, limit):
        hits = orig_fts_search(q, limit)
        raw_fts.extend(hits)
        return hits

    retriever.fts_search = spy_fts

    if retriever.vector_store is not None:
        orig_vec_search = retriever.vector_store.search

        def spy_vec(vec, top_k=5, **_kw):  # type: ignore[no-untyped-def]  # pyright: ignore[reportUnknownParameterType,reportMissingParameterType]
            hits = orig_vec_search(vec, top_k=top_k)
            raw_vector.extend(hits)
            return hits

        retriever.vector_store.search = spy_vec  # type: ignore[method-assign,assignment]  # pyright: ignore[reportAttributeAccessIssue]

    orig_fusion = hr_module.reciprocal_rank_fusion
    orig_rerank = hr_module.rerank_candidates

    def spy_fusion(ranked_lists, **kwargs):
        fused = orig_fusion(ranked_lists, **kwargs)
        fused_holder.update(fused)
        return fused

    def spy_rerank(candidates, q, **kwargs):
        result = orig_rerank(candidates, q, **kwargs)
        reranked_holder.extend(result)
        return result

    hr_module.reciprocal_rank_fusion = spy_fusion
    hr_module.rerank_candidates = spy_rerank

    try:
        retrieval = retriever.retrieve(query, top_k=top_k)
    finally:
        hr_module.reciprocal_rank_fusion = orig_fusion
        hr_module.rerank_candidates = orig_rerank

    key_to_path: dict[str, str] = {
        symbol.stable_key: symbol.relative_path
        for symbol in retriever.symbol_index.symbols()
    }
    for hit in raw_fts:  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType]
        key_to_path.setdefault(hit.chunk_key, hit.relative_path)  # type: ignore[attr-defined]
    for hit in raw_vector:  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType]
        key_to_path.setdefault(hit.chunk_key, getattr(hit, "relative_path", ""))  # type: ignore[attr-defined]

    fused_ordered = sorted(fused_holder.items(), key=lambda item: item[1], reverse=True)  # type: ignore[arg-type]  # pyright: ignore[reportCallIssue,reportArgumentType]

    fts_rank = _first_rank(raw_fts, lambda h: h.relative_path, target)
    vector_rank = _first_rank(raw_vector, lambda h: getattr(h, "relative_path", ""), target)
    fused_rank = _first_rank(fused_ordered, lambda item: key_to_path.get(item[0], ""), target)
    reranked_rank = _first_rank(reranked_holder, lambda c: c.relative_path, target)

    final_files = _dedupe_files(retrieval.candidates, limit=10)
    final_rank = final_files.index(target) if target in final_files else None

    if fts_rank is None and vector_rank is None:
        stage_lost = "never a candidate (absent from both fts and vector hits)"
    elif reranked_rank is not None and reranked_rank >= 10 and final_rank is None:
        stage_lost = "demoted by reranking (below rank 10 after rerank)"
    elif final_rank is None:
        stage_lost = "lost to per-file cap / file dedup after an otherwise-fine rerank rank"
    else:
        stage_lost = "present in final top 10"

    return {
        "query": query,
        "target": target,
        "fts_rank": fts_rank,
        "fts_pool_size": len(raw_fts),
        "vector_rank": vector_rank,
        "vector_pool_size": len(raw_vector),
        "fused_rank": fused_rank,
        "reranked_rank": reranked_rank,
        "final_rank": final_rank,
        "final_files": final_files,
        "stage_lost": stage_lost,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default=None, help="Path to an existing index.sqlite")
    parser.add_argument("--repo", default=None, help="Repo dir to index fresh (mutually exclusive with --db unless db doesn't exist yet)")
    parser.add_argument("--query", required=True)
    parser.add_argument("--target", required=True, help="Expected relative_path that should be retrieved")
    parser.add_argument("--embed", action="store_true", help="Run the embedding worker (needed for vector-stage visibility)")
    parser.add_argument("--top-k", type=int, default=30)
    args = parser.parse_args()

    if args.db and Path(args.db).exists():
        db_path = args.db
        provider = None
        if args.embed:
            from embeddings.local_provider import LocalEmbeddingProvider

            provider = LocalEmbeddingProvider()
        result = diagnose(db_path, provider, args.query, args.target, top_k=args.top_k)
    else:
        if not args.repo:
            parser.error("--repo is required when --db doesn't already point at a built index")

        with tempfile.TemporaryDirectory() as tmp:
            db_path = args.db or str(Path(tmp) / "index.sqlite")
            provider = build_index(args.repo, db_path, embed=args.embed)
            result = diagnose(db_path, provider, args.query, args.target, top_k=args.top_k)

    for key, value in result.items():
        print(f"{key}: {value}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
