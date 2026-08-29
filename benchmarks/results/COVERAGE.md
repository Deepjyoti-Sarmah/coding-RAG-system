# Index coverage audit

Diagnostic only — no code changes. Produced with `benchmarks/audit_coverage.py`
against the same pinned commits already recorded in `benchmarks/results/*.json`,
run through the real pipeline (`ingestion.loader`, `analysis.build_graph`,
`chunking.symbol_chunker`) with no embeddings.

| repo | files walked | skipped (dir/ext/size/ignore) | documents | zero-symbol docs | zero-chunk docs |
|---|---|---|---|---|---|
| express | 6 | 0/0/0/0 | 6 | 0 | 0 |
| chi | 135 | 30/21/0/0 | 84 | 0 | 0 |
| django | 3686 | 71/2688/0/0 | 927 | 283 | 283 |
| fastapi | 56 | 0/8/1/0 | 47 | 20 | 20 |
| fiber | 493 | 30/155/1/0 | 307 | 8 | 8 |

Zero-symbol and zero-chunk counts are identical in every repo. That's not a
coincidence: `chunking/symbol_chunker.py:build_semantic_chunks` builds exactly
one chunk per symbol with no filtering (`chunking/symbol_chunker.py:40-48`), so
"zero chunks" is not currently an independent failure mode — it is a direct,
unconditional consequence of "zero symbols."

## The 11 files, stage by stage

| repo | file | stage |
|---|---|---|
| fastapi | middleware/cors.py | **no_symbols** — parsed fine, zero symbols extracted |
| fastapi | staticfiles.py | **no_symbols** |
| fastapi | templating.py | **no_symbols** |
| fastapi | websockets.py | **no_symbols** |
| fastapi | routing.py | **skipped: size** (256,338 bytes > `MAX_FILE_SIZE_BYTES` = 200,000) |
| fiber | middleware/logger/logger.go | **indexed fine** (symbols=4, chunks=4) |
| fiber | middleware/websocket/websocket.go | **never walked** — no such file/directory exists in this repo at the pinned commit (`e7229b1b…`); there is no `middleware/websocket` package at all |
| fiber | utils.go | **never walked** — no top-level `utils.go` exists at the pinned commit; only nested ones (`middleware/logger/utils.go`, `middleware/cors/utils.go`, etc.) |
| django | contrib/sessions/middleware.py | **indexed fine** (symbols=4, chunks=4) |
| django | core/management/base.py | **indexed fine** (symbols=45, chunks=45) |
| chi | router.go | **never walked** — no such file exists in this repo at the pinned commit (`36611d24…`); chi's router lives in `mux.go` |

All 11 are accounted for with a specific stage — none "unknown."

**5 of 11 are a real indexing-coverage bug** (fastapi's 4 no_symbols files, plus
routing.py's size skip). **4 of 11 are ground-truth errors**: the expected file
does not exist in the pinned commit at all (chi `router.go`, fiber
`middleware/websocket/websocket.go`, fiber `utils.go` at the root). **2 of 11
are not coverage problems at all** — `middleware/logger/logger.go` and
`core/management/base.py`/`contrib/sessions/middleware.py` are indexed with
real symbols and chunks; their zero recall is a ranking problem, out of scope
for this audit.

## Root causes, sized repo-wide

### Cause 1 — definition-free files yield zero symbols (the dominant cause)

The symbol pass only extracts function/class-level definitions
(`analysis/passes/symbol_pass.py`). A file containing only module-level
statements — bare re-export imports, constant assignments, type aliases,
`Signal()`/`var` declarations, URL pattern lists — produces a `Document` but
no `Symbol`, and therefore (via the 1:1 chunk-per-symbol chunker) zero
chunks. The file is real, was read successfully, and is fully indexable
content — it is simply invisible to retrieval because nothing downstream of
parsing ever emits a unit for it.

Confirmed shapes seen in the zero-symbol files across all three affected repos:

- **Pure re-export**: `fastapi/middleware/cors.py`, `gzip.py`,
  `httpsredirect.py`, `trustedhost.py`, `wsgi.py`, `staticfiles.py`,
  `templating.py`, `websockets.py`, `testclient.py`, `requests.py` — each is
  one or two `from X import Y as Y` lines re-exporting a Starlette symbol.
- **Module-level constants only**: `fastapi/openapi/constants.py`,
  `fastapi/types.py` (type aliases), `fastapi/logger.py` (single `logger =
  logging.getLogger(...)`), `django/db/models/sql/constants.py`,
  `django/contrib/messages/constants.py`, `django/utils/dates.py`,
  `django/conf/locale/*/formats.py` (85 files — every one of Django's
  per-locale format modules is nothing but top-level assignments), Go
  `const (...)` blocks (`fiber/constants.go`, `client/errors.go`) and
  package-level `var` declarations (`fiber/error.go`,
  `fiber/errors_internal.go`).
- **`__init__.py` files with no defs**: 180 of Django's 283, and 5 of
  FastAPI's 20 (`__init__.py`, `_compat/__init__.py`, `dependencies/__init__.py`,
  `middleware/__init__.py`, `openapi/__init__.py`, `security/__init__.py`) —
  empty or pure re-export `__init__.py` modules.
