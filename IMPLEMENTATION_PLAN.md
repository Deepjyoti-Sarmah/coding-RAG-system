# Production Codebase RAG Plan

Purpose: this file is the implementation guide for turning this repo into a production-grade, local-first codebase RAG / semantic indexer.

This plan is written so that:
- a junior engineer can follow it step by step
- a smaller model can execute one task at a time
- progress can be updated inside this file

---

# Rules for Implementation

1. Do not add cloud dependencies.
2. Keep all parsing, indexing, embeddings, graph storage, and retrieval local.
3. Prefer correctness before adding new features.
4. Do not add embeddings before fixing semantic correctness.
5. Update this file after every completed task.
6. When changing code, add small `# TODO:` comments only where the next action is not obvious.
7. Keep TypeScript/JavaScript as the first supported language. Do not expand languages until TS/JS works correctly.

---

# Current Repo Reality Check

README says many things are complete, but the code is still earlier-stage.

Important mismatch:
- README says import extraction and import resolution are done
- actual pipeline does not run import passes

Important current goal:
- make the semantic pipeline correct
- persist graph + embeddings locally in SQLite
- support incremental updates for frequent edits/renames/moves
- then add hybrid retrieval and reranking

---

# Current Known Bugs / Gaps

## 1. `analysis/build_graph.py` loads documents twice

Problem:
- `load_code_files(root_dir)` is called twice
- documents get different UUIDs each time
- `context.document_index` and `build_result.documents` can become inconsistent

Impact:
- document-linked resolution can break
- import/document mapping can break

Fix:
- load documents once
- reuse the same list everywhere

Code area:
- `analysis/build_graph.py`

Suggested code comment:
```py
# TODO: Load documents only once. Reusing the same Document objects is required
# so document_id stays stable across all passes.
```

---

## 2. Import extraction exists but is not wired into pipeline

Problem:
- `analysis/import_extractor.py` exists
- `analysis/passes/import_resolver_pass.py` exists
- but `build_graph()` never calls import extraction or import resolution

Impact:
- README claims import pipeline works, but current graph does not use imports
- cross-file symbol resolution cannot become correct without this

Fix:
- create and run an import pass
- then run import resolver pass

Code areas:
- `analysis/build_graph.py`
- new file likely needed: `analysis/passes/import_pass.py`

Suggested code comment:
```py
# TODO: Run import extraction before reference resolution so imported names can be
# used during cross-file symbol resolution.
```

---

## 3. Reference resolver is too naive

Problem:
- `analysis/passes/resolver_pass.py` resolves by name only
- it picks `targets[0]`
- ignores lexical scope, imports, aliases, module boundaries

Impact:
- wrong symbol links
- wrong call graph
- noisy retrieval later

Fix:
- replace naive lookup with scoped resolution
- use `analysis/semantic/name_resolver.py` as base
- extend it for imported symbols and module symbols

Code area:
- `analysis/passes/resolver_pass.py`

Suggested code comment:
```py
# TODO: Replace first-match name lookup with real scope-aware resolution.
# Resolution order should be: local scope -> parent scope -> module scope -> imports.
```

---

## 4. `main.py` uses wrong symbol fields

Problem:
- code uses `symbol.start_line`
- actual data model stores line info at `symbol.location.start_line`

Impact:
- CLI output is wrong / broken

Fix:
- update output accessors to use `symbol.location.start_line`

Code area:
- `main.py`

Suggested code comment:
```py
# TODO: Symbol location lives under symbol.location, not directly on Symbol.
```

---

## 5. Declared supported languages do not match parser support

Problem:
- loader accepts `.py` and `.md`
- parser registry only supports TS/JS/TSX/JSX

Impact:
- unsupported files are loaded but not parsed
- creates confusion about real system capability

Fix options:
- Option A: remove unsupported extensions for now
- Option B: keep loading them, but clearly separate parseable vs non-parseable documents

Recommended now:
- support only TS/JS family for v1

Code areas:
- `ingestion/language.py`
- `config.py`
- `parsing/registry.py`

