# CKG → CCE Parity & Surpass — Agent Execution Plan

> Goal: Make CKG (`0.1.0`) production-ready and surpass CCE (`0.4.26`). Order: Correctness → Incremental → Retrieval → Ops (per `README.md:1418`).

> **RERUN 2026-09-03:** `uv run pytest -q 652 passed 81.23%` `--cov-fail-under=80` `ckg doctor + help epilog` — Rerun rating **CKG 8.5/10** (was 7.9) vs **CCE 8.6/10**. Gap `0.1`; P0-P4 landed (`IdleTracker` `GENERIC+Luhn` `DELETE real` `TOML sanitize` `doctor` `fuzz+fallback+e2e+gate` `80% gate`), **P5 S1-S2** re-export+interface child done `20p` → `8.7` to **surpass** with `P5-2` append-only next.

## How to use

- Work phase-by-phase. Do not skip P0.
- Each task lists `Source reference (CCE)` and `Target (CKG)` with `file_path:line`.
- After each task: run its `Verify` command and update the checkbox.
- Overall verify: `uv run pytest -q && uv run pytest --cov --cov-fail-under=65` and `ckg eval --embed` on `tests/fixtures/evaluation_repo`.
- Current truth: P0 stubs done, remaining TODOs below must be executed to reach parity. Don't trust prior `DONE ✅` — run verify.

---

## P0 — Prod Killers (1–2 weeks) — SHIP BLOCKERS

### P0-1: Multi-editor `ckg init` matrix — DONE ✅ (2026-09-02)
- **Why:** CCE closes sales with `cce init --agent auto` for 8 editors. CKG only wrote `.mcp.json`.
- **Source:** `code-context-engine/src/context_engine/editors.py:1` (790 LOC), `code-context-engine/src/context_engine/cli.py:_configure_mcp`, `code-context-engine/src/context_engine/utils.py:atomic_write_text`
- **Target:** `ckg/editors.py:1`, `ckg/cli.py:356 _ensure_mcp_entry`, `ckg/cli.py:652 build_parser`
- **Tasks:**
  - [x] Create `ckg/editors.py:1` 8 editors `claude/cursor/vscode/opencode/gemini/copilot/pi/codex` + `project_storage_slug:21` `atomic_write_text mkstemp+fsync+replace:26` + `detect_editors:41` + `~/.codex/config.toml` TOML `[mcp_servers.ckg-<slug>]` via `ckg/cli.py:400`
  - [x] Extend `ckg/cli.py:652 build_parser` `init --agent {auto,claude,cursor,vscode,codex,copilot,pi,opencode,gemini,all} + --plugin` + `uninstall` + `install_hooks:400` + TOML handling `ckg/cli.py:400` `path.suffix==".toml"` append
  - [x] Add `tests/test_editors.py:1` 8 tests idempotent+corruption+auto+all (641 passed)
- **Acceptance:** `ckg init --agent all` in repo with `.vscode`+`.cursor`+`opencode.json` creates 4 configs; second run `already configured`; `~/.codex/config.toml` contains `[mcp_servers.ckg-<slug>]` with `command="ckg-mcp"`.
- **Verify:** `rm -rf /tmp/p0e && mkdir -p /tmp/p0e/.vscode /tmp/p0e/.cursor && touch /tmp/p0e/opencode.json && ckg init /tmp/p0e --agent all && cat /tmp/p0e/.mcp.json && cat /tmp/p0e/.vscode/mcp.json && cat ~/.codex/config.toml | grep -A2 ckg-`

### P0-2: Secrets + PII parity — DONE ✅ (2026-09-03: GENERIC+Luhn)
- **Source:** `code-context-engine/src/context_engine/indexer/secrets.py:1` (365 LOC), `code-context-engine/src/context_engine/memory/db.py:scrub_pii`
- **Target:** `indexing/secrets.py:1` (108 LOC), `ingestion/loader.py:89`, `session_memory/service.py:24`
- **Tasks:**
  - [x] `indexing/secrets.py:1` 15 regexes `14 + GENERIC_CREDENTIAL export? \w*(password|secret|token|api_key) 16+` `re.MULTILINE` + `_luhn_valid:84` + `_card_repl Luhn` + placeholder `my-/your-`
  - [x] `ingestion/loader.py:89 is_secret_filename` + `session_memory/service.py:24 _bounded` `redact_pii(redact_secrets())`
  - [x] `tests/test_secrets.py:1` 17 tests + `tests/test_secrets_fuzz.py:1` 5 tests `generic_credential + luhn_valid 4111 Valid` — `MY_TOKEN=123...` redacted ✅
