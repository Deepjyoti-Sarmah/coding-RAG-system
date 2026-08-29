# External Benchmark Results (with embeddings)

Harness: `evaluation/external.py` + `benchmarks/run_external.py`
Indexing: `source_dir` as repo root for file-level ground truth, `top_k=30` chunks deduped to `min(10, distinct files available)` distinct files.
Embeddings: `LocalEmbeddingProvider` (all-MiniLM-L6-v2) via `run_embedding_worker`.

| repo | source_dir | commit | queries | mean \|expected\| | ceiling P@10 | CKG P@10 | P@10 norm | P_over_ret | R@10 | MRR | p50 latency | index time |
|------|------------|--------|---------|---------------|--------------|----------|------------|------|-----|-------------|------------|
| express | lib | 023767f | 20 | 1.05 | 0.105 | 0.105 | 1.000 | 0.283 | 1.000 | 0.875 | 36.0 ms | 0.04 s |
| fastapi | fastapi | 4903347 | 20 | 1.45 | 0.145 | 0.100 | 0.675 | 0.277 | 0.675 | 0.508 | 23.7 ms | 0.5 s |
| chi | . | 36611d2 | 18 | 1.28 | 0.128 | 0.100 | 0.861 | 0.109 | 0.861 | 0.778 | 32.1 ms | 0.6 s |
| fiber | . | e7229b1 | 20 | 1.35 | 0.135 | 0.080 | 0.625 | 0.101 | 0.625 | 0.374 | 32.1 ms | 35.4 s |
| django | django | 3b767c5 | 22 | 1.14 | 0.114 | 0.091 | 0.818 | 0.111 | 0.818 | 0.647 | 49.1 ms | 25.8 s |

*Ceiling* = `min(|expected|, 10)/10` per question, averaged; *P@10 norm* = `P@10 / ceiling` (0 when ceiling 0); *P_over_ret* = `|hits| / |ranked_files|` (CCE-comparable, divides by returned count, not fixed 10).

Notes:
- Commits are pinned and recorded in each JSON; CCE clones HEAD so its numbers drift.
- Retrieved `top_k=30` chunks then deduped to `min(10, distinct files available)`; file-level metrics. For small repos like `express` lib (6 files), a query returned only 2 distinct files yet still scored 1/10 under the fixed-k formula — the ceiling makes this visible.
- No retrieval tuning was performed (no changes to `build_fts_query`, `retrieval/reranker.py`, or chunker).
- Raw P@10 is not comparable across CKG and CCE. CKG's `evaluation/external.py:86` divides by fixed `k=10`; CCE's `code-context-engine/benchmarks/run_benchmark.py:170` divides by `len(result_files)` (however many distinct files its chunks span). Both use the same recall formula (`|hits|/|expected|`), so recall is comparable; precision is not. CCE's P@10 values exceed these ceilings (e.g., express 0.18 > 0.105), which is the visible proof of different denominators.
- For comparison, CCE's published **recall** scores are: express 1.00, fastapi 0.90, chi 0.67, fiber 0.07, django 0.95 (R@10). CKG recall is 1.00/0.675/0.861/0.625/0.818. On fiber, CCE collapses to 0.07 while CKG achieves 0.625 on the same queries and ground truth — both use identical recall denominator, so the difference likely says more about their indexer than CKG's ranking. Where precision must be compared, use `P_over_ret` (CCE-like) — e.g., express CKG 0.283 vs CCE 0.18 — but note distinct chunking still limits direct comparison.
- Index time is `reindex_index` only; embedding time is additional (e.g., fiber ~5 min for 165 batches, django ~15 min for 372 batches).
- All runs completed and emitted JSON reports in this directory. Recomputed reports verify `precision_at_10`/`recall_at_10`/`reciprocal_rank` match stored values exactly.
