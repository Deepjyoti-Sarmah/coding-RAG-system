# Track 2: module-symbol synthesis for definition-free documents

Measures the effect of `analysis/passes/module_symbol_pass.py` (added in this
change) against the Track 1 baseline (`benchmarks/results/{express,chi,django,
fastapi,fiber}.json`, commit `3df5c40`). Before/after JSONs for this
comparison are `benchmarks/results/track2_<repo>.json`.

## Design recap

Per the architectural constraint in the task brief, no symbol-less chunk was
invented. `SemanticChunk.chunk_key` is `symbol.stable_key`
(`chunking/symbol_chunker.py:73`) and `storage/repositories/chunk_fts_repository.py:37-40`
silently drops any chunk whose `symbol_id` doesn't resolve — a symbol-less
chunk would vanish from the FTS index with no error. Instead, a document that
the symbol pass extracts nothing from gets exactly one synthesized `Symbol` of
a new kind, `SymbolKind.MODULE` (`models/entities/symbol_kind.py`), and flows
through the existing chunker path unchanged.

`analysis/passes/module_symbol_pass.py` runs after `run_import_pass` and
`run_export_pass` (it needs their output) and before `run_reference_pass`.
For each parsed document with zero symbols, it checks whether the document has
any recorded imports or exports; if so it builds one module symbol via
`build_module_symbol`, reusing `build_stable_key`/`compute_content_hash`/
`compute_signature_hash` from `analysis/fingerprints.py` the same way real
symbols do. A document with neither imports nor exports (a bare `__init__.py`)
gets nothing — an empty chunk would be index noise with no recall benefit.

The embedding text comes from the unmodified `build_embedding_text`
(`chunking/symbol_chunker.py:124`), so a module symbol's chunk reads
`module <name>` / `qualified name: <path>` / `imports: ...` / `exports: ...`
/ `source: <file content>` — the re-exported/imported names surface in two
separate fields, not just raw text.

`storage/schema.py:SCHEMA_VERSION` bumped 4 → 5 so an existing on-disk index
built before this change gets dropped and rebuilt on next open, picking up
module symbols for files whose content didn't otherwise change (unchanged
files are skipped by the incremental indexer's file-hash diff, so without a
schema bump they'd keep serving pre-change, symbol-less state indefinitely).
This reuses `storage/schema.py:create_schema`'s existing drop-and-rebuild path,
already covered by `tests/test_schema_upgrade.py` — no new invalidation
mechanism was written. `CHUNK_VERSION` was left at `"v1"`: grepping the
codebase turned up no code path that reads it for invalidation (it's stored
per-chunk but nothing compares it), so bumping it would have been cosmetic.

## Probe case

```
$ .venv/bin/python3 -c "from analysis.build_graph import build_graph; ..."
documents: ['empty_init.py', 'middleware/cors.py', 'real.py']
symbols: [('real_function', 'function', 'real.py'), ('cors.py', 'module', 'middleware/cors.py')]
chunks: [('real.py', ...), ('middleware/cors.py', 'module cors.py\nqualified name: middleware/cors.py\n...')]
```

`middleware/cors.py` (`from starlette.middleware.cors import CORSMiddleware as CORSMiddleware  # noqa`)
now yields exactly one chunk, containing `imports: import { CORSMiddleware }
from "starlette.middleware.cors"`. `empty_init.py` (a genuinely empty file)
yields nothing. `real.py` (a real function) is unaffected.

## Recall, before → after

| repo | before R@10 | after R@10 | delta | before MRR | after MRR |
|---|---|---|---|---|---|
| express | 1.000 | 1.000 | 0 | 0.875 | 0.875 |
| chi | 0.917 | 0.917 | 0 | 0.833 | 0.833 |
| django | 0.818 | 0.818 | 0 | 0.647 | 0.670 |
| fastapi | 0.700 | **0.825** | **+0.125** | 0.508 | 0.557 |
| fiber | 0.737 | 0.737 | 0 | 0.418 | 0.418 |
| **mean** | **0.834** | **0.859** | **+0.025** | 0.656 | 0.667 |