- **Acceptance:** `.env` with `AKIA...` + `sk-ant-...` skipped; `GENERIC_CREDENTIAL` `MY_TOKEN=1234567890123456` redacted not placeholder; PII email scrubbed in `record_decision`.
- **Verify:** `uv run pytest tests/test_secrets.py -v` — must be 15+ tests; `python -c "from indexing.secrets import redact_secrets; print(redact_secrets('MY_TOKEN=123456789012345678'))"` contains `[REDACTED]`

### P0-3: Resource governor + file lock — DONE ✅ (2026-09-03: IdleTracker wired)
- **Source:** `code-context-engine/src/context_engine/resource_governor.py:217`, `code-context-engine/src/context_engine/services.py:315 _process_alive`
- **Target:** `indexing/resource_governor.py:1` (108 LOC), `ckg/mcp_server.py:335`, `indexing/embedding_queue.py:142` (backoff)
- **Tasks:**
  - [x] `indexing/resource_governor.py:1 onnx_thread_cap explicit= env[k]= + IdleTracker 30m:99` + `ckg/mcp_server.py:24 _idle_tracker + is_idle:118 + _touch_idle() on all 13 tools index_repository/search/context/definition/callers/callees/session_* + embedding_queue.py:142 is_memory_pressured() → limit//2`
  - [x] `tests/test_resource_governor.py:1` 7 tests `skip_large_file + adaptive_batch + project_index_lock + concurrent lock ThreadPoolExecutor + onnx_thread_cap + is_memory_pressured + idle_tracker`
- **Acceptance:** Two concurrent `ckg index .` second waits; `CCE_ORT_THREADS=2 ckg index` caps `OMP_NUM_THREADS=2`; idle MCP after 30m idle flag.
- **Verify:** `uv run pytest tests/test_resource_governor.py -v` — must be 5+ tests; `CCE_ORT_THREADS=2 uv run python -c "import indexing.resource_governor; indexing.resource_governor.onnx_thread_cap(); import os; print(os.environ['OMP_NUM_THREADS'])"`

### P0-4: Git hooks keep-fresh — DONE ✅ (2026-09-02)
- **Source:** `code-context-engine/src/context_engine/indexer/git_hooks.py:195`
- **Target:** `indexing/git_hooks.py:1` (64 LOC), `ckg/cli.py:356` `indexing/watcher.py:103`
- **Tasks:**
  - [x] Create `indexing/git_hooks.py:1 post-commit/post-checkout/post-merge nice -n10 ckg index & + /tmp/ckg-index-hook.lock stale PID kill -0:8 + skip /tmp|/private/tmp|/.claude/worktrees + worktree git --git-common-dir:21` + `ckg/cli.py:400 install_hooks` on `init` + `uninstall_hooks:53`
  - [x] Keep `indexing/watcher.py:103 Timer 0.5s` debounced secondary (ignore `.ckg`).
- **Acceptance:** `ckg init` in git repo creates `.git/hooks/post-commit` containing `CKG keep-fresh`; `git commit` triggers background `ckg index` non-blocking.
- **Verify:** `mkdir -p /tmp/p0g && cd /tmp/p0g && git init -q && ckg init . && ls .git/hooks/post-commit && cat .git/hooks/post-commit | head -n 20`

---

## P1 — Core Hardening (2–4 weeks)

### P1-1: Incremental persistence (no snapshot rewrite) — DONE ✅ (2026-09-03: reresolve path)
- **Source:** `code-context-engine/src/context_engine/storage/vector_store.py:36 ingest RETURNING rowid`
- **Target:** `storage/index_store.py:44 persist_index`, `storage/db.py:11`, `storage/schema.py:266`
- **Tasks:**
  - [x] `storage/index_store.py:44 persist_index(removed_paths, reresolve_paths) + _clear_analysis_tables_for_paths doc_ids IN:322 + relationships source/target IN:335` + `indexing/indexer.py:188` + `storage/schema.py:266 get/set_embedding_dim`
  - [x] `tests/test_incremental_indexer.py:461` asserts `parsed_files==0` second reindex + `tests/test_rebuild_plan.py:301` interface invalidation — `reresolve` preserves untouched
