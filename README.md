# Code Knowledge Graph (CKG)

<p align="center">
  <strong>Understand your repository before the LLM sees it.<br>Local-first semantic index for AI coding agents — no cloud, no estimates.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.1.0-blue?style=flat-square" alt="version">
  <img src="https://img.shields.io/badge/tests-657%20passed-brightgreen?style=flat-square" alt="tests">
  <img src="https://img.shields.io/badge/coverage-80.53%25%20branch-brightgreen?style=flat-square" alt="coverage">
  <img src="https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square" alt="python">
  <img src="https://img.shields.io/badge/MCP-2.0%20ready-purple?style=flat-square" alt="mcp">
  <img src="https://img.shields.io/badge/license-MIT-yellow?style=flat-square" alt="license">
  <img src="https://img.shields.io/github/actions/workflow/status/Deepjyoti-Sarmah/coding-RAG-system/ci.yml?style=flat-square&label=CI" alt="CI">
</p>

<p align="center">
  <sub>Python 3.11+ · macOS · Linux · Windows · SQLite + sqlite-vec</sub>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Claude_Code-352318?style=for-the-badge&logo=anthropic" alt="Claude Code">&nbsp;
  <img src="https://img.shields.io/badge/Cursor-000?style=for-the-badge" alt="Cursor">&nbsp;
  <img src="https://img.shields.io/badge/VS_Code-007ACC?style=for-the-badge&logo=visualstudiocode" alt="VS Code">&nbsp;
  <img src="https://img.shields.io/badge/Codex-412991?style=for-the-badge" alt="Codex">&nbsp;
  <img src="https://img.shields.io/badge/Gemini-4285F4?style=for-the-badge&logo=google" alt="Gemini">&nbsp;
  <img src="https://img.shields.io/badge/OpenCode-22C55E?style=for-the-badge" alt="OpenCode">
</p>

<p align="center">
  <sub>One index. Every agent. Your code stays on your machine.</sub>
</p>

---

## Quick start — 30 seconds

```bash
uv tool install .              # from checkout — installs `ckg` + `ckg-mcp`
# or: pipx install . / pip install -e .

ckg --version                  # 0.1.0
ckg init --agent all           # auto-wires .mcp.json + .vscode/.cursor/opencode + ~/.codex/config.toml + AGENTS.md
ckg index .                    # build or update .ckg/index.sqlite
ckg status --oneline           # symbols 342 chunks 342 pending 0 gen 12
ckg search "auth flow" --top-k 5
ckg doctor .                   # ✓ index present ✓ lock free ✓ git hook ✓ backend
```

Restart your editor. Every question now hits the local index — not `grep` + re-reading files.

> **Already have Ollama?** `ckg` auto-detects `http://localhost:11434` (`nomic-embed-text 768d`). Without it, `FTS + graph` already gives `definition 0.83 / recall 0.78` on the fixture; `ckg embed` adds vectors when you want them.

---

## What you get

| | Capability | How |
|---|---|---|
| **🔍** | **Hybrid retrieval** | Exact symbol + `CALLS/IMPORTS` graph expansion + FTS5 `porter` + vector cosine (sqlite-vec / numpy fallback), fused by RRF `k=60` + reranker + per-file cap |
| **🔄** | **True incremental** | File hash + `interface_fingerprint` invalidation + `stable_key` identity + `Merkle root_hash` + append-only `INSERT OR REPLACE` chunks — reindex of a 2k-file edit `<200ms` |
| **🔒** | **Local-first, no cloud** | SQLite `WAL` `synchronous=NORMAL` `busy_timeout 5000` + disposable derived state; source is truth |
| **🧠** | **MCP 13 tools** | `index_repository` `repository_status` `definition` `callers` `callees` `search` `imports` `context` `session_*` `record_decision/code_area` — `ckg-mcp` over stdio, `IdleTracker 30m` + memory backoff |
| **🖥️** | **Multi-editor** | `ckg init --agent auto|all` detects `.vscode` `.cursor` `opencode.json` + writes ` ~/.codex/config.toml [mcp_servers.ckg-<hash>]` TOML-escaped + versioned `<!-- ckg-block-version:1 -->` |
| **📊** | **Dashboard + ops** | `ckg dashboard --no-browser` FastAPI 8 endpoints `GET /api/status/files/sessions/savings` `POST /api/reindex` `DELETE /api/files/{path}` `CSRF Sec-Fetch-Site + bearer hmac` + `ckg doctor` |

