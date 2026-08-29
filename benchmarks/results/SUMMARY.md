# External Benchmark Results (with embeddings)

> **Superseded numbers below for chi/fiber.** The coverage audit
> (`benchmarks/results/COVERAGE.md`) found `chi_queries.json` and
> `fiber_queries.json` referenced files that don't exist at the pinned
> commits (see `benchmarks/ATTRIBUTION.md`). Those queries were corrected
> and all five repos re-run; current baseline is chi R@10 0.917 (was
> 0.861), fiber R@10 0.737 (was 0.675), mean 0.834 (was 0.811 across the
> uncorrected sets) — recorded in `benchmarks/results/{chi,fiber}.json`.
> express/fastapi/django are unchanged. See `benchmarks/results/TRACK2.md`
> for the subsequent module-symbol-synthesis change on top of this.

Harness: `evaluation/external.py` + `benchmarks/run_external.py`
Indexing: `source_dir` as repo root for file-level ground truth, `top_k=30` chunks deduped to `min(10, distinct files available)` distinct files.
Embeddings: `LocalEmbeddingProvider` (all-MiniLM-L6-v2) via `run_embedding_worker`.

Final (A+B: per-file cap 3 + weighted BM25 10/5/8/1):

| repo | source_dir | commit | queries | mean \|expected\| | ceiling P@10 | CKG P@10 | P@10 norm | P_over_ret | R@10 | MRR | p50 latency | index time | mean distinct |
|------|------------|--------|---------|---------------|--------------|----------|------------|------|-----|-------------|------------|---------------|
| express | lib | 023767f | 20 | 1.05 | 0.105 | 0.105 | 1.000 | 0.180 | 1.000 | 0.875 | 21.7 ms | 0.04 s | 5.9 |
| fastapi | fastapi | 4903347 | 20 | 1.45 | 0.145 | 0.105 | 0.700 | 0.105 | 0.700 | 0.508 | 25.9 ms | 0.6 s | 10.0 |
| chi | . | 36611d2 | 18 | 1.28 | 0.128 | 0.100 | 0.861 | 0.100 | 0.861 | 0.778 | 21.9 ms | 0.6 s | 10.0 |
| fiber | . | e7229b1 | 20 | 1.35 | 0.135 | 0.085 | 0.675 | 0.085 | 0.675 | 0.397 | 35.8 ms | 29.1 s | 10.0 |
| django | django | 3b767c5 | 22 | 1.14 | 0.114 | 0.091 | 0.818 | 0.093 | 0.818 | 0.647 | 52.6 ms | 30.0 s |

*Ceiling* = `min(|expected|, 10)/10` per question, averaged; *P@10 norm* = `P@10 / ceiling` (0 when ceiling 0); *P_over_ret* = `|hits| / |ranked_files|` (CCE-comparable, divides by returned count, not fixed 10); *mean distinct* = mean `|ranked_files|` per query.

Three-variant benchmark on cheap repos (express/fastapi/chi) — same data, different retriever:

| repo | variant | R@10 | MRR | P_over_ret | mean distinct |
|------|---------|------|-----|------------|---------------|
| express | baseline | 1.000 | 0.875 | 0.283 | 4.0 |
|  | A (cap) | 1.000 | 0.875 | 0.180 | 5.9 |
|  | B (weighted) | 1.000 | 0.875 | 0.283 | 4.0 |
|  | A+B | 1.000 | 0.875 | 0.180 | 5.9 |
| fastapi | baseline | 0.675 | 0.508 | 0.277 | 4.7 |
|  | A (cap) | 0.700 | 0.508 | 0.105 | 10.0 |
|  | B (weighted) | 0.675 | 0.508 | 0.277 | 4.6 |
|  | A+B | 0.700 | 0.508 | 0.105 | 10.0 |
| chi | baseline | 0.861 | 0.778 | 0.109 | 9.4 |
|  | A (cap) | 0.861 | 0.778 | 0.100 | 10.0 |
|  | B (weighted) | 0.861 | 0.778 | 0.110 | 9.3 |
|  | A+B | 0.861 | 0.778 | 0.100 | 10.0 |

Per-file cap (A) is the driver for the distinct-files diagnostic (fastapi 4.7→10.0, chi 9.4→10.0, express 4.0→5.9, limited by 6 files). Weighted BM25 (B) alone did not move recall on cheap repos; combined A+B retains A's gains. Expensive repos run only on variants that helped (A and A+B): django and fiber both show same as baseline except fiber R@10 0.625→0.675 with A+B.

Notes:
- Commits are pinned and recorded in each JSON; CCE clones HEAD so its numbers drift.
- Retrieved `top_k=30` chunks then deduped to `min(10, distinct files available)`; file-level metrics. For small repos like `express` lib (6 files), a query returned only 2 distinct files yet still scored 1/10 under the fixed-k formula — the ceiling makes this visible.
- No retrieval tuning was performed beyond the two targeted changes (no changes to `build_fts_query`, `retrieval/reranker.py`, or chunker). All numbers are from the same harness, same ground truth.
- Raw P@10 is not comparable across CKG and CCE. CKG's `evaluation/external.py:86` divides by fixed `k=10`; CCE's `code-context-engine/benchmarks/run_benchmark.py:170` divides by `len(result_files)` (however many distinct files its chunks span). Both use the same recall formula (`|hits|/|expected|`), so recall is comparable; precision is not. CCE's P@10 values exceed these ceilings (e.g., express 0.18 > 0.105), which is the visible proof of different denominators.
- For comparison, CCE's published **recall** scores are: express 1.00, fastapi 0.90, chi 0.67, fiber 0.07, django 0.95 (R@10). CKG recall is 1.00/0.700/0.861/0.675/0.818 (final A+B). On fiber, CCE collapses to 0.07 while CKG achieves 0.675 on the same queries and ground truth — both use identical recall denominator, so the difference likely says more about their indexer than CKG's ranking. Where precision must be compared, use `P_over_ret` (CCE-like) — e.g., express CKG 0.180 vs CCE 0.18 — but note distinct chunking still limits direct comparison.
- `ckg eval --embed` on `tests/fixtures/evaluation_repo` still reports mean recall@k 0.97 / MRR 0.96 after both changes (no regression).
- Index time is `reindex_index` only; embedding time is additional (e.g., fiber ~5 min for 165 batches, django ~11-15 min for 372 batches).
- All runs completed and emitted JSON reports in this directory. Recomputed reports verify `precision_at_10`/`recall_at_10`/`reciprocal_rank` match stored values exactly.