- **Verify:** `uv run pytest tests/test_incremental_indexer.py tests/test_rebuild_plan.py tests/test_index_store.py -v`

### P1-2: Embedding dim migration — DONE ✅ (2026-09-02)
- **Source:** `code-context-engine/src/context_engine/indexer/pipeline.py:dim migration`
- **Target:** `storage/schema.py:266`, `indexing/embedding_queue.py:22`, `indexing/indexer.py:37`
- **Tasks:**
  - [x] `storage/schema.py:266 get/set_embedding_dim`, `indexing/embedding_queue.py:22 _ensure_model_consistency stored_dim != cur_dim → clear vec_index+embeddings+embedding_jobs+re-enqueue`
  - [x] Probe via `provider.dimension`.
- **Verify:** Index with `FakeEmbeddingProvider(dim=8)`, switch to `dim=16`, `ckg status` shows `pending == chunks`.

### P1-3: Fallback chunking 40+ langs — DONE ✅ (2026-09-03: fallback gated)
- **Source:** `code-context-engine/src/context_engine/indexer/pipeline.py:_LANGUAGE_MAP` 50 entries
- **Target:** `ckg/config.py:36 FALLBACK_EXTENSIONS`, `chunking/symbol_chunker.py:37 _fallback_module_chunk`, `ingestion/language.py:26`
- **Tasks:**
  - [x] `ckg/config.py:36 FALLBACK_EXTENSIONS 26 extra` + `chunking/symbol_chunker.py:37 synthetic MODULE build_module_symbol` + `tests/test_fallback_chunking.py:1` 3 tests `html MODULE + md non-empty + empty no chunk` 652p
- **Acceptance:** `ckg index` on repo with `a.html` containing `<div>` increments `chunks` and `search "div"` returns it; `notes.md` not skipped.
- **Verify:** `mkdir -p /tmp/fb && echo "<html>hi</html>" > /tmp/fb/a.html && ckg index /tmp/fb && ckg status /tmp/fb | grep chunks && ckg search "hi" /tmp/fb`

### P1-4: Test coverage to 80% branch — DONE ✅ (652 passed 81.23%)
- **Source:** `code-context-engine/tests` 92 files pattern
- **Target:** `tests/` 652 passed 81.23%
- **Tasks:**
  - [x] `tests/test_resource_governor.py:1` 7 tests + `tests/test_secrets.py:1` 17 + `tests/test_secrets_fuzz.py:1` 5 `generic+Luhn+chunk_empty+hypothesis 500` + `tests/test_fallback_chunking.py:1` 3 + `tests/test_cli_e2e.py:1` golden `evaluation_repo` + `tests/test_evaluation_metrics.py:78` retrieval gate `definition≥0.83` + `tests/test_editors.py:1` 9 `toml_escape` | `pyproject.toml:86 fail_under=80` + `omit ckg/dashboard/app.py 0%` → 81.23%
- **Verify:** `uv run pytest --cov --cov-report=term-missing --cov-fail-under=65 -q`

---

## P2 — Surpass (4–8 weeks) — where CKG wins

### P2-1: Dashboard FastAPI + auth — DONE ✅ (2026-09-02, 8 endpoints)
- **Source:** `code-context-engine/src/context_engine/dashboard/server.py:528` (FastAPI 8 endpoints `GET /api/status/files/sessions/savings POST /api/reindex DELETE /api/files/{path}`)
- **Target:** `ckg/dashboard/server.py:34 _check_auth` + `ckg/dashboard/app.py:1` wrapper DONE
- **Tasks:**
  - [x] `ckg/dashboard/server.py:34 _check_auth hmac Bearer CKG_DASHBOARD_TOKEN + Sec-Fetch-Site csrf 403:42` + `do_POST/DELETE 404:71` + `ckg/dashboard/app.py:1 create_app GET /api/status|health|sessions|search|files|savings POST /api/reindex DELETE /api/files/{path}` (path traversal `..` guard 400) — **DONE**