---

## Benchmark — evaluation_repo (honest, not 94%)

Measured on `tests/fixtures/evaluation_repo` with fixed `token_budget=800` `o200k_base` + `len//4` fallback:

| Metric | Without vectors `FTS+graph` | With vectors |
|---|---|---|
| **definition accuracy** | **0.83** | 0.92 |
| **mean recall@5** | **0.78** | 0.97 |
| **MRR** | 0.71 | 0.94 |
| **initial indexing** | ~18ms (fixture) | same + embed queue |
| **incremental (`parsed_files==0`)** | `<50ms` | `cache_hit_rate 1.0` |
| **coverage** | **80.53% branch** | `657 passed 0 skipped` |

Token savings are reported as `ExternalReport.mean_savings_pct` at `budget 800` with `baseline = expected_files only` (`evaluation/external.py:184`) — whole-repo `99%` is intentionally `0.0` (`evaluation/runner.py:202`). Cited with `mean_recall@10 + p50` or not at all. See `benchmarks/run_external.py`.

---

## Supported languages

**AST-aware (tree-sitter, stable extractors):**

| Language | Extensions | Symbol kinds |
|---|---|---|
| TypeScript / TSX / JavaScript / JSX | `.ts .tsx .js .jsx` | `function class method variable interface type_alias` + `property_signature/method_signature` children |
| Python | `.py` | `function class` (decorators preserved) |
| Go | `.go` | `function method type_spec (struct embedding → EXTENDS)` |
| Java | `.java` | `class interface enum record method field` |
| Rust | `.rs` | `function struct enum trait type const mod` |
| C# | `.cs` | `class struct enum record interface method property field` |
| C / C++ | `.c .h .cpp .hpp .hh` | `function declaration struct enum class namespace` + `DEFINITION_OF` |

**Fallback (40+ extensions, `MODULE` synthetic symbol via `chunking/symbol_chunker.py:37`):**
`html css scss less vue svelte json yaml toml xml sql graphql proto tf hcl dockerfile md` + `rb php swift kt sh bash` — indexed as `module <path>` chunks, searchable like code.

---

## CLI at a glance

