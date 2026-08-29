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
CCE.** Upstream CCE ships express 20 / fastapi 20 / chi 18 / fiber 20 /
django 22 = 100 queries total. This repo now has express 20 / fastapi
20 / chi 18 / **fiber 19** / django 22 = **99**: chi's query *count*
is unchanged (only two `expected_files` lists were edited), fiber lost
one whole query. Per-repo denominators (`|expected_files|` per query,
hence recall's denominator) therefore differ from upstream for chi and
fiber specifically, and nowhere else.

The index coverage audit (`benchmarks/results/COVERAGE.md`, commit
b38a7f7) found that some `expected_files` entries name files that
don't exist at the pinned commits recorded in `benchmarks/results/*.json`
— the ground truth itself was stale, not a retrieval failure. Each
edit and the reasoning behind it, so it's auditable rather than
trusted:

- **chi, "How does chi implement its Router interface?"**
  (`chi_queries.json` query 1): `router.go` replaced with `chi.go`.
  chi has never had a file named `router.go` at any commit in its
  history — its router implementation lives in `mux.go` and the
  `Router` interface type itself (`type Router interface { ... }`,
  what the query literally asks about) is declared in `chi.go`.
  Verified by `grep -rn "type Router interface" *.go` against the
  pinned commit (`36611d24`) before editing — `chi.go:68` is the only
  match. **This substitution could only raise the query's score, and
  in fact it already scored without any ground-truth change**: in
  `benchmarks/results/track2_chi.json`, `chi.go` ranks #1 in
  `ranked_files` for this exact query, ahead of `mux.go` — the
  retriever already agreed with this answer on the merits before the
  ground truth was ever touched. The edit brought the label in line
  with what retrieval had already found, not the other way around.
- **chi, "How does chi implement the HTTP method routing (GET, POST,
  DELETE)?"** (query 11): `router.go` dropped outright (kept `mux.go`
  only). `mux.go` alone already defines every HTTP-verb method
  (`Mux.Get`, `Mux.Post`, `Mux.Delete`, ...); `chi.go`'s `Router`
  interface declares no method-routing logic of its own, so unlike
  the previous case there was no better real file to repoint to here
  — dropping was the honest choice.
- **fiber, "How does fiber's error handling and ErrorHandler work?"**:
  `utils.go` dropped (kept `app.go` only). There is no root-level
  `utils.go` at the pinned commit (`e7229b1`) — only per-middleware
  variants (`middleware/logger/utils.go`, `middleware/cors/utils.go`,
  ...), none of which is a more specific match than the file already
  listed. `app.go` alone defines `ErrorHandler`, `DefaultErrorHandler`,
  and the config field that wires them together, so nothing was lost.
- **fiber, "How does fiber implement WebSocket support?"**: query
  removed entirely, not repointed. At the pinned commit there is no
  `middleware/websocket` directory and no WebSocket middleware
  in-repo at all — fiber v3 moved it to a separate `gofiber/websocket`
  module. No file in this repo answers the question, so no
  `expected_files` edit could have made it answerable; the only
  honest option was to remove the query.

**All four edits could only raise the recall/precision numbers for
their repo — none could lower them, and none touched a query where
the previous, stale answer was actually being retrieved correctly.**
The Track 1 recall delta (chi 0.861→0.917, fiber 0.675→0.737, mean
0.811→0.834, all recorded in `benchmarks/results/SUMMARY.md`) is
**definitional, not a retrieval improvement**: no code changed between
those two numbers (see `git show 3df5c40 --stat`), only which files
counted as correct. It must never be cited as evidence the retriever
got better — it is evidence three ground-truth entries were wrong.
The module-symbol-synthesis change in the same session (`f803314`,
fastapi 0.700→0.825) is the one delta in this project's history that
*is* a retrieval improvement, because it followed a code change with
no ground-truth edit alongside it.

Anyone comparing recall/precision numbers against upstream CCE
results, or against this repo's own pre-b38a7f7 results, should know
the query sets diverge for this reason.

Original project: elara-labs/code-context-engine, MIT License.
See `code-context-engine/LICENSE` (vendored) for the full text.