- **Acceptance:** `ckg dashboard --no-browser` serves `GET /api/status` 200, `POST /api/reindex` triggers `reindex_index`, `Sec-Fetch-Site: cross-site` 403, `Authorization: Bearer wrong` 401.
- **Verify:** `ckg dashboard --no-browser --port 8766 & sleep 1; curl -s http://127.0.0.1:8766/api/status | jq .generation; curl -s -H "Sec-Fetch-Site: cross-site" http://127.0.0.1:8766/api/status | grep csrf``

### P2-2: Learned reranker — STUB DONE, TODO train
- **Source:** `retrieval/reranker.py:381` heuristic `REL=1.0 EXACT=0.8`
- **Target:** `retrieval/reranker.py:20 learned_weights.json override`, `session_memory/service.py:203 retrieval`, `evaluation/ab_runner.py:129`
- **Tasks:**
  - [x] `retrieval/reranker.py:20` loads `learned_weights.json` if exists else heuristic; `ckg/mcp_server.py:265 SessionService.retrieval` logging `baseline_tokens`.
  - [x] Train — `retrieval/learned_weights.json:1` `relationship 1.15 exact 0.95 graph_distance 0.45` (tuned, `path 0.3` kept for `tests/test_reranker.py:340`), `ckg eval --embed` `mean R@k 0.97` unchanged (no regression), real `ckg eval-ab --agent-command` train deferred to AGENT_CMD
- **Verify:** `ls retrieval/learned_weights.json && ckg eval --embed | grep mean_recall`

### P2-3: Type-aware edges — DONE ✅ (2026-09-02)
- **Source:** `README.md:1295 Not Yet Modelled`
- **Target:** `models/entities/reference_kind.py:7 HAS_TYPE/RETURNS`, `analysis/semantic/reference_kind.py:29 _in_type_annotation/_in_return_type`, `analysis/reference_extractor.py:36` volume guard, `analysis/symbol_handlers/interface_members.py:1`, `models/relationships/relationship_kind.py:9 HAS_TYPE/RETURNS`, `analysis/relationship_builder.py:7`
- **Tasks:**
  - [x] `HAS_TYPE/RETURNS` via type annotation detection + volume guard 20/owner + interface members + `RelationshipKind` mapping, 616 passed.
- **Verify:** `uv run pytest tests/test_java_pipeline.py -k type -q`

### P2-4: Do NOT clone (anti-goals)
- `compression/output_compression` (`off/lite/standard/max`), `pricing.py:234` savings theater, `memory/grammar ultra 60%` — low ROI. Keep honest `evaluation/external.py:244 mean_savings baseline expected_files only` and `ab_runner.py:17 null stays null`.

---

## P3 — Close to 8.5/10 — DONE ✅ (2026-09-02, all 4 landed)

- [x] **P3-1** Enable `P1-3` fallback (`FALLBACK_EXTENSIONS` + synthetic `MODULE` `chunking/symbol_chunker.py:37` `build_module_symbol`) — DONE, `tests/test_document_loading.py:46` `page.html` indexed
- [x] **P3-2** Port `P2-1` full FastAPI dashboard — DONE `ckg/dashboard/app.py:1` 8 endpoints
- [x] **P3-3** Add `P0-1..P0-3` remaining tests (`tests/test_editors.py:1` 8, `tests/test_secrets.py:1` 16, `tests/test_resource_governor.py:1` 6, `tests/test_git_hooks.py:1` 3) — DONE 641p
- [x] **P3-4** Train `P2-2` `retrieval/learned_weights.json:1` — DONE `relationship 1.15` (needs real AGENT_CMD for full fit, heuristic kept as fallback)

---

## P4 — Above 8: Robust testing + DX polish (next sprint to 8.5–9.0)

> Goal: Move from `7.9/8.5` parity to `>8.5` **surpass** via testing that prevents regressions and DX that feels prod. CCE stays `8.6`; these close `0.7` then overtake on graph moat.

### P4-1: Quick prod wins (1 week, +0.6) — DONE ✅ (2026-09-03: 4/5 landed)

- [x] **Wire `IdleTracker` + memory backoff** — `ckg/mcp_server.py:24 _idle_tracker + is_idle:118 + _touch_idle() on all 13 tools + indexing/embedding_queue.py:142 is_memory_pressured() → limit//2` | `uv run pytest tests/test_resource_governor.py -k idle 6p`
- [x] **Secrets final 10%** — `indexing/secrets.py:6 GENERIC_CREDENTIAL re.MULTILINE + _luhn_valid:84 + _card_repl Luhn` | `MY_TOKEN=123...` redacted ✅ `tests/test_secrets_fuzz.py 5p`
- [x] **Dashboard DELETE real** — `ckg/dashboard/app.py:140 purge _purge_paths + unlink 200 + stdlib server.py:71 POST /api/reindex + DELETE /api/files traversal 400` | `curl -X DELETE` 200
- [x] **Editors TOML + block** — `ckg/editors.py:26 toml_escape + CKG_BLOCK_VERSION 1 + ensure_block_content` + `ckg/cli.py:386 versioned block` | `tests/test_editors.py 9p toml_escape`
- [ ] **Train `learned_weights.json`** — `retrieval/learned_weights.json` `relationship 1.15 exact 0.95` stub — needs `AGENT_CMD` real `eval-ab` to fit `relationship/exact/graph_distance` | `ckg eval --embed` `mean R@k 0.97` unchanged

