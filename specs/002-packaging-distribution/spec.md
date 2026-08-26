# Feature Specification: Packaging, Distribution, and CI

**Feature Branch**: `002-packaging-distribution`

**Created**: 2026-08-27

**Status**: Draft

**Input**: Constitution amendment (Python floor 3.14 → 3.11) plus making CKG installable and continuously verified via packaging, `ckg init`, and CI — no indexing/analysis/retrieval behaviour changes.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Install and run from anywhere (Priority: P1)

A developer installs CKG with `uv tool install .` or `pip install` and runs `ckg --help` from outside the repository. The CLI and MCP server are available as `ckg` and `ckg-mcp` entry points without requiring `PYTHONPATH` hacks or `uv run python cli.py`.

**Why this priority**: Distribution is the contract; if the wheel is broken nothing else is usable. This is the standalone MVP slice.

**Independent Test**: Build wheel and sdist with `uv build`, install into an isolated environment, and assert `ckg --help` and `ckg-mcp` entry points resolve outside the repo.

**Acceptance Scenarios**:

1. **Given** a built wheel, **When** `uv tool install .` runs, **Then** `ckg --help` exits 0 from `/tmp` without `PYTHONPATH`.
2. **Given** `pyproject.toml` with `requires-python >=3.11`, **When** installed on 3.11/3.12/3.13, **Then** import succeeds with no syntax errors (no PEP 695 generics, no `type` statements).

---

### User Story 2 - One-command editor setup (Priority: P2)

A developer runs `ckg init` in their project. CKG detects which editors are present and writes MCP configuration for each: `.mcp.json` (default / `.claude/`), `.vscode/mcp.json` (when `.vscode/` exists), `.cursor/mcp.json` (when `.cursor/` exists), and updates `opencode.json` when present. Existing files are merged, never overwritten wholesale; re-running `ckg init` is idempotent.

**Why this priority**: Manual MCP wiring is error-prone; `init` removes friction for every downstream user and is testable independently of indexing.

**Independent Test**: Create a temporary directory, run `ckg init`, assert `.mcp.json` contains `ckg` entry invoking `ckg-mcp`. Second run reports "already configured" and preserves file contents. Existing unrelated servers are preserved.

**Acceptance Scenarios**:

1. **Given** a fresh directory, **When** `ckg init` runs, **Then** `.mcp.json` is created with `mcpServers.ckg.command == "ckg-mcp"`.
2. **Given** an existing `.mcp.json` with an unrelated server, **When** `ckg init` runs, **Then** both servers coexist and the unrelated entry is preserved.
3. **Given** `ckg` already configured, **When** `ckg init` runs again, **Then** it reports "already configured" and does not modify the file.

---

### User Story 3 - Green CI on every push (Priority: P3)

Every push and pull request runs a lint gate and a cross-platform test matrix. Lint is a single Python 3.12 job running `ruff check .`. Tests run `uv run pytest` on `ubuntu-latest, macos-latest, windows-latest` × `3.11, 3.12, 3.13` with `fail-fast: false`. macOS exercises the documented sqlite-vec fallback (no shim to force sqlite-vec; `retrieval/numpy_vector_store.py` via `storage/db.py::load_vec_extension` returning `False`).

**Why this priority**: Completes the installability contract with continuous verification; ensures the 3.11 floor and fallback paths stay honest.

**Independent Test**: Push to `main` and observe CI: lint passes only when `uv run ruff check .` is clean, and the test matrix passes on all OS/Python combos including macOS fallback.

**Acceptance Scenarios**:

1. **Given** a lint violation, **When** CI runs, **Then** the lint job fails and blocks the PR.
2. **Given** `code-context-engine/` exists as an untracked nested git repo, **When** lint runs, **Then** it is excluded and does not fail the gate.
3. **Given** `tests/fixtures/python_repo/api.py` contains an intentionally unused variable, **When** lint runs, **Then** the fixture is excluded and does not fail the gate.

---

### Edge Cases