Suggested code comment:
```py
# TODO: Keep v1 language support aligned with parser support. Do not advertise
# Python/Markdown indexing until parser + analysis passes exist for them.
```

---

## 6. `pyproject.toml` is missing runtime dependencies used by code

Problem:
- code imports `numpy`, `sentence_transformers`, `sklearn`
- these are not in `pyproject.toml`

Impact:
- retrieval pipeline is not installable from project metadata

Fix:
- add missing dependencies only when the retrieval pipeline is ready
- avoid adding embedding dependencies before semantic fixes if not needed immediately

Code area:
- `pyproject.toml`

Suggested code comment:
```toml
# TODO: Keep dependencies aligned with actually imported runtime modules.
```

---

## 7. Variable symbol registration likely uses wrong AST node type

Problem:
- `analysis/registry.py` registers `"variable_declaration"`
- handler name and logic suggest it expects declarator-like fields (`name`, `value`)

Impact:
- top-level variable/function-like declarations may be missed or extracted incorrectly

Fix:
- verify Tree-sitter node types for TS/JS
- register correct node type(s)
- add tests for `const x = 1`, `const fn = () => {}`, destructuring, exports

Code areas:
- `analysis/registry.py`
- `analysis/symbol_handlers/variable.py`

Suggested code comment:
```py
# TODO: Verify actual TS/JS AST node type here. This handler appears to expect a
# declarator-style node, not a declaration wrapper node.
```

---

## 8. No persistent storage yet

Problem:
- graph/index only exists in memory

Impact:
- no local durable index
- no incremental updates
- no rename/move tracking

Fix:
- add SQLite-based storage layer
- store graph tables, chunk tables, embeddings, file state

---

## 9. No incremental indexing yet

Problem:
- every run rebuilds everything

Impact:
- poor UX on active codebases
- expensive re-embedding

Fix:
- hash files
- only reindex changed files
- delete/rebuild records for changed files
- preserve stable lineage where possible

---

# North Star Architecture

```text
Repository
  -> File Scanner
  -> ParsedDocument IR
  -> Symbol Pass
  -> Import Pass
  -> Export Pass
  -> Reference Pass
  -> Resolver Pass
  -> Relationship Pass
  -> SQLite Graph Store
  -> Chunk Builder
  -> Embedding Store (SQLite local vector)
  -> Hybrid Retrieval
  -> Reranking
  -> Context Builder
  -> LLM
```

All local. No cloud.

---

# Implementation Phases

---

# Phase 0 - Stabilize Current Code

Goal:
- fix correctness bugs before adding new features

Status: COMPLETED

Phase summary:
- All Phase 0 tasks are complete.
- Variable extraction was verified with passing tests in `tests/test_variable_extraction.py`.
- New work should start from Phase 1.

## Task 0.1 - Fix double document loading

Files:
- `analysis/build_graph.py`

Steps:
1. Load documents once.
2. Assign the same list to both `build_result.documents` and `context.document_index`.
3. Confirm all downstream passes use the same `Document` objects.

Done when:
- `load_code_files(root_dir)` is called once inside `build_graph()`

Checklist:
- [x] Remove second document load
- [x] Reuse one shared `documents` list
- [x] Verify `document_id` consistency across passes

---

## Task 0.2 - Fix CLI symbol location bug

Files:
- `main.py`

Steps:
1. Replace direct line access with `symbol.location.start_line`.
2. Search for any other direct `start_line` / `end_line` assumptions.

Done when:
- CLI can print correct symbol locations

Checklist:
- [x] Fix `symbol.start_line`
- [x] Search for similar location field misuse
- [x] Fix `result.symbol_index` not exposed on `BuildResult`

---

## Task 0.3 - Align language support with parser support

Files:
- `config.py`
- `ingestion/language.py`
- `parsing/registry.py`

Recommended v1 behavior:
- support only `.ts`, `.tsx`, `.js`, `.jsx`

Steps:
1. Remove `.py` and `.md` from v1 indexing config OR clearly mark them as non-parseable.
2. Ensure README / future docs match actual support.

Done when:
- loader/parser behavior is consistent and unsurprising

