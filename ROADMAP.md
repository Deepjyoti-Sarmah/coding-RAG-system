# symbolgraph Roadmap — Agent Execution Plan

> Goal: make symbolgraph (`0.1.0`) production-ready and keep it honest. Order: Correctness → Incremental → Retrieval → Ops.

> **AUDIT 2026-09-04 (publish readiness):** `uv run pytest -q --cov` → `657 passed, 0 skipped, 80.53% branch`. `uv build` green. `uv run ruff check .` → `All checks passed!`. Engine work (P0–P5) is done; packaging (`P6`) is the only thing between symbolgraph and a published tool.

> **AUDIT 2026-09-05:** `uv run pytest -q --cov` → `670 passed, 80.61% branch`. `uv run ruff check .` → `All checks passed!`. `P5-4` (external benchmark + token/$ savings) is done — see its entry below. `P5-3` reranker weights are correctly labeled tuned, not learned. `P5-5` parse-once + shadowing invariants are pinned by test. Remaining open work is `P5-4a`'s own follow-on (original queries for more repos) and `P6-8`'s tag push, both explicitly deferred pending your go-ahead, not oversights.

> **AUDIT 2026-09-05 (cont'd):** `S3` done — `677 passed, 80.68% branch`, `ruff` clean. Only `4` checkboxes remain in the whole file, and all four need something only you can provide: a real agent to run the reranker training loop (×2 listings, same task), the `v0.1.0` tag push, and a manual-versioning note that isn't really a task. There is no more unblocked engine work left to pick up.

## How to use

- Work phase-by-phase. Do not skip P0.
- Each task lists a `Target` with `file_path:line`.
- After each task: run its `Verify` command and update the checkbox.
- Overall verify: `uv run pytest -q && uv run pytest --cov --cov-fail-under=80` and `sg eval --embed` on `tests/fixtures/evaluation_repo`.
- Current truth: P0–P5 landed. **Start at `P6`.** Don't trust prior `DONE ✅` — run verify.

---

## P0 — Prod Killers (1–2 weeks) — SHIP BLOCKERS

### P0-1: Multi-editor `sg init` matrix — DONE ✅ (2026-09-02)
- **Why:** One-command setup across every editor an agent might run in, not just `.mcp.json`.
- **Target:** `symbolgraph/editors.py:1`, `symbolgraph/cli.py:356 _ensure_mcp_entry`, `symbolgraph/cli.py:652 build_parser`
- **Tasks:**
  - [x] Create `symbolgraph/editors.py:1` 8 editors `claude/cursor/vscode/opencode/gemini/copilot/pi/codex` + `project_storage_slug:21` `atomic_write_text mkstemp+fsync+replace:26` + `detect_editors:41` + `~/.codex/config.toml` TOML `[mcp_servers.sg-<slug>]` via `symbolgraph/cli.py:400`
  - [x] Extend `symbolgraph/cli.py:652 build_parser` `init --agent {auto,claude,cursor,vscode,codex,copilot,pi,opencode,gemini,all} + --plugin` + `uninstall` + `install_hooks:400` + TOML handling `symbolgraph/cli.py:400` `path.suffix==".toml"` append
  - [x] Add `tests/test_editors.py:1` 8 tests idempotent+corruption+auto+all (641 passed)
- **Acceptance:** `sg init --agent all` in repo with `.vscode`+`.cursor`+`opencode.json` creates 4 configs; second run `already configured`; `~/.codex/config.toml` contains `[mcp_servers.sg-<slug>]` with `command="sg-mcp"`.
- **Verify:** `rm -rf /tmp/p0e && mkdir -p /tmp/p0e/.vscode /tmp/p0e/.cursor && touch /tmp/p0e/opencode.json && sg init /tmp/p0e --agent all && cat /tmp/p0e/.mcp.json && cat /tmp/p0e/.vscode/mcp.json && cat ~/.codex/config.toml | grep -A2 sg-`

### P0-2: Secrets + PII redaction — DONE ✅ (2026-09-03: GENERIC+Luhn)
- **Target:** `indexing/secrets.py:1` (108 LOC), `ingestion/loader.py:89`, `session_memory/service.py:24`
- **Tasks:**
  - [x] `indexing/secrets.py:1` 15 regexes `14 + GENERIC_CREDENTIAL export? \w*(password|secret|token|api_key) 16+` `re.MULTILINE` + `_luhn_valid:84` + `_card_repl Luhn` + placeholder `my-/your-`
  - [x] `ingestion/loader.py:89 is_secret_filename` + `session_memory/service.py:24 _bounded` `redact_pii(redact_secrets())`
  - [x] `tests/test_secrets.py:1` 17 tests + `tests/test_secrets_fuzz.py:1` 5 tests `generic_credential + luhn_valid 4111 Valid` — `MY_TOKEN=123...` redacted ✅
- **Acceptance:** `.env` with `AKIA...` + `sk-ant-...` skipped; `GENERIC_CREDENTIAL` `MY_TOKEN=1234567890123456` redacted not placeholder; PII email scrubbed in `record_decision`.
- **Verify:** `uv run pytest tests/test_secrets.py -v` — must be 15+ tests; `python -c "from indexing.secrets import redact_secrets; print(redact_secrets('MY_TOKEN=123456789012345678'))"` contains `[REDACTED]`

### P0-3: Resource governor + file lock — DONE ✅ (2026-09-03: IdleTracker wired)
- **Target:** `indexing/resource_governor.py:1` (108 LOC), `symbolgraph/mcp_server.py:335`, `indexing/embedding_queue.py:142` (backoff)
- **Tasks:**
  - [x] `indexing/resource_governor.py:1 onnx_thread_cap explicit= env[k]= + IdleTracker 30m:99` + `symbolgraph/mcp_server.py:24 _idle_tracker + is_idle:118 + _touch_idle() on all 13 tools index_repository/search/context/definition/callers/callees/session_* + embedding_queue.py:142 is_memory_pressured() → limit//2`
  - [x] `tests/test_resource_governor.py:1` 7 tests `skip_large_file + adaptive_batch + project_index_lock + concurrent lock ThreadPoolExecutor + onnx_thread_cap + is_memory_pressured + idle_tracker`
- **Acceptance:** Two concurrent `sg index .` second waits; `SG_ORT_THREADS=2 sg index` caps `OMP_NUM_THREADS=2`; idle MCP after 30m idle flag.
- **Verify:** `uv run pytest tests/test_resource_governor.py -v` — must be 5+ tests; `SG_ORT_THREADS=2 uv run python -c "import indexing.resource_governor; indexing.resource_governor.onnx_thread_cap(); import os; print(os.environ['OMP_NUM_THREADS'])"`

### P0-4: Git hooks keep-fresh — DONE ✅ (2026-09-02)
- **Target:** `indexing/git_hooks.py:1` (64 LOC), `symbolgraph/cli.py:356` `indexing/watcher.py:103`
- **Tasks:**
  - [x] Create `indexing/git_hooks.py:1 post-commit/post-checkout/post-merge nice -n10 sg index & + /tmp/sg-index-hook.lock stale PID kill -0:8 + skip /tmp|/private/tmp|/.claude/worktrees + worktree git --git-common-dir:21` + `symbolgraph/cli.py:400 install_hooks` on `init` + `uninstall_hooks:53`
  - [x] Keep `indexing/watcher.py:103 Timer 0.5s` debounced secondary (ignore `.sg`).
- **Acceptance:** `sg init` in git repo creates `.git/hooks/post-commit` containing `symbolgraph keep-fresh`; `git commit` triggers background `sg index` non-blocking.
- **Verify:** `mkdir -p /tmp/p0g && cd /tmp/p0g && git init -q && sg init . && ls .git/hooks/post-commit && cat .git/hooks/post-commit | head -n 20`

---

## P1 — Core Hardening (2–4 weeks)

### P1-1: Incremental persistence (no snapshot rewrite) — DONE ✅ (2026-09-03: reresolve path)
- **Target:** `storage/index_store.py:44 persist_index`, `storage/db.py:11`, `storage/schema.py:266`
- **Tasks:**
  - [x] `storage/index_store.py:44 persist_index(removed_paths, reresolve_paths) + _clear_analysis_tables_for_paths doc_ids IN:322 + relationships source/target IN:335` + `indexing/indexer.py:188` + `storage/schema.py:266 get/set_embedding_dim`
  - [x] `tests/test_incremental_indexer.py:461` asserts `parsed_files==0` second reindex + `tests/test_rebuild_plan.py:301` interface invalidation — `reresolve` preserves untouched
- **Verify:** `uv run pytest tests/test_incremental_indexer.py tests/test_rebuild_plan.py tests/test_index_store.py -v`

### P1-2: Embedding dim migration — DONE ✅ (2026-09-02)
- **Target:** `storage/schema.py:266`, `indexing/embedding_queue.py:22`, `indexing/indexer.py:37`
- **Tasks:**
  - [x] `storage/schema.py:266 get/set_embedding_dim`, `indexing/embedding_queue.py:22 _ensure_model_consistency stored_dim != cur_dim → clear vec_index+embeddings+embedding_jobs+re-enqueue`
  - [x] Probe via `provider.dimension`.
- **Verify:** Index with `FakeEmbeddingProvider(dim=8)`, switch to `dim=16`, `sg status` shows `pending == chunks`.

### P1-3: Fallback chunking, 40+ languages — DONE ✅ (2026-09-03: fallback gated)
- **Target:** `symbolgraph/config.py:36 FALLBACK_EXTENSIONS`, `chunking/symbol_chunker.py:37 _fallback_module_chunk`, `ingestion/language.py:26`
- **Tasks:**
  - [x] `symbolgraph/config.py:36 FALLBACK_EXTENSIONS 26 extra` + `chunking/symbol_chunker.py:37 synthetic MODULE build_module_symbol` + `tests/test_fallback_chunking.py:1` 3 tests `html MODULE + md non-empty + empty no chunk` 652p
- **Acceptance:** `sg index` on repo with `a.html` containing `<div>` increments `chunks` and `search "div"` returns it; `notes.md` not skipped.
- **Verify:** `mkdir -p /tmp/fb && echo "<html>hi</html>" > /tmp/fb/a.html && sg index /tmp/fb && sg status /tmp/fb | grep chunks && sg search "hi" /tmp/fb`

### P1-4: Test coverage to 80% branch — DONE ✅ (652 passed 81.23%, since then 657/80.53%)
- **Target:** `tests/`
- **Tasks:**
  - [x] `tests/test_resource_governor.py:1` 7 tests + `tests/test_secrets.py:1` 17 + `tests/test_secrets_fuzz.py:1` 5 `generic+Luhn+chunk_empty+hypothesis 500` + `tests/test_fallback_chunking.py:1` 3 + `tests/test_cli_e2e.py:1` golden `evaluation_repo` + `tests/test_evaluation_metrics.py:78` retrieval gate `definition≥0.83` + `tests/test_editors.py:1` 9 `toml_escape` | `pyproject.toml fail_under=80` + `omit symbolgraph/dashboard/app.py 0%`
- **Verify:** `uv run pytest --cov --cov-report=term-missing --cov-fail-under=80 -q`

---

## P2 — Retrieval + ops depth (4–8 weeks)

### P2-1: Dashboard FastAPI + auth — DONE ✅ (2026-09-02, 8 endpoints)
- **Target:** `symbolgraph/dashboard/server.py:34 _check_auth` + `symbolgraph/dashboard/app.py:1` wrapper
- **Tasks:**
  - [x] `symbolgraph/dashboard/server.py:34 _check_auth hmac Bearer SG_DASHBOARD_TOKEN + Sec-Fetch-Site csrf 403:42` + `do_POST/DELETE 404:71` + `symbolgraph/dashboard/app.py:1 create_app GET /api/status|health|sessions|search|files|savings POST /api/reindex DELETE /api/files/{path}` (path traversal `..` guard 400)
- **Acceptance:** `sg dashboard --no-browser` serves `GET /api/status` 200, `POST /api/reindex` triggers `reindex_index`, `Sec-Fetch-Site: cross-site` 403, `Authorization: Bearer wrong` 401.
- **Verify:** `sg dashboard --no-browser --port 8766 & sleep 1; curl -s http://127.0.0.1:8766/api/status | jq .generation; curl -s -H "Sec-Fetch-Site: cross-site" http://127.0.0.1:8766/api/status | grep csrf`

### P2-2: Learned reranker — STUB DONE, TODO train
- **Target:** `retrieval/reranker.py:20 learned_weights.json override`, `session_memory/service.py:203 retrieval`, `evaluation/ab_runner.py:129`
- **Tasks:**
  - [x] `retrieval/reranker.py:20` loads `learned_weights.json` if exists else heuristic; `symbolgraph/mcp_server.py:265 SessionService.retrieval` logging `baseline_tokens`.
  - [x] Tuned — `retrieval/learned_weights.json:1` `relationship 1.15 exact 0.95 graph_distance 0.45` (grid search on `evaluation_repo`, `path 0.3` kept for `tests/test_reranker.py:340`), `sg eval --embed` `mean R@k 0.97` unchanged (no regression). Real `sg eval-ab --agent-command` training against external tasks deferred — see the honesty note at the end of `P5-3`.
- **Verify:** `ls retrieval/learned_weights.json && sg eval --embed | grep mean_recall`

### P2-3: Type-aware edges — DONE ✅ (2026-09-02)
- **Target:** `models/entities/reference_kind.py:7 HAS_TYPE/RETURNS`, `analysis/semantic/reference_kind.py:29 _in_type_annotation/_in_return_type`, `analysis/reference_extractor.py:36` volume guard, `analysis/symbol_handlers/interface_members.py:1`, `models/relationships/relationship_kind.py:9 HAS_TYPE/RETURNS`, `analysis/relationship_builder.py:7`
- **Tasks:**
  - [x] `HAS_TYPE/RETURNS` via type annotation detection + volume guard 20/owner + interface members + `RelationshipKind` mapping, 616 passed.
- **Verify:** `uv run pytest tests/test_java_pipeline.py -k type -q`

### P2-4: Deliberately not building
- `compression/output_compression` (`off/lite/standard/max`), a "savings" summary that claims a number the harness can't verify, an aggressive extractive-memory-compression mode — low ROI, and the second one specifically contradicts this project's own honesty standard. Keep `evaluation/external.py:244 mean_savings baseline expected_files only` and `ab_runner.py:17 null stays null`.

---

## P3 — Close remaining gaps — DONE ✅ (2026-09-02, all 4 landed)

- [x] **P3-1** Enable `P1-3` fallback (`FALLBACK_EXTENSIONS` + synthetic `MODULE` `chunking/symbol_chunker.py:37` `build_module_symbol`) — DONE, `tests/test_document_loading.py:46` `page.html` indexed
- [x] **P3-2** Port `P2-1` full FastAPI dashboard — DONE `symbolgraph/dashboard/app.py:1` 8 endpoints
- [x] **P3-3** Add `P0-1..P0-3` remaining tests (`tests/test_editors.py:1` 8, `tests/test_secrets.py:1` 16, `tests/test_resource_governor.py:1` 6, `tests/test_git_hooks.py:1` 3) — DONE 641p
- [x] **P3-4** Tune `P2-2` `retrieval/learned_weights.json:1` — DONE `relationship 1.15` (grid search fixture-based; heuristic kept as fallback)

---

## P4 — Robust testing + DX polish

> Goal: testing that prevents regressions and DX that feels production-ready.

### P4-1: Quick prod wins — DONE ✅ (2026-09-03: 4/5 landed)

- [x] **Wire `IdleTracker` + memory backoff** — `symbolgraph/mcp_server.py:24 _idle_tracker + is_idle:118 + _touch_idle() on all 13 tools + indexing/embedding_queue.py:142 is_memory_pressured() → limit//2` | `uv run pytest tests/test_resource_governor.py -k idle 6p`
- [x] **Secrets final 10%** — `indexing/secrets.py:6 GENERIC_CREDENTIAL re.MULTILINE + _luhn_valid:84 + _card_repl Luhn` | `MY_TOKEN=123...` redacted ✅ `tests/test_secrets_fuzz.py 5p`
- [x] **Dashboard DELETE real** — `symbolgraph/dashboard/app.py:140 purge _purge_paths + unlink 200 + stdlib server.py:71 POST /api/reindex + DELETE /api/files traversal 400` | `curl -X DELETE` 200
- [x] **Editors TOML + block** — `symbolgraph/editors.py:26 toml_escape + SG_BLOCK_VERSION 1 + ensure_block_content` + `symbolgraph/cli.py:386 versioned block` | `tests/test_editors.py 9p toml_escape`
- [ ] **Train `learned_weights.json`** — `retrieval/learned_weights.json` `relationship 1.15 exact 0.95` stub — needs a real `AGENT_CMD` `eval-ab` run to fit `relationship/exact/graph_distance` on real tasks | `sg eval --embed` `mean R@k 0.97` unchanged

### P4-2: Robust testing — DONE ✅ (2026-09-03: 7/7 landed, 652p 81.23%)

| # | From | To | File | Verify |
|---|---|---|---|---|
| T1 | `fail_under 65 79%` | **Bump to `80` gate CI + omit `app.py`** | `pyproject.toml omit symbolgraph/dashboard/app.py + fail_under 80` + `.github/workflows/ci.yml:57 80` | `uv run pytest --cov --cov-fail-under=80 -q` |
| T2 | 3 secrets/2 governor | **17 secrets + 7 governor (lock concurrent, onnx env, pressured, idle)** | `tests/test_secrets.py:1` 17 `tests/test_resource_governor.py:56` 7 | `24p` |
| T3 | No property | **Fuzz** `tests/test_secrets_fuzz.py:1` 5 `no_crash_random + generic + luhn + chunk_empty + hypothesis 500` | `uv run pytest tests/test_secrets_fuzz.py -v` 4p |
| T4 | Unit only | **Golden e2e** `tests/test_cli_e2e.py:1` `copy evaluation_repo → cmd_index→status→search→context 800` | `1p` |
| T5 | No gate | **Gate** `tests/test_evaluation_metrics.py:78 TestRetrievalGate definition≥0.83` `run_evaluation(provider=None) mean_recall≥0.5` | `1p` |
| T6 | Not concurrent | **Concurrent** `tests/test_resource_governor.py:56 ThreadPoolExecutor 2×` | `1p` |
| T7 | Not gated | **Fallback** `tests/test_fallback_chunking.py:1` 3 `html MODULE + md + empty` | `3p` |

**How robust:** `80%+ branch + hypothesis 500 + golden e2e + retrieval gate + concurrent` on this test harness.

### P4-3: DX polish — DONE ✅ (2026-09-03: 3/3)

- [x] **`sg doctor`** `symbolgraph/cli.py:218 cmd_doctor index present/lock free/queue/git hook/backend + doctor --verbose` `build_parser doctor` | `sg doctor .` `✓ lock free` `sg --help` `examples: sg init --agent all`
- [x] **Help examples** `symbolgraph/cli.py:732 build_parser epilog examples sg init/index/search/doctor/dashboard` `RawDescriptionHelpFormatter` | `sg --help | grep examples`
- [x] **Error hints** `symbolgraph/cli.py:1127 sqlite3.Error → try rm .sg and re-index` + `symbolgraph/cli.py:227 no index — run sg index .` hints on `no index found` + `lock free` check

---

## P5 — Genuine improvement (not polish)

> Semantic/retrieval/prod hardness that a chunk-based indexer can't get for free without rewriting its chunker to a real symbol model. Do after P4 T1–T2; each is measured, not claimed.

### P5-1: Semantic completeness — S1–S2 DONE ✅ (2026-09-03: 20p)

| # | Gap | Target | Tasks | Verify |
|---|---|---|---|---|
| S1 | **Re-export** `export {x} from / export * from` | `analysis/export_handlers/re_export.py:1` 59 LOC `export *` + `export {a,b as c}` + `analysis/export_registry.py:9 _ts_export_statement` chain | [x] `handle_re_export export * + export {foo} from + normal` `tests/test_re_export.py:1` 3 tests `export_star_from + export_named_from + normal` 20p interface | `uv run pytest tests/test_re_export.py -v 3p` |
| S2 | **Interface members as child Symbols** `analysis/symbol_handlers/interface.py:4` | `analysis/symbol_handlers/interface_members.py:1` 38 LOC `property_signature→VARIABLE + method_signature→METHOD` + `analysis/registry.py:67` | [x] `registry _TS_NODE_HANDLERS property_signature/method_signature` + `tests/test_interface_symbols.py:1` 17 tests `member_names_not_ref + members_as_child + imported_interface_resolves` 20p | `uv run pytest tests/test_interface_symbols.py -v 17p` |
| S3 | **Python/Go/Rust depth** — DONE ✅ (2026-09-05) | `analysis/symbol_handlers/python_function.py`, `analysis/semantic/reference_kind.py`, `analysis/passes/impl_pass.py` | [x] Python: `Symbol.decorators: tuple[str, ...]` — a new field, additive only (`qualified_name`/`stable_key` never depend on it, tested directly), captured from `decorated_definition` siblings, round-tripped through `storage/repositories/symbol_repository.py` (new `decorators_json` column, `SCHEMA_VERSION` 5→6, drop-and-rebuild per this project's own migration policy). Rejected the ROADMAP's original wording ("decorator-qualified `qualified_name`") — mutating `qualified_name` risks breaking call resolution silently; a schema field is the safe version of the same idea. Go: `field_declaration` with no `name` field (`Base` vs `b Base`) → `EXTENDS`, via `in_extends_clause` — the existing heritage-clause pipeline, not a new one; handles plain, pointer (`*Base`), and qualified (`pkg.Base`) embeds, and a negative test pins that a *named* field of the same type is composition, not `EXTENDS`. Rust: **already done** before this task — `analysis/passes/impl_pass.py` already turns `impl Trait for Type` into `IMPLEMENTS`, traits are already `SymbolKind.INTERFACE`, and `tests/test_rust_pipeline.py::test_impl_trait_for_type_is_implements` already covers it; verified live rather than trusted. |
| S4 | **HAS_TYPE query** | `models/relationships/relationship_kind.py:9 HAS_TYPE/RETURNS` + `graph/code_graph.py:168 has_type_of/typed_by/returns_of` | [x] `retrieval/hybrid_retriever.py:36 WHAT_TYPE_PATTERN + _graph_type_users has_type scan` + `sg search "where is AuthService type used"` `graph_type_users` intent |

**How to do:** Each in branch `analysis/passes/*`, reuse `compute_content_hash` + `build_stable_key` `analysis/fingerprints.py`. No new dep, just handlers + `relationship_builder.py:7 _RELATIONSHIP_BY_REFERENCE` mapping.

### P5-2: True incremental (not snapshot) + hierarchical hash — DONE ✅ (2026-09-03: append-only+merkle)

- [x] **Append-only chunks** — `storage/repositories/chunk_repository.py:4 INSERT OR REPLACE chunk_key` already `stable_key` upsert + `storage/index_store.py:44 _refresh_fts_keys` per `current_keys` + `_prune_derived` content_hash reuse `indexing/embedding_queue.py:22`
- [x] **Persist Merkle** — `indexing/merkle.py:1 compute_root leaves + dirs` + `indexing/indexer.py:250 _persist_merkle index_metadata merkle_root` after `persist_index` full+incremental — `compute_root 9c65a6b` deterministic
- Verify: `uv run pytest tests/test_incremental_indexer.py -v` `parsed_files==0` second reindex + `sqlite3 .sg/index.sqlite "select value from index_metadata where key='merkle_root'"`

### P5-3: Retrieval that learns (needs a real agent to run the training loop)

- [ ] Already `retrieval/reranker.py:20 learned_weights.json` stub + `session_memory/service.py:203 retrieval` logging. Add a training loop: `evaluation/ab_runner.py:129` paired `with_sg/without_sg` 20 tasks `evaluation/tasks.json` → logistic `REL/EXACT/GRAPH_DISTANCE` → `retrieval/learned_weights.json`. Gate `sg eval --embed mean_recall≥0.90` in `tests/test_evaluation_metrics.py:1` (fixture `0.83/0.78` `symbolgraph/cli.py:295` baseline).
- Verify: `sg eval --embed | grep mean_recall` + `ls retrieval/learned_weights.json`

### P5-4: Large-repo proof + token/$ savings — DONE ✅ (2026-09-05)

**Result:** `>4k`-token files save **90–94%** at budget 800 across all three pre-registered repos (fastapi, django, fiber); `<1k` files cost tokens. Recall gate met on all three (fastapi 0.90, django 1.00, fiber 0.95). Full table: `README.md` `## Token methodology`, raw data: `benchmarks/results/{fastapi,django,fiber}.json`, `benchmarks/results/SUMMARY.md`.

> **The one rule this task exists to enforce:** you do not pick the benchmark
> to fit the number. A plan that says "choose repos where `expected_files` are
> large, so the percentage clears 90" has selected its denominator to reach a
> predetermined headline — which is exactly what makes a competitor's 94%
> unbelievable, and adopting it with a better baseline definition just makes it
> a better-documented version of the same thing. The one asset this project has
> is that it publishes the unflattering number. Spend that and there is nothing
> left to sell.
>
> The finding is already in hand and it is not a single percentage: **savings
> scale with file size.** `benchmarks/results/self_retrieval.json` shows 76-78%
> on the two large files (`hybrid_retriever.py` 3773→840, `reranker.py`
> 3323→811) and deeply negative on small ones (`ranking.py` 96→845) because the
> context pack's fixed structure costs ~800 tokens regardless. Report *that*,
> segmented, and the large-file rows are credible precisely because the small
> ones are printed next to them.

#### P5-4a — Pre-registration (do this first, in its own commit, before any run)

- [x] Pick 3 repos on a criterion recorded **before** measuring, not after.
      Default: `local_fastapi/`, `local_django/`, `local_fiber/` — already
      pinned on disk (no clone drift), spanning Python/Python/Go. Write the
      criterion and the pinned commit SHAs into `benchmarks/PREREGISTRATION.md`.
- [x] Write 15-20 original `{query, expected_files, category}` per repo by
      reading the code, using `benchmarks/self_queries.json` as the shape.
      **Do not look at file sizes while writing them**, and do not consult any
      other project's query list (`P6-6`). Commit the query files **before**
      the first run, so git history proves they weren't tuned to the outcome.
- [x] In the same commit, pre-declare in `PREREGISTRATION.md`: the recall gate
      (`mean_recall_at_10 >= 0.90` to headline a repo), the size buckets below,
      and **that every repo run gets published whatever it returns**. A repo may
      only be dropped from a *headline* for failing the pre-declared recall
      gate — its numbers still get printed.
- [x] Write down what would falsify the claim: if the >4k bucket does not clear
      ~60% aggregate, the "savings scale with size" story is wrong and the
      honest output is the negative result.

#### P5-4b — Harness (real gap, verified)

`evaluation/external.py` already computes `mean_baseline_tokens`,
`mean_context_tokens`, `mean_savings_pct` and `aggregate_savings_pct`, and
`run_external_evaluation` already takes `token_budget: int = 800` — but
`benchmarks/run_external.py` **serializes none of it**: its `output_data` dict
carries only precision/recall/MRR/latency, and its CLI has no budget flag.
`self_retrieval.json` only has token fields because they were written in by hand.

- [x] `benchmarks/run_external.py`: add `--token-budget` (default 800) and
      `--budgets 800,1200,2000`; loop `run_external_evaluation(...,
      token_budget=b)` and nest as `budgets: {"800": {...}, ...}`, keeping the
      flat top-level keys for back-compat with existing readers.
- [x] Serialize the token fields per budget — `mean_baseline_tokens`,
      `mean_context_tokens`, `mean_savings_pct`, `aggregate_savings_pct` — plus
      per-question `baseline_tokens`/`context_tokens`/`savings_pct` (the fields
      already exist on `ExternalQuestionResult`).
- [x] Add `baseline_bucket` per question: `<1k`, `1k-4k`, `>4k` by
      `baseline_tokens`, and aggregate per bucket per budget. **This is the
      headline unit, not the whole-run mean.**
- [x] Extend `_recompute_file` to recompute per-budget and per-bucket aggregates
      (it already recomputes `aggregate_savings_pct` and enforces strict
      equality on stored precision/recall/RR — keep that check).
- [x] **No change to `evaluation/external.py:196` baseline logic.**
      `baseline = expected_files` content is the honesty moat; whole-repo stays
      refused at `evaluation/runner.py:202`.

#### P5-4c — Tests (extend, don't replace)

- [x] `test_multi_budget_monotonic` — across 800/1200/2000, `context_tokens` is
      non-decreasing and `aggregate_savings_pct` is non-increasing. Catches a
      budget that silently isn't applied.
- [x] `test_bucket_assignment_boundaries` — 999/1000/4000/4001 land in the
      intended buckets; a bucket with no questions reports null, not 0.0
      (0.0 would read as "no savings" rather than "no data").
- [x] `test_recompute_strict_equality` — already the behaviour of
      `_recompute_file`; pin it so a recompute can never quietly restate a
      stored metric.
- [x] Keep `test_aggregate_savings_is_token_weighted_not_mean_of_ratios` green —
      it is the reason the bucket table is aggregate-weighted.

#### P5-4d — Dollar conversion

- [x] `retrieval/pricing.py`: a small **dated** table, written from the current
      published rates, not copied from another project. As of **2026-06-24**:
      Claude Opus 5 `$5.00/$25.00`, Sonnet 5 `$2.00/$10.00`, Haiku 4.5
      `$1.00/$5.00` per 1M input/output. Default `sonnet`. Include the date in
      the module and print it with every dollar figure.
- [x] Input tokens only in v1: `dollars_saved = (mean_baseline_tokens -
      mean_context_tokens) * price_in / 1e6`, computed from the aggregate, never
      from the mean of per-query ratios. Say "input tokens only" in the output.
- [x] Dollars are a **projection, not a measurement** — they depend on a model
      price and a query volume this project does not control. Always render as
      a formula with its inputs visible (`N queries × tokens saved × $/1M`),
      never as a bare "saves $X".
- [x] `sg savings --json` reads `benchmarks/results/*.json`; `GET /api/savings`
      returns `{bucket, budget, aggregate_pct, tokens_saved, dollars_saved,
      model, price_date, recall_at_10}`.
- [x] Fix the stale hardcoded metrics in `symbolgraph/dashboard/app.py`
      (coverage/tests_passed drift from the measured `658` / `80.54%`).

#### P5-4e — Publication

- [x] `benchmarks/results/SUMMARY.md` — repo × budget × bucket, with commit SHA
      and queries-file link per row. (Note: the old `SUMMARY.md` was deleted
      deliberately in the third-party purge, not lost.)
- [x] `README.md` `## Token methodology` gains the bucket table and the dollar
      formula. `website/src/data/content.js` `TOKEN_SAVINGS` becomes per-repo ×
      per-bucket; keep the struck-through mean-of-ratios and the `+16.7%`
      self row as the small-file anchor.
- [x] Every published claim string carries: aggregate% **+ recall@10 + p50 +
      budget + bucket + baseline definition + commit SHA**. No dollar figure
      without model + price + price date.

- **Acceptance:** the table can be regenerated from a clean checkout by running
  the pinned commands, and every number in `README.md` and the website is
  `grep`-able in a tracked `benchmarks/results/*.json`.
- **Verify:** `uv run python benchmarks/run_external.py --recompute "benchmarks/results/*.json"` (strict equality passes) · `uv run pytest tests/test_external_eval.py tests/test_context_builder.py tests/test_tokenizer_fallback.py -q` · `uv run pytest -q` stays at or above `658 passed`, coverage `>=80%`.

- **Effort:** query authorship is the bottleneck at ~2-3 days and cannot be
  shortcut — it is the part that makes the result mean anything. Harness +
  pricing ~1 day, runs ~0.5 day/repo, publication ~0.5 day.

### P5-5: Correctness guardrails — DONE ✅ (2026-09-04)

- [x] **Parse-once invariant** — pinned in `tests/test_parse_pass.py`: 2 docs through `run_extraction_passes` → exactly 2 `TreeSitterParser.parse` calls. **Shadowing** — `hypothesis` (depth 1-4 nested same-name `f`) in `tests/test_name_resolution.py`: innermost call resolves to innermost def.
- Verify: `uv run pytest tests/test_name_resolution.py tests/test_parse_pass.py -q` → `17 passed`

**Execute order:** `S1+S2 (done) → S4+P5-2 (done) → P5-3 train (needs a real agent) → P5-4 benchmark`. Within `P5-4` the order is not negotiable: `P5-4a` pre-registration (queries committed **before** the first run) → `P5-4b` harness → `P5-4c` tests → `P5-4d` dollars → `P5-4e` publish. Running before the queries are committed forfeits the only thing that makes the result credible, because nothing afterwards can prove the queries weren't tuned to the outcome.

> **Honesty note on P5-3:** `retrieval/learned_weights.json` currently self-documents as `"_method": "grid search relationship/exact vs heuristic"` on the fixture. A 2-parameter grid search over a self-authored 20-task fixture is a *tuned heuristic*, not a learned reranker. Either finish P5-3 by fitting on external repos (fitting on the same fixture you measure against just overfits it more precisely), or call it "tuned weights" everywhere it's described — not "learns." Both are fine. Both at once is not.

> **AUDIT 2026-09-05 (real-fit attempt):** Built `scripts/train_reranker_learned.py` — a genuine logistic-regression fit over real (query, candidate, `RerankFeatures`) triples, captured by monkeypatching `retrieval.reranker._features` during live `HybridRetriever.retrieve()` calls against all 20 `evaluation/tasks.json` tasks, labeled against each task's own `expected_files`/`expected_symbols`. This is real per-candidate relevance supervision, not agent-session outcomes (see below for why `evaluation/ab_runner.py`'s task-success signal can't feed this). Result: 136 candidate examples (73 positive after loosening the label to file-OR-symbol match), training AUC 0.655. **Regresses 9 of `tests/test_reranker.py`'s existing passing tests** when its output replaces `retrieval/learned_weights.json` — confirms the honesty note above: 20 tasks, mostly tiny single/few-file fixtures, is too thin and noisy a sample to safely replace the grid-search-tuned heuristic. Reverted `retrieval/learned_weights.json` to the tuned version (`git checkout --`); 677 passed restored. The training script is committed as working, real infrastructure — running it again once `evaluation/tasks.json` has meaningfully more/larger tasks (or a held-out split) is the actual path to a defensible learned fit; swapping in its current output is not recommended.
>
> Separately, confirmed by experiment: `evaluation/ab_runner.py`'s paired `with_sg`/`without_sg` agent-session data (success/token/tool-call counts) is the *wrong* training signal for `learned_weights.json` regardless of sample size — those are whole-task outcomes, not per-candidate relevance labels, so there is no valid path from them to reranker feature weights. `scripts/ab_agent_cmd.py` (a real `claude -p` + MCP `--mcp-config` wrapper satisfying `ab_runner.py`'s file-based protocol) was built and verified against 3 real paid runs — confirmed via `--output-format stream-json` that `mcp__symbolgraph__*` tool calls are correctly detected — but was not run against the full 20-task manifest, since doing so would not have produced usable reranker training data.

---

## P6 — Publish (2026-09-04 audit) — SHIP BLOCKERS, do before any P5 work

> Audit re-measured on `2026-09-04`: `uv run pytest -q --cov` → `655 passed, 1 skipped, 80.77% branch` in `24.03s` (the header note above was stale, see `P6-5`). `uv build` → wheel + sdist OK. `uv run ruff check .` → `error: Failed to spawn: ruff`.
>
> Finding: symbolgraph's *engine* — symbol graph, HNSW vec0, a 401-LOC reranker, Merkle incremental — is solid; symbolgraph's *distribution* did not exist. Every task below is packaging, not code. None of them require touching `analysis/`, `retrieval/`, `indexing/`, or `storage/`.
>
> Three hard facts an agent must not re-litigate:
> 1. `LICENSE` did not exist, yet `README.md:13` badged MIT and `README.md:294` said "MIT — see `LICENSE`". Fixed in `P6-1`.
> 2. `.github/workflows/ci.yml:17` runs `uv run ruff check .` but `ruff` was in no dependency group — the lint job could not pass. Fixed in `P6-2`.
> 3. `benchmarks/results/django.json` existed and was tracked with real numbers on a real Django commit. It has since been removed along with the rest of `benchmarks/results/` and the query sets that produced it, because those query sets were derived from a third party's benchmark suite and this project no longer ships anything derived from it — see the note at the end of `P6-6`.

### Small-agent execution contract — read before starting

- **One task per run.** Do `P6-N`, run its `Verify`, tick its boxes, stop. Do not batch.
- **Touch only the files listed in that task's `Target`.** If a fix seems to need another file, stop and report instead.
- **`Verify` is the definition of done.** Paste the actual command output into the commit body. Never tick a box off reasoning alone.
- **Never invent numbers.** Every metric written into `README.md` must be copy-pasted from a command run in that same session, or read out of a tracked file in `benchmarks/results/`.
- **Regression gate after every task:** `uv run pytest -q` must not regress below its last-known baseline (current baseline: `657 passed, 0 skipped, 80.53% branch`) and `uv build` must stay green. If either breaks, revert.
- **Commit format:** `chore(P6-N): <what>` with the verify output quoted.
- **Order is fixed:** `P6-1 → P6-2 → P6-3 → P6-4 → P6-5` are blocking. `P6-6 → P6-10` after.

### P6-1: `LICENSE` file — LEGAL BLOCKER — DONE ✅ (2026-09-04)

- **Why:** Without it symbolgraph grants no rights: nobody at a company can adopt it and PyPI renders `License: UNKNOWN`. The MIT badge was an unbacked claim.
- **Target:** `LICENSE` (new), `pyproject.toml:5` `[project]`
- **Tasks:**
  - [x] Create `LICENSE` — standard MIT text, `Copyright (c) 2026 Deepjyoti Sarmah`.
  - [x] `pyproject.toml:10` after `requires-python` add `license = "MIT"` and `license-files = ["LICENSE"]`.
- **Acceptance:** `LICENSE` exists; built wheel metadata carries `License-Expression: MIT`. — confirmed in built wheel METADATA.
- **Verify:** `test -f LICENSE && uv build && python -c "import zipfile,glob; w=sorted(glob.glob('dist/*.whl'))[-1]; m=zipfile.ZipFile(w).read([n for n in zipfile.ZipFile(w).namelist() if n.endswith('METADATA')][0]).decode(); print([l for l in m.splitlines() if 'License' in l])"`

### P6-2: Make the lint job runnable — CI BLOCKER — DONE ✅ (2026-09-04)

- **Why:** `README.md:14` renders a CI badge for a workflow whose `lint` job failed at step 1 on every push. `ruff` had also **never been run on this codebase** before this task.
- **Target:** `pyproject.toml` `[dependency-groups] dev`, then whatever ruff flagged.
- **Tasks:**
  - [x] Add `"ruff>=0.13"` to the dev group; `uv sync`. (Also added `hypothesis>=6.100` and later `httpx>=0.27` — `uv sync` uncovered both were never declared, only pip-installed by hand, so their gated tests had been silently skipping everywhere including CI.)
  - [x] Ran `uv run ruff check .` — **116 findings on first run**. 61+33 mechanical fixes applied via `--fix`/`--unsafe-fixes` (import sort, unused imports, redefinitions, set-literal, unused locals in tests). One self-inflicted bug caught and fixed in-flight: a blind sed rename in `tests/test_editors.py` briefly broke `test_init_auto` — corrected before commit.
  - [x] Judgement-call findings (**not** hand-edited in `analysis/`, `retrieval/`, `indexing/`, `storage/`): consolidated into a documented `pyproject.toml [tool.ruff.lint] ignore` for `BLE001`/`S110` (deliberate best-effort exception handling, already the codebase's own prior pattern) + `SIM102`/`SIM103`/`SIM115`/`ASYNC220` (left selected-out with reasons in the config comment; genuine follow-up, not fixed blind). `SIM117` (nested `with`) fixed by hand — 6 sites, all in `tests/`, behavior-neutral.
- **Acceptance:** `uv run ruff check .` exits `0`; test suite stays green. Final baseline after this and `P6-5`'s follow-up fix: `657 passed, 0 skipped, 80.53% branch`.
- **Verify:** `uv run ruff check . && uv run pytest -q | tail -1`

### P6-3: PyPI metadata — the package page — DONE ✅ (2026-09-04)

- **Why:** `pyproject.toml` had **no** `authors`, `urls`, `classifiers`, or `keywords`. On PyPI that renders as a blank card. Highest legitimacy-per-minute item in the whole plan.
- **Target:** `pyproject.toml` `[project]`
- **Tasks:**
  - [x] `authors = [{ name = "Deepjyoti Sarmah", email = "deepjyoti-sarmah@users.noreply.github.com" }]` — GitHub noreply placeholder, one-line swap if a different address is preferred.
  - [x] `keywords = ["mcp", "rag", "code-search", "tree-sitter", "knowledge-graph", "llm", "code-intelligence"]`
  - [x] `classifiers` — `Development Status :: 4 - Beta`, `Intended Audience :: Developers`, `License :: OSI Approved :: MIT License`, `Operating System :: OS Independent`, Python `3` / `3.11` / `3.12` / `3.13`, `Topic :: Software Development :: Libraries :: Python Modules`, `Topic :: Software Development :: Documentation`, `Typing :: Typed`.
  - [x] `[project.urls]` — `Homepage`/`Repository`/`Issues` = `https://github.com/Deepjyoti-Sarmah/coding-RAG-system` (+ `/issues`), `Changelog` = `.../blob/main/CHANGELOG.md`.
- **Acceptance:** wheel METADATA contains `Project-URL`, `Classifier`, `Keywords`, `Author`. — confirmed.
- **Verify:** `uv build && python -c "import zipfile,glob; w=sorted(glob.glob('dist/*.whl'))[-1]; z=zipfile.ZipFile(w); m=z.read([n for n in z.namelist() if n.endswith('METADATA')][0]).decode(); print('\n'.join(l for l in m.splitlines() if l.startswith(('Project-URL','Classifier','Keywords','Author'))))"`

### P6-4: Cap dependency ranges — DONE ✅ (2026-09-04)

- **Why:** `mcp>=2.0.0` and `tree-sitter>=0.25.2` were both **unbounded**. `uv tool install` resolves fresh from PyPI and **ignores `uv.lock`**, so the lockfile does not protect an end user from a future breaking major.
- **Target:** `pyproject.toml` `dependencies`
- **Tasks:**
  - [x] `"mcp>=2.0,<3"` — `symbolgraph/mcp_server.py:5` imports `mcp.server.mcpserver.MCPServer`, a 2.x-only path; a 3.x release breaking that API stops the MCP server from starting with no clear error.
  - [x] `"tree-sitter>=0.25.2,<0.26"` — the grammar pins (`tree-sitter-c==0.24.1`, `tree-sitter-cpp==0.23.4`, `tree-sitter-java==0.23.5`) are 0.25-ABI wheels. Mixing a 0.26 core with them corrupts memory reading `Node.start_point/end_point`. **This was not theoretical:** `uv tool install --force dist/*.whl` on this exact machine, before the cap, had already resolved `tree-sitter==0.26.0` unbounded — the fix changed a live install to `0.25.2`.
  - [x] Added a comment above each cap saying why and when it may be lifted.
- **Acceptance:** a fresh install from the wheel still runs. — confirmed: `uv tool install --force` → `sg --version` → `0.1.0`, `sg init` → `Wrote .mcp.json`, from a clean `mktemp -d` outside the checkout.
- **Verify:** `uv build && uv tool install --force dist/*.whl && cd "$(mktemp -d)" && sg --version && sg init && test -f .mcp.json && echo OK`

### P6-5: Reconcile README numbers with measurement — DONE ✅ (2026-09-04)

- **Why:** Honesty is the differentiator this project claims for itself (`README.md:69`). Drifted badges cost exactly that.
- **Target:** `README.md`
- **Tasks:**
  - [x] Fixed badge counts to the measured `657 passed` / `80.53% branch`.
  - [x] Deleted a stale "not yet in `benchmarks/results/*.json`" clause that had become false.
  - [x] Fixed every other stale count in the file to match a fresh measurement.
- **Acceptance:** no stale count remains.
- **Verify:** `uv run pytest -q --cov 2>&1 | tail -2`

**Real regression caught mid-task, not just README drift:** the first `--cov` run under this task measured **79.91%, below the 80% gate** — a genuine drop from the number the header claimed. Root cause: `embeddings/ollama_provider.py` imports `httpx` inline with a urllib fallback, but `httpx` was never declared as a dependency anywhere — only pip-installed by hand in the local dev venv, same defect class as the `hypothesis` gap found in `P6-2`. Two httpx-path tests had been silently skipping everywhere, including CI, undercounting `embeddings/` coverage. Fixed by adding `"httpx>=0.27"` to dev deps (testing-only — end users still get the urllib fallback, ollama support stays optional). After the fix: `657 passed, 0 skipped, 80.53% branch`.

**New follow-up found, not fixed (out of scope for a packaging task):** `uv run pytest -q --cov` emits **27 warnings**, mostly `ResourceWarning: unclosed database in <sqlite3.Connection ...>` from tests that don't close their connection. Test hygiene, not a packaging fix — flagged for a future pass.

### P6-6: External benchmark — removed, needs original queries

- **What happened:** This task previously published a real-repo benchmark table (Django/FastAPI/Express/chi/Fiber) sourced from `benchmarks/results/*.json`. Those result files, and the `*_queries.json` files that produced them, have since been **deleted**: the query sets (`{query, expected_files}` lists) were derived from a third-party project's benchmark suite, and this project no longer ships anything derived from another project's work.
- **What's left:** `tests/fixtures/evaluation_repo` is the only benchmark data in the repo now — self-authored, so it carries no attribution obligation. `README.md`'s benchmark section reflects only that fixture.
- **To get real-repo numbers back honestly:** write an original `{query, expected_files}` set per target repo from scratch (don't consult or copy anyone else's query list while doing it), then run `benchmarks/run_external.py --repo <url> --source-dir <dir> --queries <your-file> --output benchmarks/results/<name>.json` and cite only what that produces. This is `P5-4`.
- **Verify:** `grep -ri 'third.party\|derived from\|attribution' README.md benchmarks/` returns nothing benchmark-related; `ls benchmarks/*.json benchmarks/results/ 2>&1` shows no files.

### P6-7: `CHANGELOG.md` + `CONTRIBUTING.md` + `SECURITY.md` — DONE ✅ (2026-09-04)

- **Why:** Their absence is the tell separating "someone's project" from "a project". `SECURITY.md` is not boilerplate here: symbolgraph reads source trees and redacts credentials, so a disclosure path is on-topic.
- **Target:** `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md` (all new)
- **Tasks:**
  - [x] `CHANGELOG.md` — Keep-a-Changelog, `0.1.0` seeded from `git log --oneline --grep='^feat'` (224 total commits), grouped by area not a raw commit dump; `[Unreleased]` present.
  - [x] `CONTRIBUTING.md` — `uv sync`, the three CI checks (`ruff`, `--cov-fail-under=80`, `-m "not slow"`), the `README.md ## Engineering rule` quote, and a directory map flagging `analysis/retrieval/indexing/storage` as the semantic core.
  - [x] `SECURITY.md` — supported version (`0.1.x`), GitHub private vulnerability reporting (no fabricated email), explicit "what symbolgraph deliberately does / does not do" split.
- **Verify:** `ls CHANGELOG.md CONTRIBUTING.md SECURITY.md && head -5 CHANGELOG.md`

### P6-8: Tag `v0.1.0` + `publish.yml` — workflow DONE ✅, tag pending

- **Why:** 217+ commits, **zero tags**. There is no installable known-good symbolgraph and no way to say "fixed in 0.1.1".
- **Target:** `.github/workflows/publish.yml` (new)
- **Tasks:**
  - [x] `.github/workflows/publish.yml` — trigger `on: push: tags: ['v*']`; three jobs: `test` (full `ubuntu/macos/windows × 3.11/3.12/3.13` matrix, ruff + pytest + 80% gate, same as `ci.yml`) → `build` (asserts the pushed tag matches `pyproject.toml`'s `version` before building, `uv build`, uploads the dist artifact) → `publish` (PyPI **trusted publishing**, OIDC, `permissions: id-token: write`, `environment: pypi` — no API token in secrets).
  - [x] `test` gates `build` gates `publish` via `needs:` — nothing publishes without a green full matrix on the tagged commit.
  - [ ] **Not done — needs your decision, not mine:** `git tag -a v0.1.0 -m "..." && git push origin v0.1.0`. Pushing a tag is what actually triggers `publish.yml`; if PyPI trusted publishing isn't configured yet (one-time step on pypi.org: project → Publishing → add this repo + `publish.yml` + environment `pypi` as a trusted publisher) the `publish` job will fail closed rather than leak a token, but the tag itself is still an outward, hard-to-cleanly-reverse action on a shared branch. Left for explicit go-ahead.
- **Acceptance:** tag push produces a PyPI release; `uv tool install symbolgraph` works from a clean machine. — workflow verified valid; tag/publish pending.
- **Verify:** `git tag | grep v0.1.0 && test -f .github/workflows/publish.yml`

### P6-9: `server.json` — MCP registry listing — DONE ✅ (2026-09-04)

- **Why:** The MCP registry is the actual distribution channel for a tool like this. symbolgraph already declares the `sg-mcp` entry point and exposes **13 tools** via `mcp.tool()` — the work is a manifest, not code.
- **Target:** `server.json` (new)
- **Tasks:**
  - [x] `name: io.github.Deepjyoti-Sarmah/sg`, package `symbolgraph` from PyPI. Added `runtimeArguments: ["--from", "symbolgraph", "sg-mcp"]` since the PyPI package name and the MCP command name differ — plain `uvx symbolgraph` would try to run a script that doesn't exist; this is the standard `uvx --from <package> <script>` idiom for that case.
  - [ ] `version` in lockstep with `pyproject.toml` is manual today (both currently `0.1.0`) — no automated check ties them; bump both together at the next release.
- **Verify:** `python -c "import json; d=json.load(open('server.json')); print(d['name'], d['version'])"`

### P6-10: Repo-root hygiene — DONE ✅ (2026-09-04)

- **Why:** `docs/IMPLEMENTATION.md` is **186 KB**; at the repo root that's the 2nd thing a visitor sees, and reads as unfinished rather than thorough. Separately `.sg/` and `.coverage` were sitting untracked because `.gitignore` omitted them.
- **Target:** `.gitignore`, `docs/`
- **Tasks:**
  - [x] `.gitignore` — added `.sg/`, `.coverage`, `.pytest_cache/`, and an anchored `/results/` (leading slash so it matches only the root-level scratch dir, not the now-removed `benchmarks/results/`).
  - [x] `git mv IMPLEMENTATION.md docs/IMPLEMENTATION.md` + `git mv DESIGN_C_CPP.md docs/DESIGN_C_CPP.md`, fixed all inbound references.
  - [x] **Deviation from the task as written:** this roadmap file itself was **not** moved into `docs/`. It's the live document driving execution while the user works through it box-by-box at the repo root; relocating it mid-task for a cosmetic win risks breaking that reference for zero benefit.
- **Verify:** `git status --porcelain | grep -E '\.sg|\.coverage' | wc -l` → `0`

### P6 — done when

```bash
test -f LICENSE && \
uv run ruff check . && \
uv run pytest -q | tail -1 && \
uv build && \
git tag | grep -q v0.1.0 && echo "READY TO PUBLISH"
```

**Order restated for the agent:** `P6-1 → P6-2 → P6-3 → P6-4 → P6-5` (blocking, done) → `P6-7`, `P6-9`, `P6-10` (done) → `P6-8` tag push (pending your go-ahead) → `P6-6` (needs original queries first, see `P5-4`).

---

## Final Acceptance Checklist

- [x] `sg init --agent all` configures editors idempotently — **DONE `symbolgraph/editors.py:1` 8 editors + `symbolgraph/cli.py:400` TOML `sg-<slug>` + `tests/test_editors.py:1` 8 tests**
- [x] `sg index . && sg status --oneline` shows `symbols X chunks Y pending Z gen N` — **DONE**
- [x] `sg search "auth" --top-k 5` returns `CALLS/IMPORTS` expanded with `vector_search_used` flag — **DONE**
- [x] `.env` + PII scrubbed, concurrent `sg index` locked, `git commit` auto-reindexes — **DONE `indexing/secrets.py:1` 14 regexes + `redact_pii` + `indexing/resource_governor.py:57` `ProjectIndexLock`+`is_memory_pressured`+`IdleTracker` + `indexing/git_hooks.py:1`**
- [x] `uv run pytest --cov --cov-fail-under=80 -q` passes — **DONE**
- [x] `sg dashboard --no-browser` serves FastAPI on `127.0.0.1:8765` with CSRF+token — **DONE `symbolgraph/dashboard/server.py:34` `_check_auth` + `symbolgraph/dashboard/app.py:1` `POST /api/reindex`+`GET /api/files|savings`+`DELETE`**
- [x] `sg eval-ab --pilot --preflight` provisions paired worktrees — **DONE**
- [x] `LICENSE` + PyPI metadata + capped deps + lint clean + `CHANGELOG`/`CONTRIBUTING`/`SECURITY` + `publish.yml` + `server.json` — **DONE, tag pending**

## Commands for agent

```bash
# setup
uv sync
uv run pytest -q
uv run pytest --cov --cov-report=term-missing --cov-fail-under=80 -q

# smoke
sg --version
sg index tests/fixtures/evaluation_repo --no-background
sg status --oneline
sg search "login" --top-k 3
sg context "how does login work?" --budget 800

# fallback chunking
mkdir -p /tmp/fb && echo "<html>hi</html>" > /tmp/fb/a.html && sg index /tmp/fb --no-background && sg status /tmp/fb && sg search "hi" /tmp/fb

# editors
rm -rf /tmp/p0e && mkdir -p /tmp/p0e/.vscode /tmp/p0e/.cursor && touch /tmp/p0e/opencode.json && sg init /tmp/p0e --agent all && cat /tmp/p0e/.mcp.json

# secrets
uv run pytest tests/test_secrets.py -v
python -c "from indexing.secrets import redact_secrets; print(redact_secrets('MY_TOKEN=123456789012345678'))"

# dashboard
sg dashboard --no-browser --port 8766 &
sleep 1; curl -s http://127.0.0.1:8766/api/status | jq .
curl -s -H "Sec-Fetch-Site: cross-site" http://127.0.0.1:8766/api/status | grep -q csrf && echo "csrf ok"

# ab harness
sg eval-ab --pilot --preflight --output /tmp/ab
sg eval --embed
```

## References

- `pyproject.toml:7 version 0.1.0`, `README.md`, `docs/IMPLEMENTATION.md`, `docs/DESIGN_C_CPP.md`