| Command | Example | What it does |
|---|---|---|
| `ckg index <path> [--embed] [--no-background]` | `ckg index .` | Build/update `.ckg/index.sqlite` (only changed files reparsed) |
| `ckg status [path] [--oneline]` | `ckg status --oneline` | `symbols 342 chunks 342 pending 0 gen 12` |
| `ckg search <query> [path] [--top-k N] [--no-vector]` | `ckg search "login"` | Hybrid RRF search |
| `ckg definition <name>` | `ckg definition createAuth` | Exact symbol definition |
| `ckg callers <name>` | `ckg callers login` | `CALLS` incoming 1-hop |
| `ckg callees <name>` | `ckg callees login` | `CALLS` outgoing 1-hop |
| `ckg imports <file>` | `ckg imports api.ts` | Imports + resolved `::symbol` |
| `ckg context <query> [--budget N] [--top-k N]` | `ckg context "how does login work?" --budget 800` | Token-budgeted `primary/supporting` pack |
| `ckg eval [--embed] [--top-k N]` | `ckg eval` | Fixed fixture metrics |
| `ckg watch <path> [--no-embed] [--debounce 0.5]` | `ckg watch .` | `watchdog` debounced reindex + `embed limit 200` |
| `ckg init [path] [--agent auto|all] [--plugin]` | `ckg init --agent all` | Wire MCP for all detected editors + git hooks |
| `ckg uninstall [path]` | `ckg uninstall` | Remove MCP entries + hooks |
| `ckg embed [path] [--limit N]` | `ckg embed` | Drain `PENDING → DONE` queue (`content_hash` reuse) |
| `ckg doctor [path] [--verbose]` | `ckg doctor .` | `index present / lock free / queue pending / git hook / backend` |
| `ckg dashboard [path] [--port 8765] [--allow-remote]` | `ckg dashboard --no-browser` | `127.0.0.1` read-only, `CSRF + CKG_DASHBOARD_TOKEN hmac`, `POST /api/reindex` `DELETE /api/files/{path}` |
| `ckg sessions <start|list|status|timeline|recall|export|prune>` | `ckg sessions recall auth .` | Local `session.sqlite` decisions/code_areas/retrieval history |
| `ckg eval-ab --manifest evaluation/tasks.json [--agent-command "$CMD"]` | `ckg eval-ab --pilot --preflight` | Paired `with_ckg/without_ckg` worktrees, `null stays null` |

`ckg --help` shows per-command examples. Override DB with `ckg --db /tmp/x.sqlite <cmd>`.

**11 MCP tools + 2 session tools** via `ckg-mcp` stdio: `index_repository` `repository_status` `definition` `callers` `callees` `search` `imports` `context` `session_start/end/status/recall/timeline` `record_decision/code_area`.

---

## How it works

```text
Repository
    ↓  .gitignore/.ckgignore — ingestion/loader.py
Scan + hash (mtime fast-path)
    ↓  indexing/diff.py + merkle.py root_hash
ParsedDocument (tree parsed once, thread-local)
    ↓  parsing/tree_sitter_parser.py
Symbol / Import / Export / Reference passes
    ↓  analysis/pipeline.py + symbol_handlers/*
Resolution (scope climb inner→outer→module→imports) + heritage
    ↓  analysis/semantic/* + import_resolver
Relationships CALLS/EXTENDS/IMPLEMENTS/HAS_TYPE/RETURNS/DEFINES
    ↓  CodeGraph graph/code_graph.py
Semantic chunks (symbol + parent + calls + called_by + imports)
    ↓  chunking/symbol_chunker.py content_hash v1
FTS5 porter + vector sqlite-vec/numpy + EmbeddingJob PENDING→DONE
    ↓  storage/schema.py generation
Hybrid RRF(k=60) + graph expand (budget 6+2) + reranker + per-file cap 3 + budget 800
    ↓  retrieval/hybrid_retriever.py + reranker.py + context_builder.py
LLM gets primary/supporting + relationships + file_paths — not 50k tokens
```

Reindex after edit: `Merkle` subtree check → `interface_fingerprint` importers → `stable_key` `INSERT OR REPLACE` → `content_hash` reuse → `bump_generation`.

---

## Dashboard + ops

```bash
ckg dashboard . --no-browser --port 8765
# → http://127.0.0.1:8765  GET /api/status /api/files /api/sessions /api/savings
# POST /api/reindex  DELETE /api/files/a.html  (400 on .., 401 on bad bearer, 403 on cross-site)

CKG_DASHBOARD_TOKEN=secret ckg dashboard --allow-remote  # remote needs flag + token
ckg doctor --verbose
# ✓ index present: .ckg/index.sqlite
# ✓ lock free: free (.ckg/.index.lock fcntl)
# ✓ embedding queue: pending=0
# ✓ git hook: .git/hooks/post-commit CKG keep-fresh
# ✓ embedding backend: local:all-MiniLM-L6-v2:384 (FALLBACK: FTS+graph 0.83/0.78 ok)
```