Checklist:
- [x] Decide supported extensions for v1
- [x] Update config
- [x] Update language mapping if needed

---

## Task 0.4 - Verify AST node types for variables

Files:
- `analysis/registry.py`
- `analysis/symbol_handlers/variable.py`
- `tests/test_variable_extraction.py`

Current status:
- registry mapping was changed from `variable_declaration` to `variable_declarator`
- handler name typo was fixed
- 8 verification tests pass

Steps:
1. Inspected actual TS/JS tree-sitter node shapes — confirmed `variable_declarator` has `name`/`value` fields, `variable_declaration` does not.
2. Added tests covering all required cases.
3. Verified `_is_module_scoped()` works correctly against exported and nested declarations.

Done when:
- top-level variable and arrow-function symbols are extracted correctly ✅
- exported declarations are extracted correctly ✅
- nested function-local variables are not incorrectly extracted as module-level symbols ✅
- destructuring is skipped correctly ✅

Checklist:
- [x] Verify node type (`variable_declaration` -> `variable_declarator`)
- [x] Fix registry mapping
- [x] Fix function name typo (`handle_varibale_declarator` -> `handle_variable_declarator`)
- [x] Add tests for `const x = 1`
- [x] Add tests for `const fn = () => {}`
- [x] Add tests for `export const x = 1`
- [x] Add tests for destructuring skip behavior
- [x] Add tests proving nested non-module variables are not extracted
- [x] Re-check `_is_module_scoped()` using real AST behavior
- [x] Mark Phase 0 complete only after tests pass

---

# Phase 1 - Introduce Stable ParsedDocument IR

Goal:
- parse once and reuse cleanly in all passes

Status: NOT STARTED

## Task 1.1 - Create `ParsedDocument`

Suggested new file:
- `models/parsed_document.py`

Suggested fields:
- `document: Document`
- `tree: Tree`
- `file_hash: str`

Steps:
1. Create dataclass.
2. Parse each document once.
3. Store parsed documents in context/result.

Done when:
- symbol/import/reference/export passes consume `ParsedDocument`

Checklist:
- [ ] Create `ParsedDocument`
- [ ] Create parse stage in pipeline
- [ ] Refactor passes to use parsed docs

Suggested code comment:
```py
# TODO: All semantic passes should consume ParsedDocument so we never re-parse the
# same file during one indexing run.
```

---

## Task 1.2 - Extend indexing context

Files:
- `models/indexing_context.py`

Add fields like:
- parsed documents
- import/export indexes later
- file hashes later

Checklist:
- [ ] Add parsed-document storage
- [ ] Keep context focused on reusable intermediate state

---

# Phase 2 - Wire Import Pipeline

Goal:
- make import extraction and module resolution real

Status: NOT STARTED

## Task 2.1 - Add import pass

Suggested new file:
- `analysis/passes/import_pass.py`

Behavior:
- iterate over parsed documents
- call `extract_imports(...)`
- append to `result.import_references`

Checklist:
- [ ] Create import pass
- [ ] Use parsed documents
- [ ] Store results in `BuildResult`

Suggested code comment:
```py
# TODO: Import references must be extracted before symbol resolution can handle
# imported names and aliases.
```

---

## Task 2.2 - Run import resolver pass in pipeline

Files:
- `analysis/build_graph.py`

Correct order should become approximately:
1. load docs
2. parse docs
3. symbol pass
4. import pass
5. import resolver pass
6. reference pass
7. reference resolver pass
8. relationship pass
9. graph pass

Checklist:
- [ ] Insert import pass
- [ ] Insert import resolver pass
- [ ] Verify build order

---

## Task 2.3 - Test import forms

Files to add:
- `tests/...` (create a test layout if none exists)

Test cases:
- named import
- multi named import
- alias import
- default import
- namespace import
- mixed import

Checklist:
- [ ] Test extraction
- [ ] Test module resolution
- [ ] Test local alias mapping

---

# Phase 3 - Replace Naive Reference Resolution

Goal:
- resolve symbols correctly inside and across files

Status: NOT STARTED

