# Track 1: where do the remaining misses get lost?

Diagnostic only — no fix applied in this commit. Produced with
`benchmarks/diagnose_ranking.py`, which instruments the real
`retrieval.hybrid_retriever.HybridRetriever._hybrid_search` path (wraps
`fts_search`, `vector_store.search`, and the module-level
`reciprocal_rank_fusion`/`rerank_candidates` calls it makes) rather than
reimplementing search, so every number below reflects production behavior.

## Scope: which misses were diagnosed

The task brief cites "13 remaining zero-recall queries." Recomputing directly
from the committed `benchmarks/results/track2_*.json` reports (state as of
commit `8fe4fd4`, before this session's changes) finds **10** queries with
`recall_at_10 == 0.0` (django 4, fastapi 2, fiber 4; chi and express have
none), plus **8** further queries with partial recall where at least one
expected file is still missing from the top 10 (chi 3, fastapi 3, fiber 2).
That's 18 affected queries, 21 individual (query, missing-file) pairs — more
than 13, and the discrepancy isn't resolved; it's reported as measured rather
than adjusted to match. This diagnosis covers all 21 pairs; the table below
is the full accounting, none left as "unknown."

## Full stage table

| repo | query | target | fts_rank | vector_rank | fused_rank | reranked_rank | stage lost |
|---|---|---|---|---|---|---|---|
| fastapi | route decorators like @app.get | routing.py | — | — | — | — | never a candidate (file not indexed — `MAX_FILE_SIZE_BYTES`, Track 3) |
| fastapi | APIRouter class | routing.py | — | — | — | — | never a candidate (same) |
| fastapi | WebSocket endpoints | routing.py | — | — | — | — | never a candidate (same) |
| fastapi | background tasks | routing.py | — | — | — | — | never a candidate (same) |
| fastapi | serve static files | staticfiles.py | — | 81/90 | 117 | 118 | demoted by reranking |
| chi | Router interface | mux.go | 10/90 | 86/90 | 25 | 28 | demoted by reranking |
| chi | middleware chained and applied | chain.go | 2/90 | 5/90 | **1** | 56 | demoted by reranking |
| chi | request context...middleware | mux.go | 10/90 | 5/90 | **3** | 78 | demoted by reranking |
| django | management command base class | core/management/base.py | 2/90 | 6/90 | **3** | 30 | demoted by reranking |
| django | session middleware | contrib/sessions/middleware.py | 8/90 | **1/90** | **6** | 15 | demoted by reranking (barely misses top 10) |
| django | session middleware | contrib/sessions/base_session.py | 50/90 | 24/90 | 21 | 51 | demoted by reranking |
| django | password hashing | contrib/auth/hashers.py | 40/90 | **1/90** | 31 | 59 | demoted by reranking |
| django | URL path converters | urls/converters.py | **0/90** | **0/90** | **0** | 17 | demoted by reranking — best possible pre-rerank position (rank 0 of 90 on every signal), still falls out of top 10 |
| fiber | path parameters and query strings | ctx.go | — | 41/90 | 81 | 41 | demoted by reranking |
| fiber | path parameters and query strings | router.go | 12/90 | 84/90 | **6** | 90 | demoted by reranking (dead last) |
| fiber | Logger middleware log requests | middleware/logger/logger.go | 66/90 | 11/90 | 18 | 65 | demoted by reranking (own test/util siblings win instead) |
| fiber | static file serving | app.go | 54/90 | 82/90 | 82 | 91 | demoted by reranking |
| fiber | static file serving | ctx.go | 82/90 | 74/90 | 120 | 124 | demoted by reranking (mediocre pre-rerank too — see caveat) |
| fiber | fasthttp under the hood | ctx.go | 13/90 | — | 29 | 22 | demoted by reranking (recall=0.5, other expected file hits) |
| fiber | Server-Sent Events | ctx.go | 76/90 | 21/90 | 44 | 76 | demoted by reranking |
| fiber | middleware chaining with Use() | router.go | 64/90 | — | 129 | 97 | demoted by reranking (recall=0.5; also weak pre-rerank) |

Every diagnosed row is **(b) demoted by ranking**, not (a) never a candidate
— except FastAPI's `routing.py`, which is a coverage gap (the file is
skipped by `MAX_FILE_SIZE_BYTES` and has zero chunks at all), out of Track 1's
scope and addressed separately in Track 3. **Group sizes: (a) never-a-candidate
= 4/21 pairs, all `routing.py`; (b) demoted-by-ranking = 17/21 pairs**, spread
across chi, django, and fiber.

## The specific unknown: django's management-command case

The task's own hand-computation: `core/management/base.py` tokenizes to
`{core, management, base, py}`, overlapping the query
(`"How does Django's management command base class parse arguments and
execute?"`) on `{management, base}` — 2 hits, so `_path_match` (as it was)
saturates at 1.0. The competitor `core/management/commands/testserver.py`
overlaps on `{management}` only — 0.5. By that math alone, `base.py` should
already win. **It didn't, and the diagnostic explains why**: `base.py` *is*
a strong pre-rerank candidate — `fts_rank=2`, `vector_rank=6`, `fused_rank=3`
out of a 90-wide pool, resoundingly beating `testserver.py` at the fusion
stage. The reranker actively demotes it to `reranked_rank=30`. Dumping
`RerankFeatures` per candidate (see session transcript) shows the actual
mechanism: `testserver.py`'s `Command` class scored `vector=1.0` (rank 0 in
the vector search — its content genuinely embeds close to the query,
semantically) and `kind_match=1.0`, `exact_symbol=1.0` (the token "command"
matches the symbol name `Command`, case-insensitively). `base.py`'s single
best chunk is its `execute` *method* — `kind_match=0.0` (a method, not a
`class`, and the query happens to contain the literal word "class") even
though it has `exact_symbol=1.0` too (the query also contains "execute").
The two path_match values were already equal (1.0 for both, both matched
"management"), so path_match alone explains nothing here — this is a second,
independent mechanism: **`kind_match` is a blunt, corpus-wide boost**. Any
class-kind candidate anywhere in the repo gets the same +0.2·1.0 whenever the
query contains the literal word "class," regardless of whether that specific
class is the one named. Combined with a `Command` class that's genuinely a
strong vector match for a query about "commands," this is enough to
overcome `base.py`'s better pre-rerank position.

