# Attribution

The query sets in this directory are copied from the vendored project
`code-context-engine` (https://github.com/elara-labs/code-context-engine),
which is published under the MIT License:

- `express_queries.json` — 20 queries expecting files under `lib/` in https://github.com/expressjs/express
- `fastapi_queries.json` — 20 queries expecting files under `fastapi/` in https://github.com/fastapi/fastapi
- `chi_queries.json` — 18 queries expecting files under `.` in https://github.com/go-chi/chi
- `fiber_queries.json` — 19 queries expecting files under `.` in https://github.com/gofiber/fiber
- `django_queries.json` — 22 queries expecting files under `django/` in https://github.com/django/django

Total: 99 queries.

The JSON format and expected file lists were originally taken verbatim
from `code-context-engine/benchmarks/*_queries.json`; they are
reproduced here for the external benchmark harness
(`benchmarks/run_external.py` and `evaluation/external.py`) which
evaluates file-level retrieval (precision@10 / recall@10 / MRR) rather
than symbol-level.

**`chi_queries.json` and `fiber_queries.json` are no longer verbatim
CCE.** The index coverage audit (`benchmarks/results/COVERAGE.md`,
commit b38a7f7) found that some `expected_files` entries name files
that don't exist at the pinned commits recorded in
`benchmarks/results/*.json` — the ground truth itself was stale, not
a retrieval failure:

- chi: `router.go` was replaced with `chi.go` (which defines the
  `Router` interface the query asks about) in one query, and dropped
  outright in another where `mux.go` already covered the answer.
  chi has never had a `router.go`; its router logic lives in
  `mux.go` and the `Router` interface is defined in `chi.go`.
- fiber: `utils.go` was dropped from one query (`app.go` alone already
  answers it; there is no root-level `utils.go`, only per-middleware
  variants like `middleware/logger/utils.go`). The "How does fiber
  implement WebSocket support?" query was removed entirely — at the
  pinned commit, fiber v3 has no in-repo WebSocket middleware at all
  (it moved to a separate `gofiber/websocket` module), so no correct
  file exists to answer it.

Anyone comparing recall/precision numbers against upstream CCE
results, or against this repo's own pre-b38a7f7 results, should know
the query sets diverge for this reason.

Original project: elara-labs/code-context-engine, MIT License.
See `code-context-engine/LICENSE` (vendored) for the full text.