- **URL/signal/decorator modules**: `django/contrib/admindocs/urls.py`,
  `contrib/auth/urls.py`, `contrib/flatpages/urls.py` (module-level
  `urlpatterns = [...]` list, no functions), `contrib/auth/signals.py`,
  `core/signals.py`, `db/backends/signals.py` (bare `Signal()` assignments),
  `views/decorators/gzip.py`.
- One non-Python outlier: `django/contrib/admin/static/admin/js/jquery.init.js`
  is walked as a JS file (`INCLUDE_EXTENSIONS` includes `.js`) but has no
  top-level function/class either.

**Size, repo-wide**: 283/927 documents in django (30.5%), 20/47 in fastapi
(42.6%), 8/307 in fiber (2.6%), 0/84 in chi, 0/6 in express. Django is the
worst-hit in absolute terms (283 unreachable files); fastapi is worst-hit in
proportion (nearly every third file in the audited `fastapi/` source dir).
This single root cause — not size, not exclude dirs, not ignore rules —
explains effectively all zero-symbol documents observed across all five repos.

*Recommendation (not applied): give definition-free documents a fallback
chunk — e.g. one whole-file chunk keyed on the document rather than a symbol
— so a file with no function/class defs still becomes retrievable. This
would need a real design decision (chunk key scheme, embedding text shape)
and is out of scope for a diagnostic pass.*

### Cause 2 — MAX_FILE_SIZE_BYTES silently drops large single files

`ingestion/loader.py:19` `should_skip_file` drops any file over 200,000 bytes
before it becomes a `Document` at all — no symbols, no chunks, and (unlike
Cause 1) no trace that the file was ever seen. `fastapi/routing.py` is
256,338 bytes, just 28% over the cap. `fiber/ctx_test.go` (330,691 bytes) is
also caught by this, though it's a test file and not part of any ground
truth.

**Size, repo-wide**: 1 file in fastapi, 1 in fiber, 0 in chi/django/express.
Rare, but each hit is a substantial, clearly-relevant real file (routing.py is
core to FastAPI) rather than a locale/config module, so its retrieval impact
per incident is disproportionate to its frequency.

*Recommendation (not applied): raise `MAX_FILE_SIZE_BYTES` or special-case it
for source files (vs. generated/data files) — needs its own analysis of what
the cap was protecting against.*

### Cause 3 — ground-truth references files that don't exist at the pinned commit

Not an indexing problem: `chi/router.go`, `fiber/utils.go` (root), and
`fiber/middleware/websocket/websocket.go` never existed in the tree at the
pinned commits used for benchmarking. `chi`'s router logic lives in
`mux.go`; fiber's utility functions live in several nested `utils.go` files
per middleware package, not one root file; fiber's WebSocket support is not
present at this commit at all (no `middleware/websocket` directory exists).
No amount of indexing or ranking work can surface a file that isn't there.

**Size, repo-wide**: 3 of the 11 expected files across 2 repos (chi, fiber).
Not generalizable beyond the specific query set — this is a ground-truth
data quality issue, not a pipeline bug.

*Recommendation (not applied): correct or remove these three `expected_files`
entries in `benchmarks/chi_queries.json` / `benchmarks/fiber_queries.json` —
explicitly out of scope per this task's guardrails (no query JSON edits).*

### Not a coverage cause — ranking misses on correctly-indexed files

`fiber/middleware/logger/logger.go` (4 symbols/chunks),
`django/contrib/sessions/middleware.py` (4 symbols/chunks), and
`django/core/management/base.py` (45 symbols/chunks) are all indexed
correctly — real `Document`, real `Symbol`s, real `Chunk`s. Their zero
recall is a retrieval/ranking problem, not an indexing gap, and is out of
scope for this audit.

## Verification

- Reproduced the confirmed probe: `fastapi/middleware/cors.py` is a
  one-line re-export, becomes a `Document`, yields 0 symbols and 0 chunks.
- All 11 named files resolved to a specific stage (no "unknown").
- `.venv/bin/python3 -m unittest discover tests` — 508 tests, all passing.
- `grep -rc huggingface` across the tree (excluding `.venv`) — 0 hits outside
  vendored dependencies; the suite runs fully offline.
- No changes made to chunking, retrieval, ranking, loader skip rules, config
  constants, query JSONs, ground truth, or `code-context-engine/`.