This is a **different mechanism** from the chi/fiber pattern below, and the
fix applied in this session's Track 2 (a basename-vs-directory-aware
`_path_match`) targets it only indirectly: `base.py`'s own basename ("base")
is itself a query token ("management command **base** class..."), which
under the new `_path_match` earns it the full 1.0 on a *specific* signal
rather than tying with `testserver.py` on a generic one. `kind_match` itself
was not touched — its blunt corpus-wide behavior is a known follow-on
candidate for a future round, flagged but out of this session's scope (the
task's guidance named `_path_match` and test/example deprioritization
specifically).

## The chi/fiber mechanism: generic directory-token saturation

Distinct from django's case, chi and fiber show a cleaner, single-cause
pattern: `_path_match` (as it was) computed
`hits = len(path_tokens & tokens); return min(hits / 2.0, 1.0)` over the
*whole* relative path — so a query containing a directory name (e.g.
"middleware") gives **every file in that directory** the same 0.5–1.0
credit, while the actual target file often shares *no* token with the query
at all. Concrete case: query "How is request context used to pass values
between middleware and handlers?" wants `mux.go`. `mux.go`'s path tokens are
`{mux, go}` — zero overlap with the query, `path_match=0`. Every file under
`middleware/` (dozens of them, including test files like
`middleware/request_id_test.go`) gets `path_match=0.5` just for living in a
directory the query happens to name. `mux.go` starts strong pre-rerank
(`fused_rank=3`) purely on FTS/vector content signal, then loses that lead
once path-based noise floods in, ending at `reranked_rank=78`. The same
pattern repeats for `chain.go` (`fused_rank=1` → `reranked_rank=56`) and
fiber's `router.go` (`fused_rank=6` → `reranked_rank=90`, dead last) and
`middleware/logger/logger.go` (`fused_rank=18` → `reranked_rank=65`, beaten
by its own `_test.go`/`utils.go` siblings in the same directory). This one
generalizes cleanly across both languages and both repos, and is exactly
what `benchmarks/results/COVERAGE.md` had already flagged as "test/example
files polluting fiber and chi results" without yet identifying the
reranker-side mechanism that lets them win.

## The starkest case: urls/converters.py

For "How does Django convert URL path converters like `<int:id>` into Python
types?", `urls/converters.py` is `fts_rank=0`, `vector_rank=0`, and
`fused_rank=0` — the single best-fused candidate out of all 90 pooled
chunks, on every raw signal simultaneously. The reranker still drops it to
`reranked_rank=17`, outside the top 10. This is the cleanest possible
demonstration that "demoted by ranking" is not a subtle effect at the
margins — a candidate that dominates the entire pre-rerank pool can still
lose. `final_files` for that query is `template/defaulttags.py`,
`templatetags/static.py`, `forms/widgets.py`, and seven more files with no
obvious connection to URL path converters, which is consistent with the
generic-directory/kind_match mechanisms above (many of the winners are
class-kind candidates in files that share a generic token like "static" or
"template" with unrelated parts of the query).

## Caveat: not every miss is purely a reranking artifact

Fiber's `ctx.go` for "static file serving" (`fused_rank=120`) and "Server-Sent
Events" (`fused_rank=44`) are mediocre even *before* reranking —
`fts_rank`/`vector_rank` in the 70s-80s out of a 90-wide pool. `ctx.go` is a
large, many-symbol file; whichever specific chunk should answer "static file
serving" apparently doesn't score well on lexical or vector similarity to
begin with, and neither the directory-token bug nor a basename fix touches
that (`ctx.go`'s basename "ctx" doesn't appear in either query). This is a
plausible, separate content-relevance gap, not something Track 2's rerank
fix is expected to close.

## Track 2 fix, informed by this diagnosis

17 of 21 pairs are (b), and two independent mechanisms were found:
generic-directory-token saturation (chi, fiber — clean, single-cause) and a
corpus-wide `kind_match` freebie compounding with genuine vector similarity
(django — more subtle). Per the task's guidance ("reranker features —
basename-vs-query-term matching beyond the current saturating `_path_match`,
and deprioritizing test and example files"), this session's fix (committed
separately) changes `retrieval/reranker.py`:

1. `_path_match` now distinguishes a hit on the file's own basename (strong,
   specific signal, full 1.0 credit) from a hit only on a directory segment
   or qualified name (weak, generic signal, capped at 0.5 instead of the
   previous 1.0).
2. A new `test_example` feature (weight -0.4) deprioritizes candidates whose
   path matches `tests?/`, `test_*`, `*_test.EXT`, `_examples?/`, or
   `testdata/` — directly targeting the `_test.go`/`_examples/` noise
   observed flooding chi's and fiber's results.

`kind_match`'s corpus-wide bluntness (the django mechanism) was **not**
touched — it wasn't named in the task's guidance, and changing it risks
touching every intent-based query that relies on it (`test_kind_match_boost`
in `tests/test_reranker.py`). Flagged here as a candidate for a future round.

Measured before/after results are in `benchmarks/results/TRACK2_RERANK.md`.