## Task 3.1 - Use scoped local resolution

Files:
- `analysis/passes/resolver_pass.py`
- `analysis/semantic/name_resolver.py`

Steps:
1. Replace direct `lookup_by_name` + first hit.
2. Resolve in this order:
   - local scope
   - parent scope
   - module scope
   - imported symbols
3. Keep unresolved references explicit instead of guessing badly.

Checklist:
- [ ] Call `resolve_symbol(...)`
- [ ] Add unresolved-path handling
- [ ] Stop using `targets[0]`

Suggested code comment:
```py
# TODO: Never resolve by global first-name match when a scoped resolution path exists.
```

---

## Task 3.2 - Add imported symbol resolution

Need new behavior:
- `ImportReference` should resolve not just to `Document`
- it should eventually resolve to the actual exported `Symbol`

Current:
```text
ImportReference -> Document
```

Target:
```text
ImportReference -> Exported Symbol
```

Checklist:
- [ ] Add export model/index
- [ ] map imported names to exported symbols
- [ ] support aliases

---

# Phase 4 - Add Export Analysis

Goal:
- enable real cross-file symbol resolution

Status: NOT STARTED

## Task 4.1 - Create export entity/model

Suggested files:
- `models/entities/exports.py`
- `analysis/export_extractor.py`
- `analysis/passes/export_pass.py`

Need to support:
- named exports
- default exports
- re-exports later

Checklist:
- [ ] Add export entity
- [ ] Extract exports from TS/JS
- [ ] Store export index per document

---

## Task 4.2 - Resolve imports to exported symbols

Steps:
1. For each import reference, find target document.
2. Look up export table in target document.
3. Resolve imported name to symbol.
4. Store resolved import symbol mapping.

Checklist:
- [ ] Resolve named imports
- [ ] Resolve default imports
- [ ] Resolve alias imports
- [ ] Handle namespace imports at least minimally

---

# Phase 5 - SQLite Local Persistence

Goal:
- persist graph/index fully on device

Status: NOT STARTED

## Storage decision

Use:
- SQLite for metadata and graph
- SQLite FTS5 for lexical search
- local SQLite vector extension for embeddings

Do NOT add a separate graph DB yet.

---

## Task 5.1 - Create schema

Suggested file:
- `schema.sql`

Tables:
- `documents`
- `symbols`
- `imports`
- `exports`
- `references`
- `relationships`
- `chunks`
- `embeddings`
- `file_state`
- optional `symbol_lineage`

Suggested minimal schema fields:

### documents
- id
- absolute_path
- relative_path
- language
- file_hash
- size_bytes
- line_count
- updated_at

### symbols
- id
- document_id
- stable_key
- name
- qualified_name
- kind
- parent_symbol_id
- start_line
- end_line
- start_byte
- end_byte
- content_hash
- signature_hash

### imports
- id
- document_id
- module_path
- imported_name
- local_name
- resolved_document_id
- resolved_symbol_id

### references
- id
- document_id
- owner_symbol_id
- name
- kind
- start_line
- start_byte
- resolved_symbol_id

### relationships
- id
- source_symbol_id
- target_symbol_id
- kind

### chunks
- id
- symbol_id
- relative_path
- chunk_text
- chunk_hash

### embeddings
- chunk_id
- embedding

### file_state
- relative_path
- file_hash
- last_indexed_at

Checklist:
- [ ] Write schema.sql
- [ ] Add indexes on lookup columns
- [ ] Add migration/init code

---

## Task 5.2 - Create persistence layer

Suggested folder:
- `storage/`

Suggested files:
- `storage/db.py`
- `storage/repositories/...`

Checklist:
- [ ] DB connection helper
- [ ] WAL mode
- [ ] transaction wrapper
- [ ] repository methods for documents/symbols/etc.

Suggested code comment:
```py
# TODO: Keep graph edges in SQLite tables first. Do not introduce a graph database
# unless relational traversal becomes a proven bottleneck.
```

---

# Phase 6 - Incremental Indexing

Goal:
- support frequent edits without full rebuild

Status: NOT STARTED

