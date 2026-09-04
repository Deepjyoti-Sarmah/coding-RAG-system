# Changelog

All notable changes to CKG (Code Knowledge Graph) are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
this project uses [SemVer](https://semver.org/).

## [Unreleased]

- Packaging/publish readiness — see `ROADMAP.md` `P6`.
- Removed the external benchmark data (`benchmarks/*_queries.json`,
  `benchmarks/results/`) and its attribution file — those query sets
  were derived from a third-party project's benchmark suite, and this
  project no longer ships anything derived from another project's work.
  A real-repo benchmark with original queries is planned (`ROADMAP.md`
  `P5-4`). `CCE_ORT_THREADS` renamed to `CKG_ORT_THREADS`.

## [0.1.0] — 2026-09-04

First tagged release. Seeded from `feat(P*)` commit history (224 commits
total); grouped by area rather than listed commit-by-commit.

### Added

- **Symbol graph** — tree-sitter based multi-language extraction (Python,
  JS/TS/TSX/JSX, Go, Rust, Java, C#, C, C++), stable-key symbols with
  `CALLS` / `EXTENDS` / `IMPLEMENTS` / `HAS_TYPE` / `RETURNS` /
  `DECLARES` relationships and cross-file import/export resolution,
  including `export * from` / `export {x} from` re-exports and
  `property_signature` / `method_signature` interface members.
- **Hybrid retrieval** — FTS5 (per-column BM25 weights) + sqlite-vec
  cosine (numpy fallback where the extension can't load) + exact-symbol +
  graph expansion, fused by RRF and a learned/tuned reranker with a
  per-file cap and token budget.
- **Incremental indexing** — Merkle-hashed change detection, append-only
  chunk reuse via `content_hash`, interface-aware re-resolution instead
  of full snapshot rewrites, embedding-dimension migration on model change.
- **CLI** — `ckg init` (8-editor matrix: Claude, Cursor, VS Code, OpenCode,
  Gemini, Copilot, Pi, Codex, plus `--agent all`), `index`, `status`,
  `search`, `definition`, `callers`, `callees`, `imports`, `context`,
  `embed`, `recall`, `timeline`, `export`, `prune`, `doctor`, `eval` /
  `eval-ab`, `uninstall`.
- **MCP server** (`ckg-mcp`) — exposes the same tool surface to agents
  over the Model Context Protocol.
- **Ops** — resource governor (PSI/ONNX-thread caps, idle tracker,
  memory-pressure backoff), file locking for concurrent `ckg index`, git
  hooks (`post-commit`/`post-checkout`/`post-merge`) for keep-fresh
  reindexing, a local FastAPI dashboard (HMAC bearer auth + CSRF checks,
  8 endpoints) with a coverage/savings view.
- **Security** — secret redaction (15+ regexes incl. Luhn-validated card
  numbers, `GENERIC_CREDENTIAL` heuristic) and PII scrubbing applied
  before anything is indexed or stored in session memory.
- **Evaluation** — fixed-benchmark suite (`ckg eval`), paired A/B harness
  (`ckg eval-ab`) against real coding-agent runs, and a reusable
  external file-level benchmark harness (`benchmarks/run_external.py`)
  for running against any repo with a `{query, expected_files}` set.
- **Session memory** — local, project-scoped decision/code-area/timeline
  recall, redacted the same way as the index.

### Packaging (this release)

- `LICENSE` (MIT) with third-party notice for the `code-context-engine`
  derived benchmark query sets.
- `ruff` added as a dev dependency and the codebase's first lint pass
  cleaned (116 findings on first run — this project had never been
  linted before).
- `hypothesis` and `httpx` added as dev dependencies — both were
  previously only pip-installed by hand, so their gated tests had been
  silently skipping in every clean environment, including CI.
- `mcp` capped `<3`, `tree-sitter` capped `<0.26` — both were unbounded
  and `uv tool install` ignores `uv.lock`; the tree-sitter cap fixed a
  live ABI mismatch this exact repo had already resolved into.
- PyPI metadata (`authors`, `keywords`, `classifiers`, `project.urls`)
  and a trusted-publishing (OIDC) `publish.yml`.

[Unreleased]: https://github.com/Deepjyoti-Sarmah/coding-RAG-system/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Deepjyoti-Sarmah/coding-RAG-system/releases/tag/v0.1.0
