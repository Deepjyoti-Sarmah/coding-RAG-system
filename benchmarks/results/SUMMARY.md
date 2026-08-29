# External Benchmark Results (with embeddings)

Harness: `evaluation/external.py` + `benchmarks/run_external.py`
Indexing: `source_dir` as repo root for file-level ground truth, top_k=30 deduped to 10 distinct files.
Embeddings: `LocalEmbeddingProvider` (all-MiniLM-L6-v2) via `run_embedding_worker`.

| repo | source_dir | commit | queries | P@10 | R@10 | MRR | p50 latency | index time |
|------|------------|--------|---------|------|------|-----|-------------|------------|
| express | lib | 023767f | 20 | 0.105 | 1.000 | 0.875 | 36.0 ms | 0.04 s |
| fastapi | fastapi | 4903347 | 20 | 0.100 | 0.675 | 0.508 | 23.7 ms | 0.5 s |
| chi | . | 36611d2 | 18 | 0.100 | 0.861 | 0.778 | 32.1 ms | 0.6 s |
| fiber | . | e7229b1 | 20 | 0.080 | 0.625 | 0.374 | 32.1 ms | 35.4 s |
| django | django | 3b767c5 | 22 | 0.091 | 0.818 | 0.647 | 49.1 ms | 25.8 s |

Notes:
- Commits are pinned and recorded in each JSON; CCE clones HEAD so its numbers drift.
- Retrieved `top_k=30` chunks then deduped to 10 files; metrics are file-level.
- No retrieval tuning was performed (no changes to `build_fts_query`, `retrieval/reranker.py`, or chunker).
- For comparison, CCE's published file-level scores (different system) are:
  express 0.18/1.00, fastapi 0.24/0.90, chi 0.10/0.67, fiber 0.03/0.07, django 0.16/0.95 (P@10/R@10).
  CKG's fiber recall 0.625 is well above CCE's 0.07 — not a harness bug, fiber is Go monorepo with many files and CKG's simple file-level recall is higher.
- Index time is `reindex_index` only; embedding time is additional (e.g., fiber ~5 min for 165 batches, django ~15 min for 372 batches).
- All runs completed and emitted JSON reports in this directory.