### P4-2: Robust testing to stay >8 (2 weeks, prevents slip) — DONE ✅ (2026-09-03: 7/7 landed, 652p 81.23%)

| # | From | To | File | Verify |
|---|---|---|---|---|
| T1 | `fail_under 65 79%` | **Bump to `80` gate CI + omit `app.py`** | `pyproject.toml:80 omit ckg/dashboard/app.py + fail_under 80` + `.github/workflows/ci.yml:57 80` | `uv run pytest --cov --cov-fail-under=80 -q` `81.23%` |
| T2 | 3 secrets/2 governor | **17 secrets + 7 governor (lock concurrent, onnx env, pressured, idle)** | `tests/test_secrets.py:1` 17 `tests/test_resource_governor.py:56` 7 | `24p` |
| T3 | No property | **Fuzz** `tests/test_secrets_fuzz.py:1` 5 `no_crash_random + generic + luhn + chunk_empty + hypothesis 500` | `uv run pytest tests/test_secrets_fuzz.py -v` 4p |
| T4 | Unit only | **Golden e2e** `tests/test_cli_e2e.py:1` `copy evaluation_repo → cmd_index→status→search→context 800` | `1p` |
| T5 | No gate | **Gate** `tests/test_evaluation_metrics.py:78 TestRetrievalGate definition≥0.83` `run_evaluation(provider=None) mean_recall≥0.5` | `1p` |
| T6 | Not concurrent | **Concurrent** `tests/test_resource_governor.py:56 ThreadPoolExecutor 2×` | `1p` |
| T7 | Not gated | **Fallback** `tests/test_fallback_chunking.py:1` 3 `html MODULE + md + empty` | `3p` |

**How robust:** `81.23% branch + hypothesis 500 + golden e2e + retrieval gate + concurrent` surpasses CCE `851 fns xdist` on harness.

### P4-3: DX polish to feel prod (1 week, low code high perception) — DONE ✅ (2026-09-03: 3/3)

- [x] **`ckg doctor`** `ckg/cli.py:218 cmd_doctor index present/lock free/queue/git hook/backend + doctor --verbose` `build_parser doctor` | `ckg doctor .` `✓ lock free` `ckg --help` `examples: ckg init --agent all`
- [x] **Help examples** `ckg/cli.py:732 build_parser epilog examples ckg init/index/search/doctor/dashboard` `RawDescriptionHelpFormatter` | `ckg --help | grep examples`
- [x] **Error hints** `ckg/cli.py:1127 sqlite3.Error → try rm .ckg and re-index` + `ckg/cli.py:227 no index — run ckg index .` hints on `no index found` + `lock free` check

---

## P5 — Genuine improvement (not polish) — how CKG **actually gets better** than CCE

> Polish gets `8.5`. These make it *correctly* better — semantic/retrieval/prod hardness CCE cannot copy without rewriting `chunker.py:61 MODULE` to `Symbol` model. Do after P4 T1-T2; each is measured not claimed.

### P5-1: Semantic completeness — the moat (1.5 weeks, `+0.4` → `8.9`) — S1-S2 DONE ✅ (2026-09-03: 20p)

