# Implementation Plan: Packaging, Distribution, and CI

**Branch**: `002-packaging-distribution` | **Date**: 2026-08-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-packaging-distribution/spec.md` and Constitution amendment (3.14 → 3.11, v1.0.0 → v1.1.0).

## Summary

Make CKG installable and continuously verified without changing indexing/analysis/retrieval behaviour: add a `hatchling` build system, fix package discovery for 9 of 11 namespace packages lacking `__init__.py`, expose `ckg`/`ckg-mcp` entry points, add `ckg init` editor detection/merging, exclude `code-context-engine` and fixtures from lint/build, and add a cross-platform CI matrix that proves the macOS sqlite-vec → NumpyVectorStore fallback.

## Technical Context

**Language/Version**: Python 3.11+ (amended; tree is 3.10-compatible)
**Primary Dependencies**: `hatchling` (new build backend), existing `mcp`, `sqlite-vec`, `tree-sitter` stack unchanged
**Storage**: unchanged (SQLite via storage/)
**Testing**: existing 458-test suite plus 6 new `ckg init` tests; `uv lock` after `requires-python` change
**Target Platform**: Linux CLI / MCP server (unchanged), wheel + sdist via `uv build`
**Performance Goals**: unchanged — packaging does not alter indexing/retrieval
**Constraints**: flat layout preserved (no `src/` move); 9 namespace packages listed explicitly; no new runtime deps; ruff rule set not widened
**Scale/Scope**: packaging, lint config, `ckg init`, CI, docs; zero edits to core pipeline except import-sort auto-fixes

## Constitution Check

| Principle | Status |
|---|---|
| I Local-first | PASS — `hatchling` is offline build dep; no cloud/service additions |
| II Incremental = full | PASS — no indexing/chunking/storage changes; parity tests untouched |
| III Tests before moving forward | PASS — `ckg init` lands with unit tests; suite stays green before every commit |
| IV Neutral core | PASS — packaging/CLI/CI are edge concerns; no shared-pipeline edits |
| V Layering | PASS — `cli` → `indexing` → `storage` direction preserved; `ckg init` is pure CLI |
| VI Measure | PASS — `uv run python cli.py eval` byte-identical to baseline |
| VII Simplicity | PASS — explicit package list over `src/` move; minimal CI; no speculative abstractions |

## Decisions

1. **Build backend**: `hatchling` via `[build-system]` (`hatchling.build`). Top-level packages listed explicitly in `[tool.hatch.build.targets.wheel] packages = [11]` because 9 are implicit namespace packages. Two top-level modules `cli.py`, `mcp_server.py` (plus `config.py` for runtime) included via `[tool.hatch.build] force-include`; `src/` layout rejected because it rewrites 458 test import paths.

2. **Package name and Python floor**: `name = "code-knowledge-graph"`, `requires-python = ">=3.11"`, `description` replaced. Constitution "Additional Constraints" amended to `Python 3.11+` with version bump `1.0.0 → 1.1.0` and governance commit message explaining 3.10-compatibility (`slots=True`, `X | None`) and that 3.14 blocks distribution. `uv lock` re-resolved after the floor change.

3. **Entry points**: `[project.scripts] ckg = "cli:main"`, `ckg-mcp = "mcp_server:main"` — both `main` signatures (`cli.py:352` `argv list | None -> int`, `mcp_server.py:208` `-> None`) match hatch entry-point expectations.

4. **Ruff**: `[tool.ruff] exclude = ["code-context-engine", "tests/fixtures", ".venv"]`; `TC004` ignored via `[tool.ruff.lint] ignore = ["TC004"]` to avoid churn from a newly-defaulted rule that wasn't in the original baseline (fixture `F841` is intentional test data and must be excluded, not fixed). `I001` auto-fixed in `analysis/` plus `PIE800`/`I001` in `tests/`. `uv run ruff check .` must be clean; CI lint gate will otherwise go red on first run.

5. **`ckg init`**: Follows `build_parser():273` subparser pattern with `path` second (`nargs="?", default="."`). Detection → file: always `.mcp.json` (default / `.claude/`), `.vscode/ → .vscode/mcp.json`, `.cursor/ → .cursor/mcp.json`, `opencode.json →` update. Entry invokes `ckg-mcp` (`{"command": "ckg-mcp"}`). Merge semantics: read existing JSON, preserve all keys, add `mcpServers.ckg` (or `mcp.ckg` for `opencode.json`), check any of `mcpServers`/`servers`/`mcp` for existing `ckg` and report "already configured" without overwriting.

6. **CI**: `.github/workflows/ci.yml` with `lint` (single `ubuntu-latest`, 3.12, `ruff check .`) and `test` (matrix `os: [ubuntu, macos, windows] × python-version: ["3.11","3.12","3.13"]`, `fail-fast: false`, `uv run pytest`) via `astral-sh/setup-uv`. macOS deliberately has no sqlite-vec shim; the `retrieval/numpy_vector_store.py` fallback via `storage/db.py::load_vec_extension` returning `False` is the feature under test for those cells.

7. **Git hygiene**: `code-context-engine/` is an untracked nested git repo not yet gitignored; `git add -A` would create a broken gitlink. Add it to `.gitignore`, exclude from ruff and from the wheel/sdist (`[tool.hatch.build.targets.sdist] exclude`), and forbid `git add -A` / `git add .` in commits.

## Project Structure

```text
.specify/memory/constitution.md        # amended 3.11+, v1.1.0
pyproject.toml                          # build-system, requires-python, scripts, hatch wheel/sdist, ruff, pytest
.gitignore                              # + code-context-engine/
cli.py                                  # build_parser init, cmd_init, _ensure_mcp_entry, main dispatch
mcp_server.py                           # instructions fix (TS/JS/TSX/JSX/Python/Go)
tests/test_cli.py                       # + TestCliInit (fresh, preserve, idempotent, vscode/cursor, opencode, no-vscode)
.github/workflows/ci.yml                # lint + 9-cell test matrix
specs/002-packaging-distribution/{spec,plan,tasks}.md
```

Changed registrations: none in `analysis/` business logic; only `pyproject.toml`, `cli.py`, `mcp_server.py`, `.gitignore`, CI, docs, and `uv.lock`.

Tests: 458 existing + 6 new `ckg init` = 464 passing; `uv run ruff check .` clean; `uv build` wheel/sdist contain 11 packages + 3 top-level modules and exclude 6 forbidden dirs.

## Phase 0 Research (verified empirically before touching anything)

- `uv run pytest -q tests` → 458 passed (bare `uv run pytest -q` collected 133 errors from `code-context-engine/tests`).
- `uv run ruff check .` → 8 errors (4 `I001` in `analysis/`, 1 `F541` in `code-context-engine`, 1 `F841` in `tests/fixtures/python_repo/api.py`, 1 `PIE800` + 1 `I001` in `tests/`); fixture `F841` is deliberate.
- `ls` → 9 of 11 top-level packages have no `__init__.py` (`analysis`, `retrieval`, `models`, `indexing`, `graph`, `parsing`, `chunking`, `ingestion`, `embeddings`); only `storage`, `evaluation` have it.
- `ls -la code-context-engine/.git` → nested repo; not in `.gitignore`.
- `cat pyproject.toml` → 24 lines, no `[build-system]`, `requires-python >=3.14`, `name = rag-pipeline`, placeholder description.