Only fastapi's recall moved. That matches the coverage audit: fastapi was the
only repo among the five where a *never-retrieved expected file* was a
definition-free document (`chi`/`express` had none; `fiber`'s
`middleware/logger/logger.go` and `django`'s two never-retrieved files were
already indexed with real symbols — their zero recall was a ranking problem
outside this task's scope, confirmed in `COVERAGE.md`). Django's MRR moved
+0.023 despite unchanged recall — the extra module chunks compete as
candidates and shifted rank order on some already-hit queries, for better
in aggregate.

**This is a smaller improvement than the task's own prediction of ~0.95 for
fastapi / +0.03-0.04 mean.** Reported here as measured, not adjusted to match
the estimate.

### fastapi, file by file

`benchmarks/audit_coverage.py --check` before/after:

| file | before | after |
|---|---|---|
| `middleware/cors.py` | no_symbols | indexed fine (symbols=1, chunks=1) |
| `staticfiles.py` | no_symbols | indexed fine (symbols=1, chunks=1) |
| `templating.py` | no_symbols | indexed fine (symbols=1, chunks=1) |
| `websockets.py` | no_symbols | indexed fine (symbols=1, chunks=1) |
| `routing.py` | skipped: size | skipped: size (unchanged, out of scope) |

All four definition-free files are indexed now. Per-query effect
(`benchmarks/results/track2_fastapi.json`):

| query | expected | before recall | after recall |
|---|---|---|---|
| How does FastAPI handle CORS middleware? | `middleware/cors.py` | 0 | **1.0** |
| How does FastAPI integrate with Jinja2 templates? | `templating.py` | 0 | **1.0** |
| How are WebSocket endpoints defined and handled? | `routing.py`, `websockets.py` | 0 | 0.5 (websockets.py now hits; routing.py still lost to the size cap) |
| How does FastAPI serve static files? | `staticfiles.py` | 0 | 0 (still not ranked in top 10, despite being indexed — a ranking problem, not coverage) |

2 of 4 checked-file queries went from a full miss to a full hit, one went
from a full miss to a partial hit, and one stayed a full miss for a reason
outside this task (ranking). Being indexed is necessary but not sufficient
for being retrieved in the top 10 — `staticfiles.py`'s single module chunk
apparently doesn't score highly enough against its query under the current
BM25/vector ranking, which this task was explicitly told not to touch.

## Chunk-count deltas (repo-wide, not just the checked files)

| repo | zero-symbol docs before | zero-symbol docs after | total chunks before | total chunks after | new chunks |
|---|---|---|---|---|---|
| express | 0 | 0 | 233 | 233 | 0 |
| chi | 0 | 0 | 462 | 462 | 0 |
| django | 283 | 240 | 11,986 | 12,029 | **+43** |
| fastapi | 20 | 3 | 343 | 360 | **+17** |
| fiber | 8 | 3 | 5,479 | 5,484 | **+5** |

Django gained 43 new module chunks out of 927 documents (+0.36% of total
chunks) — real, but far below the 283 originally flagged in `COVERAGE.md`,
because most of Django's definition-free files (the 85 `conf/locale/*/formats.py`
modules, most `__init__.py` files) have neither imports nor exports — they are
bare constant assignments with no `import`/`from` statements at all, so by
design they synthesize nothing. The remaining 240 django zero-symbol
documents are genuinely content-free by this pass's definition and stay
unreachable; broadening what counts as "worth retrieving" (e.g. synthesizing
from top-level constant assignments too) was out of scope for this task.

Fiber gained 5 of its 8 zero-symbol documents (the ones with imports, e.g.
`constants.go`'s package-level `const` block still has an import line); the
other 3 have neither and stay empty.

## Guardrail checks

- `ckg eval --embed` on `tests/fixtures/evaluation_repo`: **0.97 / 0.96,
  unchanged** from the pre-Track-2 baseline confirmed earlier in this same
  session.
- `.venv/bin/python3 -m unittest discover tests -q`: **512 tests, all
  passing** (508 existing + 4 new in `tests/test_module_symbol_pass.py`).
- `grep -rc huggingface` across the tree (excluding `.venv`,
  `code-context-engine/`, `.git`): **0** — suite runs fully offline.
- No changes to `retrieval/reranker.py`, `build_fts_query`, the per-file cap,
  or the BM25 weights.
- No changes under `code-context-engine/`.
- `config.py:MAX_FILE_SIZE_BYTES` untouched; `routing.py` stays dropped by the
  size cap, as scoped.