## Task 6.1 - Add file hashing

Steps:
1. Compute hash for each file content during load.
2. Compare against `file_state`.
3. Skip unchanged files.

Checklist:
- [ ] Add file hash generation
- [ ] Store in file_state
- [ ] Detect changed/new/deleted files

---

## Task 6.2 - Reindex only changed files

Behavior:
- unchanged files: keep rows
- changed files: delete old rows for that file, then rebuild
- deleted files: remove related rows

Checklist:
- [ ] Delete stale rows by document/file
- [ ] Rebuild graph edges for affected files
- [ ] Rebuild chunks/embeddings only for changed files

Suggested code comment:
```py
# TODO: Indexing must be file-incremental. Never rebuild the entire repository when
# only one file changed.
```

---

## Task 6.3 - Add stable symbol identity / lineage

Problem:
- filenames and function names change frequently
- UUID alone is not enough across reindex runs

Need:
- stable matching heuristics between old/new symbols

Suggested symbol identity fields:
- `stable_key`
- `qualified_name`
- `content_hash`
- `signature_hash`
- parent scope chain

Matching order:
1. exact stable key
2. exact signature/body hash
3. same parent + similar signature
4. same content at moved path

Checklist:
- [ ] Design stable key format
- [ ] Store symbol lineage info
- [ ] Preserve identity across rename/move when confidence is high

Suggested code comment:
```py
# TODO: Symbol identity must survive common edits like file rename, symbol rename,
# or function movement when code content remains mostly the same.
```

---

# Phase 7 - Chunking and Embeddings

Goal:
- add semantic retrieval after correctness + persistence exist

Status: NOT STARTED

## Task 7.1 - Keep symbol-centered chunking

Do not chunk full files first.

Chunk should contain:
- symbol kind/name
- qualified name
- file path
- source code
- callers/callees
- imports/exports later
- parent class/module context

Checklist:
- [ ] Review `chunking/symbol_chunker.py`
- [ ] Add richer chunk metadata
- [ ] Ensure chunk IDs are stable enough for incremental updates

---

## Task 7.2 - Add local embedding model

Requirements:
- fully local
- no cloud API

Steps:
1. Choose local embedding model.
2. Embed only changed/new chunks.
3. Store vectors in local SQLite vector storage.

Checklist:
- [ ] Choose local embedding model
- [ ] Add embedding pipeline
- [ ] Store vectors locally

Note:
- do not prioritize model tuning before retrieval plumbing exists

---

# Phase 8 - Hybrid Retrieval

Goal:
- combine precision and recall

Status: NOT STARTED

Retrieval order:
1. exact symbol lookup
2. graph traversal
3. lexical / FTS search
4. vector search
5. merge candidates
6. rerank

---

## Task 8.1 - Add lexical search with SQLite FTS5

Checklist:
- [ ] Create FTS table for chunk text / symbol text
- [ ] Add query method
- [ ] return scored candidates

---

## Task 8.2 - Improve graph-aware retriever

Files:
- `retrieval/hybrid_retriever.py`
- `graph/code_graph.py`

Need query routing for:
- where defined
- who calls
- who is called by
- symbol lookup
- semantic concept search

Checklist:
- [ ] Keep graph routes for structural queries
- [ ] Use vector only for semantic meaning queries

---

## Task 8.3 - Candidate merge strategy

Start simple.

Use weighted merge or reciprocal rank fusion from:
- exact match candidates
- FTS candidates
- vector candidates
- graph-expanded candidates

Checklist:
- [ ] Merge candidate lists
- [ ] keep provenance/source score info

---

# Phase 9 - Reranking

Goal:
- improve top-k quality for code questions

Status: NOT STARTED

## Task 9.1 - Start with heuristic reranking

Scoring features:
- exact symbol name match
- query/path token overlap
- symbol kind relevance
- graph distance to seed node
- vector similarity score
- FTS score

Examples:
- `where is X defined` -> prioritize declaration symbols
- `who calls X` -> prioritize caller relationships
- `auth flow` -> prioritize graph-connected auth-related symbols