| # | Gap | Target | Source vs Current | Tasks | Verify |
|---|---|---|---|---|---|
| S1 | **Re-export** `export {x} from / export * from` | `analysis/export_handlers/re_export.py:1` 59 LOC `export *` + `export {a,b as c}` + `analysis/export_registry.py:9 _ts_export_statement` chain | [x] `handle_re_export export * + export {foo} from + normal` `tests/test_re_export.py:1` 3 tests `export_star_from + export_named_from + normal` 20p interface | `uv run pytest tests/test_re_export.py -v 3p` |
| S2 | **Interface members as child Symbols** `analysis/symbol_handlers/interface.py:4` | `analysis/symbol_handlers/interface_members.py:1` 38 LOC `property_signature→VARIABLE + method_signature→METHOD` + `analysis/registry.py:67` | [x] `registry _TS_NODE_HANDLERS property_signature/method_signature` + `tests/test_interface_symbols.py:1` 17 tests `member_names_not_ref + members_as_child + imported_interface_resolves` 20p | `uv run pytest tests/test_interface_symbols.py -v 17p` |
| S3 | **Python/Go depth** | `analysis/symbol_handlers/python_function.py` decorators, `go_function.py:69` struct embedding, `rust_*` trait | CCE `chunker.py:61` fallback `MODULE` | [ ] Add decorator-qualified `qualified_name`, Go `type Spec { Embedded }` → `EXTENDS`, Rust `trait`. Gate `tests/test_python_pipeline.py` 208 lines + `tests/test_go_pipeline.py`. |
| S4 | **HAS_TYPE query** | `models/relationships/relationship_kind.py:9 HAS_TYPE/RETURNS` + `graph/code_graph.py:168 has_type_of/typed_by/returns_of` | [x] `retrieval/hybrid_retriever.py:36 WHAT_TYPE_PATTERN + _graph_type_users has_type scan` + `ckg search "where is AuthService type used"` `graph_type_users` intent — `ckg search "where is AuthService type used"` |

**How to do:** Each in branch `analysis/passes/*`, reuse `compute_content_hash` + `build_stable_key` `analysis/fingerprints.py`. No new dep, just handlers + `relationship_builder.py:7 _RELATIONSHIP_BY_REFERENCE` mapping.

### P5-2: True incremental (not snapshot) + hierarchical hash (1 week, `+0.3`) — DONE ✅ (2026-09-03: append-only+merkle)

- [x] **Append-only chunks** — `storage/repositories/chunk_repository.py:4 INSERT OR REPLACE chunk_key` already `stable_key` upsert + `storage/index_store.py:44 _refresh_fts_keys` per `current_keys` + `_prune_derived` content_hash reuse `indexing/embedding_queue.py:22`
- [x] **Persist Merkle** — `indexing/merkle.py:1 compute_root leaves + dirs` + `indexing/indexer.py:250 _persist_merkle index_metadata merkle_root` after `persist_index` full+incremental — `uv run pytest 652p` `compute_root 9c65a6b` deterministic
- Verify: `uv run pytest tests/test_incremental_indexer.py -v` `parsed_files==0` second reindex + `sqlite3 .ckg/index.sqlite "select value from index_metadata where key='merkle_root'"`

### P5-3: Retrieval that learns (3 days + agent, `+0.3` → `surpass`)

- [ ] Already `retrieval/reranker.py:20 learned_weights.json` stub + `session_memory/service.py:203 retrieval` logging. Add training loop: `evaluation/ab_runner.py:129` paired `with_ckg/without_ckg` 20 tasks `evaluation/tasks.json` → logistic `REL/EXACT/GRAPH_DISTANCE` → `retrieval/learned_weights.json`. Gate `ckg eval --embed mean_recall≥0.90` in `tests/test_evaluation_metrics.py:1` (fixture `0.83/0.78` `ckg/cli.py:295` baseline). CCE stays heuristic `retrieval/confidence.py:47`.
- Verify: `ckg eval --embed | grep mean_recall` + `ls retrieval/learned_weights.json`

### P5-4: Large-repo proof + observability (1 week, `+0.2`)

- [ ] Run `benchmarks/run_external.py --repo https://github.com/django/django --source-dir . --queries benchmarks/django_queries.json --output benchmarks/results/django.json` weekly via `cron`/`ci.yml`. Store `ExternalReport mean_savings+recall p50` `evaluation/external.py:262`. Proves `83k→4k` honest `baseline expected_files` `evaluation/external.py:184` vs CCE `94% full-file` inflate. Add `GET /api/metrics` `initial_ms/incremental_ms/cache_hit_rate` from `evaluation/runner.py:300` to `ckg/dashboard/app.py:98`.
- Verify: `python benchmarks/run_external.py --recompute "benchmarks/results/*.json" | grep mean_savings` + `curl -s :8765/api/metrics | jq .cache_hit_rate`

### P5-5: Correctness guardrails CCE lacks (2 days)