- Flat layout with 9 of 11 packages lacking `__init__.py` — build must list packages explicitly; moving to `src/` layout would rewrite import paths in 458 tests.
- `code-context-engine/` is an untracked nested git repo not in `.gitignore` — a single `git add -A` creates a broken submodule gitlink; CI and build must exclude it and `.gitignore` must be updated.
- `uv.lock` resolved against 3.14 — lowering `requires-python` invalidates the lockfile and requires `uv lock` plus a full suite re-run.
- `ckg init` must never overwrite existing MCP configs wholesale; merging is required.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-1**: `pyproject.toml` declares a `[build-system]` using `hatchling` and makes the project buildable (`uv build` produces wheel and sdist).
- **FR-2**: `requires-python` is `>=3.11` and `name` is `code-knowledge-graph`; `description` is a real one-line summary.
- **FR-3**: `[project.scripts]` maps `ckg = "cli:main"` and `ckg-mcp = "mcp_server:main"`; entry points invoke the correct mains.
- **FR-4**: `[tool.hatch.build.targets.wheel]` lists all eleven top-level packages explicitly (`analysis`, `chunking`, `embeddings`, `evaluation`, `graph`, `indexing`, `ingestion`, `models`, `parsing`, `retrieval`, `storage`) plus the two top-level modules `cli.py` and `mcp_server.py`; `tests`, `test_repo`, `specs`, `code-context-engine`, `benchmarks`, `docs` are excluded from the wheel.
- **FR-5**: `mcp_server.py` `instructions=` states support for TypeScript, JavaScript, TSX, JSX, Python, and Go (not just TypeScript/JavaScript).
- **FR-6**: `cli.py` exposes `ckg init [path]` following the existing subparser pattern (`path` second, `nargs="?", default="."`); it detects editors and writes/merges MCP configs invoking `ckg-mcp`, never overwriting wholesale, and is idempotent with "already configured" reporting.
- **FR-7**: `[tool.ruff]` excludes `code-context-engine`, `tests/fixtures`, and `.venv`; `uv run ruff check .` exits clean after auto-fix; fixture `F841` is excluded not fixed.
- **FR-8**: `.gitignore` ignores `code-context-engine/` to prevent broken gitlink.
- **FR-9**: `.github/workflows/ci.yml` defines `lint` (single 3.12, `ruff check .`) and `test` (matrix OS × Python 3.11/3.12/3.13, `fail-fast: false`, `uv run pytest`) using `astral-sh/setup-uv`; macOS proves the sqlite-vec → NumpyVectorStore fallback via `storage/db.py::load_vec_extension`.

### Assumptions

- The tree contains no syntax newer than 3.10 (no PEP 695 generics, no `type` statements; `slots=True` and `X | None` are 3.10+), so the 3.11 floor is safe.
- No `src/` layout move — flat layout is preserved to avoid rewriting 458 test import paths.
- Ruff rule set is not widened beyond defaults in this change.

### Dependencies / Constraints

- Constitution Additional Constraints amended: Python 3.11+, version bump 1.0.0 → 1.1.0.
- Build backend is `hatchling` only; no new runtime dependencies.
- CI must prove the macOS sqlite-vec fallback works rather than shim it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-1**: `uv build` succeeds and the wheel contains all 11 packages plus `cli.py`, `mcp_server.py` (verified via `unzip -l`), and excludes the 6 forbidden directories.
- **SC-2**: `uv tool install .` followed by `ckg --help` from `/tmp` succeeds without `PYTHONPATH`.
- **SC-3**: `uv run pytest -q` reports 458 + init tests passing (464) and `uv run ruff check .` is clean; `uv run python cli.py eval` output is byte-identical to the pre-change baseline (modulo timing jitter).
- **SC-4**: `ckg init` on a fresh dir, on a dir with an existing unrelated server, and idempotent double-run all pass their assertions (file contents merged, not overwritten).
- **SC-5**: CI `lint` and 9-cell `test` matrix are green on push/PR, including macOS cells exercising the NumpyVectorStore fallback.

## Key Entities *(include if feature involves data)*

- **Package**: name `code-knowledge-graph`, version 0.1.0, Python 3.11+, hatchling-built wheel with explicit package list.
- **MCP Config**: JSON files (`.mcp.json`, `.vscode/mcp.json`, `.cursor/mcp.json`, `opencode.json`) containing `mcpServers`/`mcp` entry `ckg -> {command: "ckg-mcp"}`.

## Review & Acceptance Checklist

- [x] Focused on user value, no implementation choices leaked into stories
- [x] All mandatory sections completed
- [x] Requirements are testable and unambiguous within stated assumptions
- [x] Success criteria measurable

*(Execution details live in plan.md and tasks.md per the SDD workflow.)*