Checklist:
- [ ] Design score formula
- [ ] Implement reranker over merged candidates
- [ ] add tests/examples for query types

Suggested code comment:
```py
# TODO: Reranking should prefer structurally correct code entities before broad
# semantic similarity.
```

---

## Task 9.2 - Add local model reranker later

Only after heuristic reranker works.

Use for top 20-50 results only.

Input features can include:
- query
- symbol signature
- chunk text
- file path
- graph summary

Checklist:
- [ ] Select local reranker model
- [ ] run on small candidate set only

---

# Phase 10 - Context Builder

Goal:
- produce minimal, useful context for an LLM

Status: NOT STARTED

For each top result gather:
- symbol definition
- direct callers/callees
- related imports/exports
- parent class/module
- a few nearby supporting symbols

Do not dump whole files by default.

Checklist:
- [ ] Build context packer
- [ ] deduplicate overlapping symbols
- [ ] cap token/line budget

---

# Phase 11 - Evaluation

Goal:
- measure quality before claiming production grade

Status: NOT STARTED

## Task 11.1 - Add test repos / fixtures

Use small controlled repos first.

Question classes:
- where is X defined
- who calls X
- what does X import
- what exports X
- cross-file call chain
- semantic search like “auth logic”

Checklist:
- [ ] add fixtures
- [ ] add expected answers

---

## Task 11.2 - Add metrics

Metrics:
- definition lookup accuracy
- call edge accuracy
- import/export resolution accuracy
- retrieval recall@k
- MRR / ranking quality
- indexing latency
- incremental update latency

Checklist:
- [ ] evaluation script
- [ ] baseline results table in this file

---

# Suggested Immediate Execution Order

If implementing now, do tasks in exactly this order:

1. Task 0.1 - fix double document loading
2. Task 0.2 - fix CLI location bug
3. Task 0.3 - align language support
4. Task 0.4 - verify variable AST mapping
5. Task 1.1 - add ParsedDocument
6. Task 2.1 - add import pass
7. Task 2.2 - run import resolver in pipeline
8. Task 2.3 - test imports
9. Task 3.1 - replace naive resolver
10. Task 4.1 - export extraction
11. Task 4.2 - import-to-symbol resolution
12. Phase 5 - SQLite persistence
13. Phase 6 - incremental indexing
14. Phase 7 - embeddings
15. Phase 8 - hybrid retrieval
16. Phase 9 - reranking
17. Phase 10 - context builder
18. Phase 11 - evaluation

---

# What NOT To Do Yet

Do not do these before Phase 3/4 are solid:
- multi-language support
- remote vector DB
- cloud embeddings
- IDE integration
- agent workflow orchestration
- aggressive context compression
- fancy UI

---

# Update Log

Use this section to track progress.

## Completed
- [x] Task 0.1 - Fix double document loading (already correct, verified)
- [x] Task 0.2 - Fix CLI symbol location bug
- [x] Task 0.3 - Align language support with parser support
- [x] Task 0.4 - Verify AST node types for variables (8 tests written and passing)

## In Progress
- [ ] None yet

## Blocked
- [ ] None yet

---

# Per-Task Notes Template

Copy this block under a task when working on it.

```md
### Work Notes
- Owner:
- Date:
- Files changed:
- Summary:
- Risks:
- Follow-up TODOs:
```

---

# Definition of v1 Done

v1 is done when all of these are true:

- TS/JS code indexing works reliably
- documents are parsed once via ParsedDocument
- symbols/imports/exports/references are extracted
- cross-file symbol resolution works for common cases
- call graph is mostly correct on test fixtures
- graph is stored locally in SQLite
- chunk + embedding storage is local
- incremental reindex works for changed files
- hybrid retrieval works locally
- reranking improves top-k results
- evaluation exists and is repeatable

---

# Final Reminder

This project should be built with this priority:

1. semantic correctness
2. local persistence
3. incremental updates
4. retrieval quality
5. reranking quality
6. LLM context generation

Graph gives precision.
Embeddings give recall.
Reranking gives relevance.
Incremental indexing gives usability.
