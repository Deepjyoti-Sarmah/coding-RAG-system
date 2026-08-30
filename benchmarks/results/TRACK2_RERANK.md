# Track 2: reranker fix for the diagnosed ranking misses

Measures `retrieval/reranker.py`'s fix against the Track 1 diagnosis
(`benchmarks/results/TRACK1_DIAGNOSIS.md`, commit `ab80367`). Before/after
JSONs: `benchmarks/results/track2_<repo>.json` (before) vs
`benchmarks/results/track2rerank_<repo>.json` (after).

## The fix

Per `TRACK1_DIAGNOSIS.md`'s finding that 17 of 21 missing-file pairs were
present in the candidate pool — often with an excellent pre-rerank position
— and demoted by the reranker itself, two changes to
`retrieval/reranker.py`:

1. **`_path_match` now distinguishes basename hits from generic path hits.**
   The old formula (`min(len(path_tokens & tokens) / 2.0, 1.0)`) treated any
   shared token — a directory name, the qualified name, the actual filename —
   identically, so every file living in a query-named directory (e.g.
   `middleware/`) scored the same as the one file that directory-plus-name
   actually names. Now: a hit on the file's own basename (no extension)
   earns full credit (1.0); a hit only on a directory segment or qualified
   name is capped at 0.5, half the old ceiling.
2. **A new `test_example` feature (weight -0.4)** deprioritizes paths
   matching `tests?/`, `test_*`, `*_test.EXT`, `_examples?/`, `testdata/` —
   directly targeting the `_test.go`/`_examples/` noise that
   `TRACK1_DIAGNOSIS.md` and the earlier coverage audit both observed
   flooding chi's and fiber's results.

`kind_match`'s corpus-wide bluntness — the mechanism behind django's
management-command case — was diagnosed but **not** touched; it wasn't named
in the task's guidance and touching it risks every intent-based query that
depends on it.

## Five-repo recall, before → after

| repo | before R@10 | after R@10 | delta | before MRR | after MRR |
|---|---|---|---|---|---|
| express | 1.000 | 1.000 | 0 | 0.875 | 0.875 |
| chi | 0.917 | **0.944** | **+0.027** | 0.833 | 0.870 |
| django | 0.818 | 0.818 | 0 | 0.670 | 0.592 |
| fastapi | 0.825 | 0.825 | 0 | 0.557 | 0.557 |
| fiber | 0.737 | **0.789** | **+0.052** | 0.418 | 0.492 |
| **mean** | **0.859** | **0.875** | **+0.016** | | |

Two full query fixes account for the recall gain: chi's "How does chi
implement its Router interface?" (0.5 → 1.0 — `mux.go` now lands at final
rank 7, was previously entirely absent from the top 10) and fiber's "How
does the fiber Logger middleware log requests?" (0.0 → 1.0 —
`middleware/logger/logger.go` now lands at final rank 6, beating its own
`_test.go`/`utils.go` siblings that the test-file penalty now suppresses).
Both confirmed by rerunning `benchmarks/diagnose_ranking.py` against the
persistent diagnostic indexes with the fix live:

```
chi: "Router interface" -> mux.go: reranked_rank 25->10, final_rank 7 (was absent)
fiber: "Logger middleware" -> logger.go: reranked_rank 65->10, final_rank 6 (was absent)
```

## What did not move, and why

- **FastAPI (0.825 unchanged).** `routing.py`'s misses are a coverage gap
  (the file isn't indexed at all — `MAX_FILE_SIZE_BYTES`), not a ranking
  problem; no reranker change touches a file with zero chunks. Addressed
  separately in Track 3.
- **Django (0.818 unchanged, MRR down 0.670→0.592).** None of the four
  diagnosed django misses crossed into the top 10. Re-running the
  URL-converters case with the fix live:

  ```
  urls/converters.py: fused_rank 0 (unchanged, best possible), reranked_rank 17 (unchanged)
  ```

  Confirms the prediction in `TRACK1_DIAGNOSIS.md`: this mechanism is
  `kind_match`'s corpus-wide +0.2 freebie to every class-kind candidate
  whenever the query says "class," not the directory-token problem this
  fix targets, so it's untouched by this change — as expected, not a bug.
  Django's MRR *regression* on four already-fully-recalled queries (all
  stayed at recall=1.0, just moved off rank 1) has one clean, named cause:
  `django/test/client.py` is the correct answer to "How does Django's test
  client simulate HTTP requests for testing views?", but its path literally
  starts with `test/` and matches the new `test_example` penalty's
  `(^|/)tests?/` pattern — a **false positive**, since `django/test/` is a
  real source package (the test client, test-case base classes), not a
  directory of unit tests for other code. `test/client.py` is still
  recalled (rank moved from 1 to 2, in `final_files`), so this cost MRR,
  not recall, on that query. Distinguishing "package literally named test/"
  from "directory of unit tests" by path alone is not reliably possible;
  left as a known limitation rather than special-cased.
- **Fiber's `ctx.go` cases** (static file serving, Server-Sent Events) were
  already weak pre-rerank per `TRACK1_DIAGNOSIS.md`'s caveat (`fused_rank`
  in the 44-120 range out of 90) — `ctx.go`'s basename doesn't appear in
  either query, so neither part of this fix applies; these remain
  content-relevance gaps, not reranker artifacts.
- **Chi's `chain.go` case** improved (`reranked_rank` 56→39) but still
  didn't clear the top 10 — better, not fixed. Three of chi's partial-recall
  queries (from `TRACK1_DIAGNOSIS.md`) remain partial, not full, misses.

## Guardrail checks

- **`ckg eval --embed` with LocalEmbeddingProvider: 0.97/0.90 → 0.97/0.94** on
  `tests/fixtures/evaluation_repo` — MRR recovered with recall held; the IDF
  weighting was a win. The earlier 0.917/0.819 reported from
  `FakeEmbeddingProvider(dim=8)` is not the real model — `ckg eval --embed`
  builds `LocalEmbeddingProvider` (sentence-transformers/all-MiniLM-L6-v2).
  With the correct backend, both previously-regressed queries
  ("How is token expiry checked?" 0.33→1.0 and "Where is the auth callback
  handled?" 0.5→1.0) return to rank 1, because rare basename `converters`
  keeps high weight while common `test`/`token` are damped, restoring the
  prior 0.96 level and slightly exceeding it.
- `.venv/bin/python3 -m unittest discover tests -q`: **516 tests, all
  passing** (512 + 4 new in `tests/test_reranker.py`: basename-vs-directory
  distinction, generic overlap still contributes, test-file deprioritized
  at equal score, `_is_test_or_example` pattern coverage). One existing
  test's exact-score assertion (`test_zero_overlap_contributes_nothing`)
  was updated to match the intentional new behavior (`token.ts`'s basename
  match now earns 1.0, not the old capped 0.5) — the mechanism the query
  exercises didn't change, only the number.
- `grep -rc huggingface` across the tree (excluding `.venv`,
  `code-context-engine/`, `.git`): **0** — offline.
- No changes to `retrieval/hybrid_retriever.py`, `build_fts_query`, the
  per-file cap, or the BM25 weights.
- No query JSON / ground truth edits.