Git hook `indexing/git_hooks.py` on `ckg init`: `post-commit/post-checkout/post-merge nice -n10 ckg index &` with `/tmp/ckg-index-hook.lock` stale PID + `watcher.py` debounced `0.5s` secondary.

---

## Security — redacted before it is indexed

| Layer | Detail | File |
|---|---|---|
| **Skip** | `.env* credentials.json secrets.yml .env.local .pem/.key/.p12/.jks` filename deny-list before open | `indexing/secrets.py:58 is_secret_filename` |
| **Content 15 regex** | `AKIA aws_secret_access_key ghp_ github_pat_ ghs/gho/ghu/ghr xox[abprs]- sk_live sk-..T3BlbkFJ sk-ant- AIza eyJ..JWT PRIVATE KEY + GENERIC_CREDENTIAL dotenv 16+` | `indexing/secrets.py:6` |
| **Placeholder exempt** | `your-api-key xxxxx my-api-key your-secret test_key` not redacted | `indexing/secrets.py:24` |
| **PII** | `EMAIL IPV4 SSN PHONE E164 + CARD Luhn` (`411111… valid → [REDACTED:CARD]`, `1234… invalid → keep`) | `indexing/secrets.py:84 redact_pii` |
| **Traversal** | `resolved.relative_to(project)` in `indexer/pipeline.py`, `dashboard DELETE .. \ / 400` | `storage/index_store.py` |
| **WAL** | `PRAGMA journal_mode=WAL synchronous=NORMAL foreign_keys=ON busy_timeout 5000` | `storage/db.py:11` |
| **Lock** | `fcntl.flock .ckg/.index.lock LOCK_EX|LOCK_NB` + `ProjectIndexLock` context | `indexing/resource_governor.py:61` |

See `indexing/resource_governor.py:12 onnx_thread_cap CCE_ORT_THREADS` + `is_memory_pressured PSI avg10>25` + `MAX_FILE 2MB` + `TOKENIZERS_PARALLELISM false`.

---

## Token methodology — how to cite X%

Do not cite `99% whole-repo`. Pair `mean_savings_pct + mean_recall@10 + p50` at fixed `budget 800`:

```bash
python benchmarks/run_external.py --repo https://github.com/fastapi/fastapi --source-dir . \
  --queries benchmarks/fastapi_queries.json --output benchmarks/results/fastapi.json
python benchmarks/run_external.py --recompute "benchmarks/results/*.json"  # mean_savings + recall
ckg eval-ab --manifest evaluation/tasks.json --condition both --output results/ --agent-command "$AGENT_CMD"
```

* `baseline = expected_files only` (`evaluation/external.py:184`) `context = build_context_pack(budget 800)` (`:197`) `ExternalReport.mean_savings_pct` — honest.
* `evaluation/runner.py:202 token_reduction=0.0` (whole-repo indefensible) `dashboard/server.py:94 savings sum-over-events` not per-query.
* `eval-ab` `total_tokens null stays null` (`ab_runner.py:17` never fabricated) requires real agent `CKG_AB_* env`.

---

## Current status — what 0.1.0 is, what is not

**Shipped (657p 80.53% branch, `IMPLEMENTATION.md` phases `COMPLETE`):** tree-sitter parse once, document load, symbol/index, reference + member-expression `auth.client.createAuth`, cross-file import/export resolve incl. `re_export export * from` + `export {x} from`, `CALLS/EXTENDS/IMPLEMENTS/HAS_TYPE/RETURNS`, interface `property_signature/method_signature` as child symbols, SQLite `13 tables + vec0 + FTS5 porter`, incremental `hash + Merkle root_hash + interface-aware reresolve`, semantic chunks `content_hash`, `FTS + vector + exact + graph expand 6+2 + RRF + reranker + per-file cap 3 + budget 800`, `FTS+graph 0.83/0.78` out-of-box, `ckg 13 cmds + ckg-mcp 13 tools`, `doctor + dashboard 8 endpoints CSRF+bearer hmac`, `eval + eval-ab 20 tasks`.

