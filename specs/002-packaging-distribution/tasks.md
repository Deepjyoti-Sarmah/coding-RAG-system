# Tasks: Packaging, Distribution, and CI

**Input**: [plan.md](plan.md) | **Branch**: `002-packaging-distribution`

## 1. Constitution amendment

- [x] 1.1 Amend `.specify/memory/constitution.md` Additional Constraints `Python 3.14+` → `Python 3.11+`, bump `Version 1.0.0` → `1.1.0`, set `Last Amended` to 2026-08-27, leave `Ratified` unchanged — own commit with body explaining 3.10-compatibility and that 3.14 blocks distribution

## 2. Make the package buildable

- [x] 2.1 Add `[build-system]` (`hatchling`) to `pyproject.toml`; change `requires-python` to `>=3.11`, `name` to `code-knowledge-graph`, replace placeholder `description`
- [x] 2.2 Add `[project.scripts]` `ckg = "cli:main"` and `ckg-mcp = "mcp_server:main"`; add `[tool.hatch.build.targets.wheel]` listing all 11 packages plus `cli.py`/`mcp_server.py` (and `config.py` for runtime) via `force-include`; exclude `tests`, `test_repo`, `specs`, `code-context-engine`, `benchmarks`, `docs` from wheel/sdist
- [x] 2.3 Run `uv lock` after `requires-python` change and re-run full suite (458 passed before init tests)

## 3. Ruff and gitignore

- [x] 3.1 Add `[tool.ruff] exclude = ["code-context-engine", "tests/fixtures", ".venv"]` (and `[tool.ruff.lint] ignore = ["TC004"]` to avoid churn from a newly-defaulted rule); add `.gitignore` entry for `code-context-engine/`
- [x] 3.2 Run `uv run ruff check . --fix`, manually resolve remaining (if any), and verify `uv run ruff check .` is clean; exclude the intentional `F841` in `tests/fixtures/python_repo/api.py` rather than fixing the fixture
- [x] 3.3 Add `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, `norecursedirs` for `code-context-engine`) so bare `uv run pytest -q` reports 458 passed

## 4. Stale string

- [x] 4.1 Fix `mcp_server.py` `MCPServer(instructions=...)` from "a TypeScript/JavaScript repository" to mention TypeScript, JavaScript, TSX, JSX, Python, and Go

## 5. `ckg init`

- [x] 5.1 Add `init` subcommand to `cli.py` following `build_parser()` `path` second / `nargs="?", default="."` convention; implement detection (always `.mcp.json`, `.vscode/ → .vscode/mcp.json`, `.cursor/ → .cursor/mcp.json`, `opencode.json` → update) with merge-only semantics, `ckg-mcp` entry, "already configured" reporting, and printing what was written
- [x] 5.2 Add tests in `tests/test_cli.py` (`TestCliInit`) covering fresh directory, preserving unrelated server, idempotent double-run, `.vscode`/`.cursor` when present, `opencode.json` update, and no `.vscode` creation when dir missing

## 6. CI

- [x] 6.1 Create `.github/workflows/ci.yml` with `lint` (single 3.12 `ruff check .`) and `test` (matrix `os: [ubuntu, macos, windows]` × `python-version: ["3.11","3.12","3.13"]`, `fail-fast: false`, `uv run pytest`) using `astral-sh/setup-uv`; document macOS sqlite-vec → NumpyVectorStore fallback (no shim)

## 7. Definition of done

- [x] 7.1 Verify `uv run pytest -q` (464 passed), `uv run ruff check .` clean, `uv run python cli.py eval` byte-identical to baseline, `uv build` produces wheel+sdist, `uv tool install .` succeeds, `ckg --help` runs from `/tmp`
