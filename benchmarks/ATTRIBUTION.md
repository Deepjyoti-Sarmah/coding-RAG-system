# Attribution

The query sets in this directory are copied from the vendored project
`code-context-engine` (https://github.com/elara-labs/code-context-engine),
which is published under the MIT License:

- `express_queries.json` — 20 queries expecting files under `lib/` in https://github.com/expressjs/express
- `fastapi_queries.json` — 20 queries expecting files under `fastapi/` in https://github.com/fastapi/fastapi
- `chi_queries.json` — 18 queries expecting files under `.` in https://github.com/go-chi/chi
- `fiber_queries.json` — 20 queries expecting files under `.` in https://github.com/gofiber/fiber
- `django_queries.json` — 22 queries expecting files under `django/` in https://github.com/django/django

Total: 100 queries.

The JSON format and expected file lists are taken verbatim from
`code-context-engine/benchmarks/*_queries.json`. No queries were
added, removed, or modified; they are reproduced here for the
external benchmark harness (`benchmarks/run_external.py` and
`evaluation/external.py`) which evaluates file-level retrieval
(precision@10 / recall@10 / MRR) rather than symbol-level.

Original project: elara-labs/code-context-engine, MIT License.
See `code-context-engine/LICENSE` (vendored) for the full text.