**Not yet (deliberate, not oversights):** `learned_weights.json` heuristic `relationship 1.15` needs real `AGENT_CMD` train; `export *` wildcard `target_symbol None`; `P5-2` append-only already `INSERT OR REPLACE` but `chunks_fts prune_not_in` not yet `HNSW`.

**In progress:** `P5` `learned reranker train + large-repo proof + parse-once hypothesis`.

**Planned:** `Docker remote` `fastembed→sqlite-vec HNSW` `C/C++ overload DEFINITION_OF refinement`.

`IMPLEMENTATION.md` per-phase `### Implemented` is authoritative.

---

## v1 definition of done

- [x] TS/JS reliable, parse once
- [x] Symbols/imports/exports/references resolved for common cases (cross-file + member)
- [x] Graph persisted SQLite + generations
- [x] Incremental detected (Merkle) + chunk reuse via `content_hash`
- [x] FTS + vector locally + graph expansion + hybrid top-k
- [x] Context from entities not whole files (budget 800)
- [x] Agent can `ckg search/definition/callers/callees/context` via MCP
- [x] Eval measures `recall/MRR/latency/tokens` + `doctor` prod check

---

## Engineering rule

```
Correctness → Semantic completeness → Persistence → Incremental → Retrieval → Performance → Agents
```

> Understand the repository first. Retrieve only what matters. Then let the LLM reason.

Only the next layer may be optimized; never embed before resolution is trustworthy. See `specs/` + `IMPLEMENTATION.md` phases `0..24`.

---

## Session memory + dashboard (local only)

```bash
ckg sessions start . && ckg sessions recall "auth decision" --limit 10
ckg dashboard . --no-browser  # http://127.0.0.1:8765 read-only, localhost by default
rm -rf .ckg/session.sqlite    # wipe memory
```

Bounded `MAX_TEXT 2000` `redact_secrets + redact_pii` on `_bounded`. Raw source/tool output never stored. `prune --days 30`.

---

## Release smoke

```bash
uv build
python scripts/release_smoke.py  # wheel outside checkout: ckg --help + init + index + search + ckg-mcp startup
```

Offline needs `uv cache` wheels.

---

## Comparing to Code Context Engine (CCE 0.4.26)

We use CCE as a yardstick, not a template:

| Dimension | CCE 0.4.26 `19k LOC` | CKG 0.1.0 `657p 80.53%` |
|---|---|---|
| Semantic depth | `Chunk FUNCTION/CLASS + IMPORTS/DEFINES` `confidence 0.5dist` | `Symbol stable_key + signature + CALLS/EXTENDS/IMPLEMENTS/HAS_TYPE/RETURNS + member path auth.client.createAuth + re_export` |
| Incremental | `manifest sha256 + 96% cache 50-batch` | `hash + Merkle root_hash + interface_fingerprint reresolve + INSERT OR REPLACE` |
| Retrieval | `RRF k=60 + recency 0.1` | `RRF k=60 + graph 6+2 + reranker + cap 3 + budget 800 + learned_weights.json hook` |
| Ops | `governor PSI/ORT/Idle 30m + FastAPI 8 + 851 tests` | `governor fcntl/PSI/ORT + dashboard 8 hmac+CSRF + doctor 5 checks + 657p fuzz+e2e+gate` |
| Honesty | `94% full-file baseline` | `0.83/0.78 FTS+graph, whole-repo 0.0, external expected_files only` |

CKG’s moat is `Symbol` not `Chunk` — graph before vector — measured with `expected_files` not `full-repo`.

---

## License

MIT — see `LICENSE`. Authors: see `pyproject.toml` `Fazle Elahee / Raj` fork + `Deepjyoti` parity landings `ckg/editors` `secrets Luhn` `merkle`.

*If CKG saves you tokens, give it a star and cite `budget 800 + commit SHA`.*
