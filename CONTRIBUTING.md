# Contributing to CKG

## Setup

```bash
uv sync
uv run pytest -q
```

## Before opening a PR

```bash
uv run ruff check .                                              # must be clean
uv run pytest --cov --cov-report=term-missing --cov-fail-under=80 # must stay >= 80% branch
uv run pytest -m "not slow" -q                                   # fast subset, same as CI
```

CI (`.github/workflows/ci.yml`) runs the same three checks across
`ubuntu/macos/windows` × Python `3.11/3.12/3.13`, plus a build job that
installs the wheel and runs `ckg init` from outside the checkout — that
proves the packaging config, not just the source.

## Engineering rule

> If you can't point to the line and the test, it isn't done.

Concretely: every change ships with a test that would fail without it,
and every claim in `README.md` (a metric, a count, a "not yet") is
sourced from a command that was actually run, not estimated. Numbers
drift — see `ROADMAP.md` `P6-5` for what that costs when
caught late. Re-run the relevant `Verify:` command before claiming a
task done, don't reason your way to a checkmark.

## Where things live

| Layer | Directory |
|---|---|
| Parsing / symbol extraction | `analysis/`, `parsing/`, `models/` |
| Chunking | `chunking/` |
| Storage (SQLite schema, repositories) | `storage/` |
| Incremental indexing, git hooks, resource governor | `indexing/` |
| Retrieval (hybrid search, reranker) | `retrieval/` |
| Embeddings (local + Ollama) | `embeddings/` |
| CLI, MCP server, dashboard | `ckg/` |
| Evaluation harnesses | `evaluation/`, `benchmarks/` |
| Tests | `tests/` |

`analysis/`, `retrieval/`, `indexing/`, and `storage/` are the semantic
core — PRs touching them get read more carefully than a docs or CLI-flag
change, and should come with the reasoning, not just the diff.

## Reporting a bug

Open a GitHub issue with the `ckg doctor .` output and, if it's a
retrieval-quality issue, the query and expected vs. actual result.

## Security

See `SECURITY.md` — do not open a public issue for a vulnerability.