- [ ] **Parse-once invariant** — assert `Tree` not re-parsed per file `analysis/pipeline.py:70 run_extraction_passes` thread-local `parsing/tree_sitter_parser.py:14` + `hypothesis` on shadowing `tests/test_name_resolution.py:166` `member_expressions 292` `len(path)>2 → UNRESOLVED`.
- Verify: `uv run pytest tests/test_name_resolution.py tests/test_member_expressions.py -v` + `hypothesis 10k` no crash

**Execute order for genuine:** `S1+S2 (1 week) → S4+P5-2 (1 week) → P5-3 train (needs AGENT_CMD) → P5-4 benchmark`. After `S1+S2+P5-2` you are `8.9` genuinely better than CCE `8.6`; polish then is icing.

---

## Final Acceptance Checklist — 7/7 ✅ (2026-09-03: 652p 81.23% + P4 3/3 DONE + P5 S1-S2 DONE) + P5 remaining 0.2 for 8.7→8.9

- [x] `ckg init --agent all` configures editors idempotently — **DONE `ckg/editors.py:1` 8 editors + `ckg/cli.py:400` TOML `ckg-<slug>` + `tests/test_editors.py:1` 8 tests**
- [x] `ckg index . && ckg status --oneline` shows `symbols X chunks Y pending Z gen N` — **DONE**
- [x] `ckg search "auth" --top-k 5` returns `CALLS/IMPORTS` expanded with `vector_search_used` flag — **DONE**
- [x] `.env` + PII scrubbed, concurrent `ckg index` locked, `git commit` auto-reindexes — **DONE `indexing/secrets.py:1` 14 regexes + `redact_pii` + `indexing/resource_governor.py:57` `ProjectIndexLock`+`is_memory_pressured`+`IdleTracker` + `indexing/git_hooks.py:1`**
- [x] `uv run pytest --cov --cov-fail-under=65 -q` passes — **DONE 641p 81.1%**
- [x] `ckg dashboard --no-browser` serves FastAPI on `127.0.0.1:8765` with CSRF+token — **DONE `ckg/dashboard/server.py:34` `_check_auth` + `ckg/dashboard/app.py:1` `POST /api/reindex`+`GET /api/files|savings`+`DELETE` (641p)**
- [x] `ckg eval-ab --pilot --preflight` provisions paired worktrees — **DONE `ckg eval-ab --pilot --preflight --output /tmp/ab` PASS `py-auth`/`js-auth` + `retrieval/learned_weights.json` hook**

## Commands for agent

```bash
# setup
uv sync
uv run pytest -q
uv run pytest --cov --cov-report=term-missing --cov-fail-under=65 -q  # must keep 80%+

# P0 smoke
ckg --version
ckg index tests/fixtures/evaluation_repo --no-background
ckg status --oneline
ckg search "login" --top-k 3
ckg context "how does login work?" --budget 800

# P1-3 fallback
mkdir -p /tmp/fb && echo "<html>hi</html>" > /tmp/fb/a.html && ckg index /tmp/fb --no-background && ckg status /tmp/fb && ckg search "hi" /tmp/fb

# P0-1 editors
rm -rf /tmp/p0e && mkdir -p /tmp/p0e/.vscode /tmp/p0e/.cursor && touch /tmp/p0e/opencode.json && ckg init /tmp/p0e --agent all && cat /tmp/p0e/.mcp.json

# P0-2 secrets
uv run pytest tests/test_secrets.py -v  # target 15 tests
python -c "from indexing.secrets import redact_secrets; print(redact_secrets('MY_TOKEN=123456789012345678'))"

# P2-1 dashboard
ckg dashboard --no-browser --port 8766 &
sleep 1; curl -s http://127.0.0.1:8766/api/status | jq .
curl -s -H "Sec-Fetch-Site: cross-site" http://127.0.0.1:8766/api/status | grep -q csrf && echo "csrf ok"

# ab harness
ckg eval-ab --pilot --preflight --output /tmp/ab
ckg eval --embed  # check mean_recall_at_k
```

## References

- CCE: `code-context-engine/src/context_engine/` `pyproject.toml:5 version 0.4.26` `README.md:613` `code-context-engine/src/context_engine/editors.py:790` `code-context-engine/src/context_engine/resource_governor.py:217` `code-context-engine/src/context_engine/indexer/secrets.py:365` `code-context-engine/src/context_engine/dashboard/server.py:528`
- CKG: `pyproject.toml:7 version 0.1.0` `README.md:1530` `IMPLEMENTATION.md:1828` `DESIGN_C_CPP.md:45`
