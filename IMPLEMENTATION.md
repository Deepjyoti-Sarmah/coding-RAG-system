# Production Codebase RAG / Code Intelligence Implementation Plan

> This file is the execution specification for turning CKG into a production-grade, local-first code intelligence and RAG system.
>
> It is intentionally written for both a junior engineer and an implementation agent such as Codex:
>
> - one task at a time
> - small changes
> - tests before moving forward
> - no speculative abstractions
> - design can change when implementation evidence shows the current approach is wrong

---

# 0. North Star

The system should eventually look like:

```text
Repository
    ↓
File Scanner + Ignore Rules
    ↓
Change Detection / Hashing
    ↓
ParsedDocument IR
    ↓
Semantic Compiler
    ├── Symbols
    ├── Imports
    ├── Exports
    ├── References
    ├── Resolution
    └── Relationships
    ↓
Code Knowledge Graph
    ↓
Semantic Chunk Builder
    ↓
Content-Addressed Chunk Cache
    ↓
Local Embeddings
    ↓
SQLite + FTS5 + Local Vector Store
    ↓
Hybrid Retrieval
    ├── Exact
    ├── FTS
    ├── Vector
    └── Graph Expansion
    ↓
Reranking
    ↓
Context Builder
    ↓
Coding Agent / LLM
```

The central rule is:

> **Source code is the source of truth. Everything else is derived state.**

---

# 1. Engineering Rules

These rules apply to every task.

## 1.1 Correctness before optimization

Do not optimize:

- embeddings
- vector search
- graph storage
- incremental indexing

until the semantic model is sufficiently correct for the feature being optimized.

---

## 1.2 One responsibility per module

Prefer:

```text
extractor
builder
resolver
pass
index
store
retriever
```

Do not create a 500-line "manager" that performs several unrelated jobs.

---

## 1.3 Inspect the AST before implementing syntax handling

For any new TypeScript/JavaScript syntax:

1. create a tiny fixture
2. print the Tree-sitter AST
3. identify actual node types/fields
4. write the handler
5. add a regression test

Never guess Tree-sitter node names.

---

## 1.4 No "first match" semantic resolution

Never do:

```python
targets = symbol_index.lookup_by_name(name)
return targets[0]
```

unless the code has already established that the candidate set is unambiguous.

Ambiguity should be represented and tested.

---

## 1.5 Do not add an abstraction without a concrete second use

Before introducing a registry/base class/framework, ask:

> Do we already have a second implementation that benefits from this abstraction?

Prefer the simplest design that supports the current feature.

---

## 1.6 Every production change needs a test

For every behavior change, add at least one regression test.

For core semantic logic, prefer:

```text
fixture source
    ↓
build/index
    ↓
assert semantic result
```

over tests that only mock internal functions.

---

## 1.7 Keep implementation deterministic

Given the same repository state:

```text
same files
same configuration
same parser version
```

the semantic index should produce the same semantic facts.

Do not use random UUIDs as the only long-term identity mechanism.

---

## 1.8 Update this file after every completed task

Each completed task must update:

```text
Status
Checklist
Tests
Decision notes
```

Do not mark a task complete because the code "looks right".

---

# 2. Current Architecture

Current semantic architecture:

```text
Documents
    ↓
Parse
    ↓
Symbols
    ↓
References
    ↓
Resolved References
    ↓
Relationships
    ↓
CodeGraph
```

Import pipeline (Phase 2 complete):

```text
ImportReference
    ↓
ResolvedImportReference
    ├── Target Document
    └── Target Symbol (via Export Table)
```

Target architecture:

```text
ParsedDocument
    ├── Symbol Pass
    ├── Import Pass
    ├── Export Pass
    └── Reference Pass

Semantic Artifacts
    ↓
Resolution
    ↓
Relationships
    ↓
Knowledge Graph
```

---

# 3. Current Project Rules

## Supported language for v1

Support only:

```text
.ts
.tsx
.js
.jsx
```

Do not advertise Python/Markdown semantic indexing until parsing and semantic passes actually exist.

---

# 4. Testing Strategy

Create a real test suite before adding persistence.

Recommended structure:

```text
tests/
├── fixtures/
│   ├── basic/
│   ├── imports/
│   ├── scopes/
│   ├── exports/
│   ├── incremental/
│   └── retrieval/
├── analysis/
├── indexing/
├── storage/
├── retrieval/
└── integration/
```

Use three levels of tests.

## Level 1 — Unit tests

Test one function:

```text
get_module_path()
resolve_symbol()
build_reference()
```

Use when behavior is local and deterministic.

## Level 2 — Semantic fixture tests

Use a tiny repository:

```text
fixture/
├── auth.ts
└── api.ts
```

Build the semantic index and assert:

```text
symbols
imports
resolutions
relationships
```

This should be the main test style for compiler behavior.

## Level 3 — Integration tests

Test:

```text
repository
    ↓
index
    ↓
SQLite
    ↓
retrieval
```

Use only after the individual layers are stable.

---

# 5. Test Conventions

Prefer explicit expected facts.

Example:

```python
assert symbol_names == {
    "createAuth",
    "login",
    "logout",
}
```

For relationships:

```python
assert relationships == {
    ("login", "createAuth", "calls"),
    ("login", "logout", "calls"),
}
```

Do not assert UUID values.

Prefer stable semantic identifiers.

---

# 6. Phase 0 — Repository Stabilization

Status: COMPLETE

Goal:

```text
existing code is internally consistent
```

Required outcomes:

- single document load
- correct location access
- language support matches parser support
- variable AST mapping verified
- current semantic tests pass

Do not reopen Phase 0 unless a regression is discovered.

---

# 7. Phase 1 — ParsedDocument IR

Status: COMPLETE

Goal:

> Parse each document once and reuse the same tree for all syntax-based passes.

## Task 1.1 — Create ParsedDocument

File:

```text
models/parsed_document.py
```

Suggested model:

```python
from dataclasses import dataclass

from tree_sitter import Tree

from models.entities.document import Document


@dataclass(slots=True)
class ParsedDocument:
    document: Document
    tree: Tree
    file_hash: str
```

Notes:

- keep it small
- do not add parser metadata unless a real consumer needs it
- file hash can temporarily be computed by the scanner/loader layer

### Tests

Create a fixture with one `.ts` file.

Assert:

- one `Document`
- one `ParsedDocument`
- the tree root is valid
- file hash is deterministic

### Done when

No semantic pass reparses a `Document`.

---

## Task 1.2 — Parse Pass

Create:

```text
analysis/passes/parse_pass.py
```

Responsibility:

```text
Document → ParsedDocument
```

It must not:

- extract symbols
- extract imports
- modify the graph
- build embeddings

### Tests

Assert:

- supported language gets parsed
- unsupported language is skipped cleanly
- parse errors are represented without crashing the entire repository build

### Decision gate

If parsing errors can only be handled by changing the parser API, stop and redesign the parse result before implementing later passes.

---

## Task 1.3 — Update IndexingContext

Add:

```text
parsed_documents
```

Do not remove:

```text
extracted_symbols
```

yet if the existing symbol pipeline still depends on it.

Migrate one pass at a time.

---

# 8. Phase 2 — Import Pipeline

Status: COMPLETE

Goal:

```text
import syntax
    ↓
ImportReference
    ↓
ResolvedImportReference
    ↓
Exported Symbol
```

## Task 2.1 — Import Pass

Status: COMPLETE

Create:

```text
analysis/passes/import_pass.py
```

Input:

```text
ParsedDocument
```

Output:

```text
BuildResult.import_references
```

Tests:

- named imports
- multiple named imports
- aliases
- default imports
- namespace imports
- mixed imports

Use the AST fixtures already created during development.

### Done when

`build_graph()` contains import references produced by the actual pipeline.

---

## Task 2.2 — Import Module Resolver

Status: COMPLETE

Current behavior already resolves:

```text
"./auth" → auth.ts
```

Do not expand path resolution too aggressively yet.

First support:

```text
./file
../file
./file.ts
./file.tsx
./file.js
./file.jsx
./directory/index.ts
```

### Tests

For each fixture:

```text
source import
expected target document
```

### Done when

All supported module paths resolve deterministically.

---

## Task 2.3 — Export Model

Status: COMPLETE

Create an export entity based on actual AST behavior.

Before implementation:

1. create export fixture
2. print AST
3. identify node types
4. implement handlers
5. add tests

Initial support:

```text
export function
export const
export default
export { name }
export { name as alias }
```

Defer:

```text
export * from
```

until named/default exports are correct.

### Implemented

- `models/entities/exports.py` — `Export(document_id, exported_name, symbol_name, location)`.
- `indexing/export_index.py` — `(document_id, exported_name) → exports` lookup.
- `analysis/export_extractor.py` + `analysis/export_registry.py` + `analysis/export_handlers/` + `analysis/export_builder.py` — node-type-keyed handlers matching the import pipeline pattern.
- `analysis/passes/export_pass.py` — `run_export_pass` wired into `build_graph` after the import pass.
- `export { a } from "./x"` and `export * from "./x"` are skipped (deferred re-exports).

## Task 2.4 — Resolve Imported Symbol

Status: COMPLETE

Change:

```text
ImportReference → Document
```

into:

```text
ImportReference
    ↓
Target Document
    ↓
Export Table
    ↓
Target Symbol
```

Add a model only if the existing `ResolvedImportReference` cannot represent the result cleanly.

Do not create duplicate models for the same concept.

### Implemented

- Extended `ResolvedImportReference` with `target_symbol: Symbol | None` instead of introducing a duplicate model.
- `analysis/semantic/import_symbol_resolver.py` — `resolve_imported_symbol` resolves the imported name via the target document's export table, then looks up the module-scope symbol by `symbol_name`. Returns `None` (never guesses) for namespace imports, missing exports, anonymous defaults, and ambiguous/duplicate exports.
- `analysis/passes/import_resolver_pass.py` populates `target_symbol` on every resolved import.

### Required tests

Given:

```text
auth.ts
    export function login()

api.ts
    import { login as authLogin } from "./auth"
```

assert:

```text
authLogin → auth.ts::login
```

Also test:

- default import
- alias import
- namespace import
- unresolved import
- missing export

---

# 9. Phase 3 — Semantic Name Resolution

Status: COMPLETE

Goal:

> Resolve references using scope and module information instead of name-only lookup.

Resolution order:

```text
current lexical scope
    ↓
parent scope
    ↓
module scope
    ↓
imports
    ↓
unresolved
```

## Task 3.1 — Scope Resolution

Use the existing:

```text
Symbol.parent_symbol_id
SymbolIndex.children_by_parent
```

Do not build a new scope system unless the existing parent chain becomes insufficient.

### Tests

Test:

```ts
function outer() {
  function inner() {
    login();
  }
}
```

and verify the resolver climbs:

```text
inner → outer → module
```

---

## Task 3.2 — Shadowing

Fixture:

```ts
const login = globalLogin;

function outer() {
  const login = localLogin;
  login();
}
```

Expected:

```text
login() → local login
```

not the global one.

This test is mandatory before claiming scope resolution works.

---

## Task 3.3 — Unresolved References

Do not silently guess.

Represent:

```text
resolved
unresolved
ambiguous
```

If changing `ResolvedReference` is required, prefer a status/result model over creating multiple nearly identical entities.

### Decision gate

If one `Symbol` cannot adequately represent a scope/module identity, stop and redesign symbol identity before adding more language features.

---

# 10. Phase 4 — Member Expressions

Status: COMPLETE

Current problem:

```ts
auth.createAuth();
auth.client.createAuth();
```

Current reference extraction can see:

```text
auth
createAuth
auth
client
createAuth
```

That is insufficient.

Target semantic representation:

```text
auth.createAuth
auth.client.createAuth
```

## Task 4.1 — Inspect AST

Create fixtures for:

```text
obj.method()
obj.a.b.method()
this.method()
Class.staticMethod()
```

Inspect AST before coding.

---

## Task 4.2 — Introduce semantic access path only if needed

Possible representation:

```text
Reference
    name
    kind
    path
```

Example:

```text
path = ["auth", "client", "createAuth"]
```

Do not add both:

```text
name
full_name
path
qualified_name
```

unless each has a distinct consumer.

### Done when

Member calls can be represented without returning to raw AST in later semantic passes.

### Implemented

- `Reference` gained `path: tuple[str, ...]`. `name` stays the property name (last path element); `path` is the single semantic access-path representation. Plain identifiers use `path = (name,)`.
- `analysis/reference_extractor.py` represents a `member_expression` atomically: one reference per access with the full dotted path, and the object/property parts are not emitted as separate references.
- `analysis/semantic/reference_kind.py` returns `CALL` for a called member expression and the existing `MEMBER_ACCESS` for a non-call member access.
- `analysis/semantic/member_resolver.py` — `resolve_member_reference` resolves:
  1. `len(path) > 2` → `UNRESOLVED` (intermediate members unverifiable without types).
  2. `this.<member>` → the owner's enclosing class scope.
  3. `<namespace import>.<member>` → exported symbol in the target document (via the export table).
  4. `<class>.<member>` → class child symbol.
- `analysis/semantic/import_symbol_resolver.py` extracted `resolve_exported_symbol`, reused by both the import resolver and the member resolver.
- `run_reference_resolver_pass` dispatches member references to the member resolver.

### Regression fixed

`auth.createAuth()` previously emitted `auth` and `createAuth` as separate references, and the `createAuth` property falsely resolved to module scope. Member expressions now resolve only through the access path; a member property never falls back to plain name lookup.

---

# 11. Phase 5 — Knowledge Graph Stabilization

Status: COMPLETE

Goal:

> Make the in-memory graph a clean, deterministic semantic representation before persistence.

## Task 5.1 — Graph API

Keep:

```text
symbols
relationships
incoming
outgoing
```

Expose semantic operations:

```text
callers_of()
callees_of()
children_of()
parents_of()
```

Avoid leaking internal dictionaries to callers.

### Implemented

- `CodeGraph` now exposes `symbols()` and `relationships()`, both returning immutable `tuple`s so callers cannot mutate internal state.
- Added `children_of()` (via a `_children_by_parent` map populated in `add_symbols`) and `parents_of()` (immediate parent lookup via `_symbols_by_id`).
- `callers_of()` / `callees_of()` unchanged; they stay duplicate-free as a side effect of relationship deduplication.

## Task 5.2 — Relationship Deduplication

A relationship should not appear multiple times because the extractor visited equivalent syntax paths.

Add a stable relationship key:

```text
(source_id, target_id, kind)
```

Use a set internally or deduplicate before storage.

### Test

Repeated references:

```ts
login();
login();
```

should produce:

```text
two references
one unique CALLS edge
```

if the graph models a relationship rather than individual occurrences.

If occurrence counts become useful later, model occurrences separately instead of duplicating edges.

### Implemented

- `Relationship` gained a `key` property returning `(source_symbol_id, target_symbol_id, kind)`.
- `CodeGraph.add_relationships` skips any relationship whose key is already present (internal `_relationship_keys` set). `BuildResult.relationships` stays the raw per-occurrence list; the graph is the deduplicated semantic view.

---

# 12. Phase 6 — Stable Identity

Status: COMPLETE

Current UUIDs are acceptable for in-memory entities.

They are not enough for long-term persistence.

## Task 6.1 — Separate Entity Identity From Source Identity

Keep:

```text
symbol_id
```

as an internal ID if useful.

Add a stable semantic key for matching across index runs.

Candidate inputs:

```text
document relative path
language
parent qualified name
symbol kind
symbol name
signature
```

Do not assume one key will survive every rename/move.

### Implemented

- `Symbol` keeps `symbol_id` (UUID) as the internal entity identity and gains `qualified_name` and `stable_key` as the source identity.
- `qualified_name` is derived from the extraction-time owner chain (e.g. `login`, `AuthService.validateUser`, `outer.inner`).
- `stable_key = "{relative_path}|{language}|{qualified_name}|{kind.value}"` via `analysis/fingerprints.py:build_stable_key`, deterministic across index runs.
- `document_id` remains a UUID; `relative_path` on `Document` serves as the stable document identity (no loader change).

---

## Task 6.2 — Symbol Fingerprints

Compute:

```text
content_hash
signature_hash
```

Use these for matching and change detection.

Do not use body hash as the permanent identity because a function can change while remaining the same symbol.

### Implemented

- `Symbol.content_hash` = SHA-256 of the symbol's source text (change detection).
- `Symbol.signature_hash` = SHA-256 of a **name-independent, body-excluding** signature via `analysis/signature.py:extract_signature`:
  - FUNCTION/METHOD: `function({param types})[:{return type}]` — parameter names and bodies are excluded so renames/body edits preserve the signature; untyped parameters contribute nothing.
  - CLASS: `class[:{extends text}]`.
  - VARIABLE: `variable:{type annotation}` else `variable:<{value node type}>`.
- Hash helpers live in `analysis/fingerprints.py`; both are computed once inside `analysis/symbol_builder.py:build_symbol`.

---

## Task 6.3 — Rename / Move Matching

Implement confidence-based matching:

```text
1. exact stable key
2. same scope + signature
3. same signature + similar source
4. same content hash at new path
```

If confidence is low:

```text
do not guess
create new identity
```

This is critical for production correctness.

### Implemented

- `analysis/symbol_matching.py` exposes `match_symbols(old_symbols, new_symbols) -> list[SymbolMatch]` with `SymbolMatch(old_symbol, new_symbol, confidence)` and `MatchConfidence {HIGH, MEDIUM}`.
- Matching ladder:
  1. exact `stable_key` → HIGH.
  2. same scope (relative_path + parent qualified name) + `signature_hash` → MEDIUM (handles rename).
  3. same `content_hash` at a different path → MEDIUM (handles move with unchanged content).
  4. "same signature + similar source" is recognized as LOW confidence and intentionally never matched → new identity (no guessing, Gate E).
- Every match requires a unique unclaimed old candidate; duplicate/ambiguous candidates produce no match.

---

# 13. Phase 7 — SQLite Persistence

Status: COMPLETE

Goal:

```text
in-memory graph
+
persistent local index
```

SQLite is the first storage choice.

Do not introduce Neo4j/Postgres unless profiling proves SQLite is insufficient.

---

## Task 7.1 — Storage Schema

Status: COMPLETE

Suggested tables:

```text
documents
symbols
imports
exports
references
relationships
chunks
embeddings
file_state
index_metadata
```

Add primary and foreign keys.

Add indexes for actual query patterns.

Do not create ten indexes "just in case".

### Implemented

- `storage/schema.py` — `SCHEMA_VERSION = 1`, `TABLES`, `INDEXES`, `create_schema`, `schema_version`, `set_schema_version`. All 10 suggested tables plus a `resolved_references` and `resolved_imports` table (BuildResult carries resolution data that `load_index` must reconstruct).
- Tables have primary keys and `ON DELETE CASCADE` foreign keys. `references` is a SQLite keyword, so it is always written as `"references"`.
- `SourceLocation` is flattened into four `INTEGER` columns (`start_line/end_line/start_byte/end_byte`) on every located entity; `Reference.path` is stored as JSON text; enums are stored as their `.value` string.
- Indexes only for real query patterns: `documents(relative_path)` UNIQUE, `symbols(document_id)`, `symbols(stable_key)`, `relationships(source, target, kind)` UNIQUE.
- `chunks`, `embeddings`, and `file_state` tables are created now but have no writers until Phases 8/10/11 (rule 1.5).

---

## Task 7.2 — Database Layer

Status: COMPLETE

Create:

```text
storage/
├── db.py
├── schema.py
└── repositories/
```

Responsibilities:

```text
db.py
    connection / pragmas / transactions

schema.py
    schema creation / migration

repositories/
    typed persistence operations
```

Do not put SQL directly into retrieval or compiler passes.

### Implemented

- `storage/db.py` — `connect(db_path)` (autocommit, `sqlite3.Row`, WAL, `foreign_keys=ON`, `busy_timeout=5000`) and a `transaction(conn)` context manager (commit on success, rollback on any exception).
- `storage/repositories/` — one module per entity, mirroring the `import_handlers/`/`export_handlers/` pattern: `document_repository.py`, `symbol_repository.py`, `import_repository.py`, `export_repository.py`, `reference_repository.py`, `resolved_reference_repository.py`, `resolved_import_repository.py`, `relationship_repository.py`. Each exposes `insert_many(conn, entities)` and `fetch_all(conn)`.
- `import_repository.insert_many` returns a `{id(import_reference): import_id}` map so `resolved_import_repository` can link resolution rows (import rows use `INTEGER PRIMARY KEY AUTOINCREMENT`; raw import/export/reference-occurrence rows carry no in-memory id).
- `storage/_rows.py` — shared `location_columns` / `source_location_from_row` helpers (functions, no base class; rule 1.5).

---

## Task 7.3 — Transactions

Status: COMPLETE

A repository update should be atomic:

```text
begin
    update affected documents
    update symbols
    update references
    update relationships
    update chunks
    update embeddings
commit
```

On failure:

```text
rollback
```

Never expose a partially indexed repository.

### SQLite pragmas

Evaluate:

```text
WAL
foreign_keys
busy_timeout
```

Use only after testing behavior.

### Implemented

- `storage/index_store.py` — `persist_index(db_path, result)` opens one connection, creates the schema, then performs a full snapshot replace inside a single `db.transaction`: clear all tables (FK-safe dependency order) and re-insert documents → symbols → imports → exports → references → resolved references → resolved imports → relationships.
- Relationships are persisted from `result.graph.relationships()` (the deduplicated semantic view); the `relationships` unique index makes re-persists idempotent (`ON CONFLICT DO NOTHING`).
- On any failure the whole transaction rolls back; a partially indexed repository is never visible (verified by forcing a foreign-key violation mid-insert and asserting every data table is empty).
- `documents.file_hash` is derived at persist time via `analysis/fingerprints.py:compute_content_hash`; the `Document` model is unchanged.
- `load_index(db_path)` reconstructs a `BuildResult`: documents, symbols, imports, exports, references, resolved references, resolved imports, relationships; rebuilds `SymbolIndex`, and rebuilds `CodeGraph` via `add_symbols`/`add_relationships` (the graph stays derived state — no graph table).
- WAL, `foreign_keys`, and `busy_timeout` are all enabled and covered by tests.

---

# 14. Phase 8 — Incremental Indexing

Status: COMPLETE

Goal:

> Reindex only the affected part of the repository.

## Task 8.1 — File State

Track:

```text
relative_path
file_hash
size
mtime
last_indexed_at
```

Hash is the correctness signal.

mtime is only a cheap change hint.

### Implemented

- `storage/repositories/file_state_repository.py` — upsert + `fetch_all` for the existing `file_state` table.
- `storage/index_store.persist_index(..., file_states=None)` writes the inventory in the same transaction; `load_file_states(db_path)` reads it back (creating the schema if needed).
- `FileState` (`models/file_state.py`) was already in place from Phase 7.

---

## Task 8.2 — Change Detection

Classify:

```text
NEW
CHANGED
UNCHANGED
DELETED
```

Do not reparse unchanged files.

### Tests

Fixture:

```text
a.ts
b.ts
```

Run index twice.

Expected second run:

```text
a.ts unchanged
b.ts unchanged
zero semantic rebuilds
zero new embeddings
```

### Implemented

- `indexing/diff.py:scan_files` classifies every repo file against the previous `file_state` inventory.
- Fast path: stored `mtime_ns` + `size_bytes` match → `UNCHANGED` without reading the file (cheap hint). Otherwise the file is read, hashed, and compared (correctness signal) — so a pure `touch` is still `UNCHANGED`.
- `FileChange` enum: `NEW` / `CHANGED` / `UNCHANGED` / `DELETED`.
- Tests cover the exact `a.ts` / `b.ts` fixture: the second run reports both `UNCHANGED`, `parsed_files == 0`, `resolved_references == 0`, `new_embeddings == 0`.

---

## Task 8.3 — Dependency Invalidation

If:

```text
a.ts imports b.ts
```

and `b.ts` changes its exported symbol set, affected semantic data in `a.ts` may need re-resolution.

Therefore change propagation must distinguish:

```text
file content changed
```

from:

```text
public semantic interface changed
```

Do not invalidate the entire repository for every edit.

### Implemented

- `indexing/diff.py:interface_fingerprint` = sorted `(exported_name, signature_hash)` tuples per file — the public semantic interface.
- `indexing/diff.py:importers_of` resolves each import to repo-relative candidate paths (reusing `resolve_module_path`) and maps module → importing document ids.
- `indexing/indexer.py:reindex_index(db_path, root_dir) -> IndexRunReport`:
  - No previous `file_state` inventory → falls back to a full `build_graph` + `persist_index`.
  - `REBUILD` set = `NEW` ∪ `CHANGED` (re-extracted through the existing passes; `run_parse_pass` gained an optional `documents` filter).
  - `RE-RESOLVE` set = importers of interface-changed or deleted files; untouched files are reused verbatim (documents/symbols/imports/exports/references/resolutions all carried from the stored index).
  - Symbol identity reconciled via Phase 6 `match_symbols` so edited symbols keep their `symbol_id` and cross-file references stay valid without re-resolving untouched files.
  - Imports/references are only re-resolved for the affected set, then merged back before the snapshot persist.
  - Report exposes per-path `changes`, `parsed_files`, `resolved_references`, `new_embeddings` (0 until Phase 11).
- Tests: body edit keeps importer resolved without re-resolution; export rename/signature change re-resolves the importer to `UNRESOLVED`; deletion removes symbols and invalidates importers; identity preserved across edits.

---

# 15. Phase 9 — Hierarchical / Merkle Hashing

Status: COMPLETE

Goal:

> Detect unchanged subtrees cheaply.

Structure:

```text
repo
├── src
│   ├── auth.ts
│   └── api.ts
└── package.json
```

Hashes:

```text
auth_hash
api_hash
    ↓
src_hash

src_hash
package_hash
    ↓
repo_hash
```

## Rules

- use deterministic ordering
- hash normalized child names + child hashes
- never hash random IDs
- changing one leaf should change only its ancestor hashes

### Implemented

- `indexing/merkle.py` — `NodeKind` (`FILE` / `DIRECTORY`), `MerkleNode(relative_path, kind, hash)`, `MerkleTree(nodes)` (`node_hash(path)`, `root_hash`), and `compute_merkle_tree(root_dir)`.
- File leaves hash their content via the existing `analysis/fingerprints.py:compute_content_hash`; directories/root hash children sorted by basename, encoded as `name\0child_hash\0` (no mtime/size/random IDs). `EXCLUDE_DIRS` are skipped via `is_inside_excluded_dir`; unreadable files are skipped cleanly like `scan_files`. Single-file roots produce a single `FILE` node.
- Deliberately no persistence or indexer wiring (rule 1.5): later phases (content-addressed chunk cache, content proofs) are the consumers.

### Tests

Change one file.

Assert:

```text
changed file hash ≠ old hash
affected directory hash ≠ old hash
unrelated directory hash == old hash
```

Additionally:

```text
file leaf hash == compute_content_hash(content)
directory nodes are DIRECTORY kind
tree hash is deterministic across two runs
adding a file changes only its ancestors
deleting a file changes only its ancestors
hash is independent of file creation order
single-file root hashes its content
```

---

# 16. Phase 10 — Semantic Chunking

Status: COMPLETE

Goal:

> Convert graph entities into retrieval units.

Default chunk unit:

```text
symbol-centered semantic chunk
```

Include only information that has proven retrieval value.

Initial fields:

```text
symbol kind
qualified name
file path
source
parent context
calls
called_by
imports
exports
```

Do not add the entire N-hop graph by default.

---

## Task 10.1 — Stable Chunk Identity

Chunk ID should not depend only on a random symbol UUID.

Prefer a stable identity plus content hash:

```text
chunk_key
chunk_version_hash
```

This makes embedding reuse possible.

### Implemented

- `chunking/symbol_chunker.py` — `SemanticChunk` now carries `chunk_key` (== `symbol.stable_key`, never a UUID), `symbol_id`, `relative_path`, `embedding_text`, `display_text`, `content_hash` (SHA-256 of `embedding_text` via the existing `compute_content_hash`), and a constant `chunk_version = "v1"`. The UUID-derived `chunk_id` field is gone.
- `build_semantic_chunk(symbol, graph, *, document_imports, exports)` builds the embedding text from all spec fields: `kind name`, `qualified name`, `file`, `parent` (via `graph.parents_of` → parent qualified name), `calls` (callees), `called by` (callers), `imports` (the symbol's document, sorted, formatted `import { imported_name } from "module_path"`), `exports` (only this symbol's aliases, sorted, with `symbol as alias` when renamed), then `source`. Empty relations render as `none`.
- `build_semantic_chunks(result)` — one chunk per symbol, grouping imports/exports by `document_id`.

---

## Task 10.2 — Chunk Tests

Given a fixture:

```text
login → createAuth
login ← api.login
```

assert the chunk contains the intended graph facts and excludes unrelated symbols.

### Implemented

- `tests/test_semantic_chunking.py` — fixture `auth.ts` (login calls createAuth), `api.ts` (run calls imported login), `util.ts` (unrelated format).
  - Task 10.2: login's chunk embeds `qualified name`, `file: auth.ts`, `calls: createAuth`, `called by: run`, `exports: login`; excludes `format` / `util.ts` / `logout`. run's chunk embeds its `import { login } from "./auth"`.
  - Task 10.1: `chunk_key` is the stable key (`auth.ts|typescript|login|function`); two full builds produce identical `chunk_key` / `content_hash` / `embedding_text` sets; a body edit changes `content_hash` while keeping `chunk_key`; distinct symbols have distinct keys; one chunk per symbol.
- Persistence: `tests/test_index_store.py` round-trips `(chunk_key, content_hash, chunk_version)` plus full embedding/display/relative-path fidelity and includes `chunks` in the rollback table list; `tests/test_incremental_indexer.py` asserts a second no-op `reindex_index` keeps identical chunks.

### Persistence

- `storage/repositories/chunk_repository.py` — `insert_many`/`fetch_all` matching the repository pattern; `chunk_key` maps to the `chunks.chunk_id` primary-key column.
- `models/build_result.py` — added `chunks: list[SemanticChunk]`.
- `analysis/build_graph.py` — computes `result.chunks` as the final step after `run_graph_pass`.
- `storage/index_store.py` — `chunk_repository.insert_many(conn, result.chunks)` inside the same transaction (after relationships); `load_index` reconstructs chunks from the table.
- `indexing/indexer.py` — recomputes `result.chunks = build_semantic_chunks(result)` from the merged result immediately before `persist_index` (cheap; no per-file merge needed).

---

# 17. Phase 11 — Local Embedding Store

Status: COMPLETE

Goal:

> Embed semantic chunks locally and reuse embeddings when content is unchanged.

Architecture:

```text
Semantic Chunk
    ↓
chunk_hash
    ↓
embedding_cache
```

If hash unchanged:

```text
reuse vector
```

If changed:

```text
embed again
```

---

## Task 11.1 — Embedding Provider Interface

Create a small interface:

```text
EmbeddingProvider
    embed(text)
    embed_batch(texts)
```

Implementation:

```text
LocalEmbeddingProvider
```

Do not hard-code `SentenceTransformer` throughout the project.

This keeps the system testable.

---

## Task 11.2 — Fake Embedding Provider

Tests should use a deterministic fake provider.

Do not load a real ML model in every unit test.

Test:

```text
same chunk hash
→ no second embedding call
```

### Implemented

- `embeddings/provider.py` — `EmbeddingProvider` ABC with `dimension` and `embed(text)` / `embed_batch(texts)` / `embed_query(query)`; vectors are `numpy` arrays.
- `embeddings/local_provider.py` — `LocalEmbeddingProvider` wraps `SentenceTransformer` (`all-MiniLM-L6-v2` default), returns normalized float32 vectors. The only place `SentenceTransformer` is referenced.
- `embeddings/fake_provider.py` — deterministic `FakeEmbeddingProvider(dimension=8)`: SHA-256 of the text mapped to float32 in `[-1, 1)` and L2-normalized; same text → identical vector, no ML model loaded.
- `indexing/vector_index.py` — now depends on `EmbeddingProvider` (`embed_batch` for `build`, `embed_query` for `search`); the old `EmbeddingEncoder` was deleted.
- `indexing/embedding_store.py` — `embed_chunks(chunks, provider, cache) -> (embeddings_by_key, new_count)`: reuses any `content_hash` found in the cache, embeds only the missing chunks via `embed_batch`, and reports how many were newly embedded.
- `storage/repositories/embedding_repository.py` — `insert_many` / `fetch_all` / `load_embedding_cache(conn)` (the last joins `chunks.content_hash` → vector); vectors are stored as float32 blobs.
- `storage/index_store.py` — `persist_index(..., embeddings=None)` writes embeddings inside the same transaction (after chunks); new `load_embedding_cache(db_path)` wrapper.
- `indexing/indexer.py` — `reindex_index(db_path, root_dir, *, embedding_provider=None)`. With no provider, embeddings are skipped entirely (no model loading, no cache IO beyond the existing path). With a provider, the existing cache is loaded, missing chunks are embedded, and `IndexRunReport.new_embeddings` reports the count. Threaded through `_incremental_rebuild` too.

### Persistence

- `embeddings` table (existing schema, BLOB) is already first in `_TABLES_IN_DEPENDENCY_ORDER`; chunk keys map to the `chunks.chunk_id` PK.

---

# 18. Phase 12 — SQLite FTS5

Status: COMPLETE

Goal:

> Fast lexical retrieval for exact identifiers and code terms.

Index fields such as:

```text
symbol name
qualified name
file path
chunk text
```

Use FTS5 only for lexical retrieval.

Do not treat FTS scores as semantic scores.

### Implemented

- `storage/schema.py` — `chunks_fts` FTS5 virtual table (`tokenize = 'porter unicode61'`) with `chunk_id UNINDEXED` plus `symbol_name`, `qualified_name`, `relative_path`, `chunk_text` columns; created idempotently with the rest of the schema. FTS rows are derived state, rebuilt on every persist.
- `storage/repositories/chunk_fts_repository.py` — `insert_many(conn, chunks, symbols_by_id)` joins each chunk to its symbol for the structured name/qualified-name fields and indexes the chunk's `embedding_text`; `search(conn, query, limit)` builds a quoted-term `MATCH` query (whitespace split, `AND`-joined — no operator injection) and returns `FtsHit` rows ranked by `bm25(chunks_fts)` ascending (best first).
- `models/entities/fts_hit.py` — `FtsHit(chunk_key, symbol_name, qualified_name, relative_path, score)`; the `chunk_key` is the stable key, so FTS hits merge cleanly with vector hits in hybrid retrieval.
- `storage/index_store.py` — `persist_index` writes FTS rows in the same transaction (after chunks); `chunks_fts` added to `_TABLES_IN_DEPENDENCY_ORDER` so snapshot clears cover it; new `search_lexical(db_path, query, limit)` wrapper.
- The score is purely lexical (BM25); nothing treats it as a semantic score.

### Decision notes

- `unicode61` + porter was chosen over `trigram` for predictable whole-identifier matching (spec: "exact identifiers"). Because FTS is rebuilt on every persist, switching tokenizers later is a one-line schema change.
- No persistence of FTS rows beyond the snapshot replace: `load_index` reconstructs chunks and FTS is re-derived at persist time (source of truth is the semantic index).

---

# 19. Phase 13 — Vector Retrieval

Status: COMPLETE

Goal:

> Semantic retrieval over chunks.

Requirements:

```text
local
persistent
incrementally updated
top-k
metadata filters
```

Start with the simplest local implementation supported by the project.

Only introduce sqlite-vec or another extension after verifying its operational requirements.

Keep an abstraction:

```text
VectorStore
```

so the storage implementation can change without rewriting retrieval logic.

### Implemented

- `retrieval/vector_store.py` — `VectorStore` ABC with `search(query_vector, *, top_k, relative_path=None) -> list[VectorSearchHit]`; `VectorSearchHit(chunk_key, relative_path, score, chunk)`.
- `retrieval/numpy_vector_store.py` — `NumpyVectorStore(entries)` builds an in-memory float32 matrix from `(SemanticChunk, vector)` pairs and does L2-normalized cosine search; optional `relative_path` filter (metadata filter). Local, top-k, no external extensions.
- `storage/index_store.py` — `load_vector_store(db_path)` reconstructs a `NumpyVectorStore` by joining the persisted `chunks` and `embeddings` tables; because `persist_index` snapshots chunks + embeddings together in one transaction, the store always reflects the latest committed generation (incrementally updated by reindexing).
- `indexing/vector_index.py` is unchanged: it remains the on-the-fly "embed texts then search" in-memory path used by `HybridRetriever`; `VectorStore` is the persisted-vector abstraction for retrieval over the on-disk index.

### Decision notes

- Requirement "incrementally updated" is satisfied by the snapshot-replace model: the embeddings table is rewritten in the same transaction as the rest of the index, and `load_vector_store` reads fresh state on demand. A live in-memory cache with subscription to reindex events is deferred until a consumer needs it.
- No sqlite-vec / extension: the local numpy matrix over persisted float32 blobs covers current scale; the `VectorStore` boundary is where a storage-backed implementation would slot in without touching retrieval logic.

---

# 20. Phase 14 — Hybrid Retrieval

Status: COMPLETE

Pipeline:

```text
query
  ↓
query classification
  ├── exact symbol
  ├── graph
  ├── FTS
  └── vector
  ↓
candidate merge
  ↓
graph expansion
  ↓
rerank
```

Start with simple weighted scoring or reciprocal rank fusion.

Do not train a reranker before establishing a baseline.

### Implemented

- `retrieval/ranking.py` — `reciprocal_rank_fusion(ranked_lists, k=60)` merges best-first ranked key lists by `Σ 1/(k + rank + 1)`; a candidate surfaced by multiple sources outranks one from a single source.
- `retrieval/candidate.py` — `HybridCandidate(chunk_key, symbol_id, symbol_name, qualified_name, relative_path, symbol_kind, score, sources)`. `chunk_key` is the stable key, so exact / FTS / vector candidates merge on one identity. `sources` records which strategies contributed.
- `retrieval/hybrid_retriever.py` — rewritten `HybridRetriever`:
  - **Query classification**: `who calls X` → `graph_callers`; `what does X call` → `graph_callees`; `where is X defined/implemented` → `exact_symbol`; anything else → `hybrid`.
  - **Candidate merge**: FTS (`search_lexical`), vector (`VectorStore.search` via injected `embed`), and exact symbol lookups (per query token) are each ranked best-first and fused with RRF by `chunk_key`.
  - **Rerank baseline**: a deterministic `NAME_MATCH_BOOST` (+0.5) lifts candidates whose symbol name appears verbatim in the query — the "exact symbol match" feature, deliberately heuristic (Phase 16 formalizes reranking).
  - **Graph expansion**: the top hybrid candidate's 1-hop neighborhood (callers, callees, parent) is appended as supporting candidates tagged `source=("graph",)`, capped at `GRAPH_EXPANSION_LIMIT = 3`. This is the baseline that Phase 15 extends into proper seed-neighborhood retrieval.
  - DB-free: `fts_search` / `vector_store` / `embed` are injected, keeping the retriever unit-testable with stubs.
- `storage/index_store.py` — `build_hybrid_retriever(db_path, provider=None)` wires `load_index` + `search_lexical` + `load_vector_store` + `provider.embed_query`. With no provider the vector source is skipped gracefully.

### Tests

`tests/test_hybrid_retrieval.py` — RRF ordering (multi-source beats single-source); stub-driven merge/ranking/sources; graph expansion adds a caller tagged `graph`; FTS-only retrieval without a vector source; and integration via `reindex_index` → `build_hybrid_retriever`: `who calls`, `what does ... call`, `where is ... defined`, exact-name-first hybrid, no-provider fallback, and empty-index behavior.

### Decision notes

- No trained reranker: per spec, the baseline is deterministic weighted scoring (RRF + name-match boost). Phase 16 adds the full feature set only after this baseline is measured.
- Graph expansion is deliberately capped and appended (supporting context), not fused into the main ranking — Phase 15 owns hop semantics and context budgets.

---

# 21. Phase 15 — Graph-Aware Retrieval

Status: COMPLETE

For a semantic seed:

```text
AuthService.login
```

expand:

```text
1-hop:
    callers
    callees
    parent
    imports
    exports

2-hop:
    only when necessary
```

Do not blindly expand N hops.

Context budgets matter.

## Implemented

- `retrieval/neighborhood.py` — `NeighborhoodHit(symbol, relation, hop)` and `expand_neighborhood(seed, *, graph, symbol_index, resolved_imports=None, exports=None, one_hop_budget=6, two_hop_budget=2)`:
  - **1-hop** in stable order (`caller`, `callee`, `parent`, `import`, `export`): callers/callees/parents from the graph, imports as the seed document's resolved target symbols (`ResolvedImportReference.target_symbol`), exports as the seed document's module-scope symbols matching `Export.symbol_name`. Deduplicated by `symbol_id` (first relation wins), capped at `one_hop_budget`, with structural relations ranked before supporting ones so the budget never starves call context.
  - **2-hop only when necessary**: when the seed has no direct call edges (no callers and no callees), one transitive hop is walked through the seed's children — each child's callees are appended as `relation="callee", hop=2`, capped at `two_hop_budget`. Class/namespace seeds whose nearest call context sits two hops away get method-level context; symbols with any direct call edge never trigger 2-hop.
  - The seed itself is never a neighbor; results are deterministic across runs.
- `retrieval/hybrid_retriever.py` — `HybridRetriever` gains optional `resolved_imports` / `exports`; `_expand_graph` (hybrid search) now uses `expand_neighborhood` instead of the Phase 14 `callers + callees + parents` hard-cap of 3. Supporting candidates stay tagged `("graph",)`. When `resolved_imports`/`exports` are not injected, imports/exports relations are skipped (stub tests unchanged).
- `storage/index_store.py` — `build_hybrid_retriever` passes `resolved_imports=result.resolved_import_references` and `exports=result.exports`, so the persisted index enables full 1-hop expansion including imports and exports.

### Tests

- `tests/test_graph_retrieval.py` (new) — all five 1-hop relations present and deduped; import relation appears even when the imported symbol is never called; parent relation resolves the enclosing class; the same symbol reached via call and import is emitted once; 2-hop fires only for a seed with no direct call edges (class → method's callee at `hop=2`); 2-hop is absent when the seed has a direct callee; `one_hop_budget` caps exports and is configurable; deterministic order across two runs; isolated leaf produces an empty neighborhood; `resolved_imports=None`/`exports=None` skip supporting relations.
- `tests/test_hybrid_retrieval.py` (extended) — stub-driven: expansion includes callers, callees, and export neighbors, plus an import neighbor for a seed that never calls the import; integration via `reindex_index` → `build_hybrid_retriever`: querying `orchestrate` surfaces its imported `helper` tagged `graph`.

### Decision notes

- 2-hop trigger is "no direct call edges → walk children's callees" per the chosen design: the nearest reachable call context for a class/namespace seed sits one containment hop plus one call hop away, and any symbol with a direct call edge already has sufficient 1-hop structural context.
- Children are deliberately not a 1-hop relation (the spec lists five kinds); they serve only as the 2-hop bridge. `children_of` remains available to consumers that need containment context.
- Imports/exports are document-scoped (the seed's file), consistent with the Phase 10 chunker, so a chunk and its neighborhood agree on what "imports/exports" mean.

---

# 22. Phase 16 — Reranking

Status: COMPLETE

Start with deterministic features:

```text
exact symbol match
path match
kind match
FTS score
vector score
graph distance
relationship relevance
```

Example:

```text
"who calls login"
```

should strongly prioritize:

```text
incoming CALLS edges
```

not just vector similarity.

Only introduce a local model reranker after the heuristic baseline is measured.

## Implemented

- `retrieval/reranker.py` — `RerankFeatures(exact_symbol, path_match, kind_match, fts, vector, graph_distance, relationship)` and `rerank_candidates(candidates, query, *, graph, symbols_by_key, seed=None, preference=None)`. Each candidate's base RRF score gets a deterministic weighted boost (`RELATIONSHIP_WEIGHT = 1.0`, `EXACT_SYMBOL_WEIGHT = 0.8`, `GRAPH_DISTANCE_WEIGHT = 0.4`, `PATH_WEIGHT = 0.3`, `KIND_WEIGHT = 0.2`, `FTS_WEIGHT = 0.1`, `VECTOR_WEIGHT = 0.1`), then candidates are stable-sorted by final score:
  - `exact_symbol` — symbol name appears verbatim in the query.
  - `path_match` — graded `(0, 0.5, 1.0)` overlap of relative-path/qualified-name tokens with query tokens.
  - `kind_match` — `function`/`class`/`method`/`variable` etc. appears in the query.
  - `fts` / `vector` — weak source-presence features (rank position is already in the RRF base score).
  - `graph_distance` — 1.0 for a direct graph neighbor of the seed (caller/callee/parent/child), 0.5 for distance 2, else 0.
  - `relationship` — 1.0 only for the relation the query asks for (`caller` for "who calls X" / "callers of X" / "called by X"; `callee` for "what does X call" / "callees of X"; `definition` for "where is X defined" / "definition of X").
- `detect_preference(query)` maps caller/callee/definition intent phrases to a `preference`, so relationship relevance dominates over vector similarity for graph-intent queries.
- `retrieval/hybrid_retriever.py` — the `NAME_MATCH_BOOST` heuristic is replaced by the reranker. `_hybrid_search` now:
  1. fuses FTS + vector + exact candidates (unchanged RRF baseline),
  2. detects a unique `seed` symbol from query tokens (`_detect_seed`, ambiguous names produce no seed — no first-match guessing),
  3. detects intent `preference`,
  4. expands the neighborhood around the seed (falling back to the top candidate) via the Phase 15 `expand_neighborhood`,
  5. reranks the combined candidate set with the deterministic features, then slices `top_k` — so graph neighbors can now outrank vector-similar-but-unrelated symbols instead of being appended after the slice.
- The dedicated `graph_callers` / `graph_callees` / `exact_symbol` strategies are unchanged (they already return exactly the wanted relation).

### Tests

- `tests/test_reranker.py` (new) — `detect_preference` intent mapping; exact-symbol boost outranks a higher base score; `callers of` preference lifts the caller above a higher-scored callee; graph-distance boost lifts a neighbor over an unrelated symbol; kind and path boosts; FTS source presence breaks a tie; deterministic across two runs; `who calls login` ranks the caller first with the seed itself second.
- `tests/test_hybrid_retrieval.py` (extended) — integration via `reindex_index` → `build_hybrid_retriever`: querying `callers of login` (a hybrid-path caller intent, not the routed canonical form) returns `run` — the incoming CALLS edge — as the top candidate.

### Decision notes

- No trained/local-model reranker per the spec: the baseline is deterministic feature scoring, measured before any model is introduced (rule 1.1).
- `exact_symbol` reuses the verbatim-name feature the Phase 14 baseline already used; the other six features are added deterministically. Weights are chosen so relationship relevance dominates for graph-intent queries and exact symbol match dominates for definition-style queries; FTS/vector rank position remains in the base RRF score.
- Graph-expanded candidates now participate in ranking instead of being appended after `top_k`; Phase 15's neighborhood module is unchanged and supplies the candidates.

---

# 23. Phase 17 — Context Builder

Status: COMPLETE

Goal:

> Produce the smallest context that is sufficient for the task.

Input:

```text
ranked candidates
graph
query
token budget
```

Output:

```text
ContextPack
```

Possible structure:

```text
primary definitions
supporting definitions
important relationships
file paths
minimal source excerpts
```

Rules:

- deduplicate overlapping source
- preserve symbol boundaries
- prioritize direct evidence
- enforce a hard budget
- never silently exceed budget

## Implemented

- `retrieval/context_builder.py` — `estimate_tokens(text)` (`max(1, len(text) // 4)`, deterministic chars-per-token heuristic — no tokenizer dependency), `ContextEntry(chunk_key, symbol_id, qualified_name, symbol_kind, relative_path, location, role, source)`, `ContextPack(query, token_budget, total_tokens, primary_definitions, supporting_definitions, relationships, file_paths)`, and `build_context_pack(candidates, *, query, graph, symbols_by_key, token_budget)`.
- `build_context_pack`:
  - **Deduplicate overlapping source**: candidates are deduplicated by `chunk_key` (the stable symbol key), so a symbol surfaced by multiple sources contributes exactly one entry; `file_paths` is the sorted unique path set; candidates with no `Symbol` in `symbols_by_key` (no source available) are skipped.
  - **Prioritize direct evidence**: candidates whose only source is `("graph",)` become `supporting`; everything else is `primary`. Primaries are added in rank order first, then supporting — a supporting symbol can never starve a primary.
  - **Enforce a hard budget / never silently exceed**: an entry is added only if its `header + source` fits the remaining budget. If only the source does not fit, the symbol is emitted header-only (`source=""`, `location="path:line"`); if even the header does not fit, it is skipped — so **symbol boundaries are preserved** (a symbol's source is never truncated mid-body) and `total_tokens <= token_budget` always holds.
  - **Important relationships**: `(source.qualified_name -> callee.qualified_name (calls))` edges from `graph.callees_of`, emitted only when _both_ endpoints were selected, deduplicated and sorted deterministically.
- `storage/index_store.py` — `build_context_pack_from_index(db_path, query, *, token_budget, provider=None, top_k=5)` = `load_index` + `build_hybrid_retriever` + `retrieve` + `build_context_pack`, mirroring the `build_hybrid_retriever` convenience (consumer: Phase 21 `ckg context` CLI).

### Tests

- `tests/test_context_builder.py` — token estimation (4 chars → 1 token, empty → 1, deterministic); single candidate is primary with full source; graph-only candidate is supporting; `total_tokens <= budget` across a range of budgets including a symbol whose source alone exceeds the budget; symbol boundaries preserved (header-only fallback, never a truncated body); a symbol skipped when even its header does not fit; primary-before-supporting when budget is tight; duplicate candidates appear once; relationships only among selected symbols; file-path dedup + sort; unknown candidate keys skipped; determinism across two runs; empty candidates → empty pack; integration via `reindex_index` → `build_context_pack_from_index` (queried symbol is primary, budget respected, with and without an embedding provider).

---

# 24. Phase 18 — Incremental Embedding / Async Worker

Status: COMPLETE

Embedding should not block semantic indexing.

Target:

```text
semantic index ready
        ↓
embedding queue
        ↓
worker
        ↓
vector store
```

Queue state:

```text
PENDING
PROCESSING
DONE
FAILED
```

Retry only failed embedding jobs.

Do not re-embed chunks with unchanged content hashes.

## Implemented

- `storage/schema.py` — `embedding_jobs` table (`chunk_key` PK, `content_hash`, `status`, `attempts`, `error`); `SCHEMA_VERSION` bumped to 2. The `embeddings` table no longer has a `chunks` foreign key (embeddings are pruned explicitly, not via cascade — see below), matching `embedding_jobs`, which is also keyed by `chunk_key` rather than a DB relationship.
- `models/entities/embedding_job_status.py` — `EmbeddingJobStatus` enum (`PENDING`, `PROCESSING`, `DONE`, `FAILED`). `models/entities/embedding_job.py` — `EmbeddingJob(chunk_key, content_hash, status, attempts, error)`.
- `storage/repositories/embedding_job_repository.py`:
  - `enqueue(conn, chunk_key, content_hash)` — upserts a job. A `FAILED` job stays `FAILED` (surfaced for retry, not silently reset); a `DONE` job with an unchanged `content_hash` stays `DONE` (never re-embedded); anything else (new chunk, or `DONE` with a changed `content_hash`) becomes `PENDING`.
  - `claim(conn, limit)` — atomically moves `PENDING`/`FAILED` jobs to `PROCESSING` and returns them (single `UPDATE ... RETURNING`, so concurrent workers cannot double-claim). This is also the retry path: a `FAILED` job is claimable exactly like a `PENDING` one.
  - `mark_done` / `mark_failed(error)` / `reenqueue` (resets to `PENDING`) / `status_counts` / `fetch_all`.
- `indexing/embedding_queue.py`:
  - `enqueue_embedding_jobs(db_path, chunks)` — called after `persist_index` with the just-persisted chunks; one `enqueue` per chunk in a single transaction. This is the non-blocking handoff: semantic indexing finishes and returns before any embedding work happens.
  - `run_embedding_worker(db_path, provider, *, limit=None) -> EmbeddingRunReport(claimed, done, reused, stale, failed)` — the worker, run as a separate step:
    1. `claim`s up to `limit` `PENDING`/`FAILED` jobs.
    2. Re-checks each claimed job's `content_hash` against the chunk's _current_ `content_hash` in the `chunks` table: a mismatch (the chunk changed again after this job was enqueued) is re-enqueued as `PENDING` with the fresh hash instead of being embedded with stale text; a chunk that no longer exists is dropped from the queue.
    3. Embeds the rest via the Phase 11 `embed_chunks` (cache-aware — a chunk whose `content_hash` is already in the embedding cache is reused, not re-embedded).
    4. On any embedding exception, every claimed-and-embeddable job in the batch is marked `FAILED` with the error message and the run returns early — a failed run never marks jobs `DONE`.
    5. On success, embeddings are upserted and jobs marked `DONE` in one transaction.
  - `queue_status(db_path) -> dict[str, int]` — status → count, for CLI/observability.
- `storage/repositories/embedding_repository.py` — `insert_many` renamed to `upsert` (`ON CONFLICT DO UPDATE`, since a retried or re-embedded chunk revisits the same `chunk_id`). `load_embedding_cache` now joins through `embedding_jobs` and requires `status = 'DONE' AND content_hash` match, so an embedding is only usable as a reuse-cache hit once its job has actually completed — a `PROCESSING`/`FAILED` row's stale embedding (if any) is never served.
- `storage/index_store.py` — `persist_index` no longer takes an `embeddings` argument; embedding is fully decoupled from the semantic-index transaction. `_prune_derived` deletes `embeddings`/`embedding_jobs` rows for chunks no longer present after a snapshot replace (mirrors `_clear_all`'s dependency-order cleanup for the derived embedding state).
- `indexing/indexer.py` — `reindex_index` / `_incremental_rebuild` dropped the `embedding_provider` parameter and the old synchronous `_embed_for_persist` call entirely. After `persist_index`, `enqueue_embedding_jobs(db_path, result.chunks)` is called and `reindex_index` returns immediately — indexing is never blocked on embedding. `IndexRunReport.new_embeddings` stays at its default `0` (embedding counts now belong to `EmbeddingRunReport`, produced by the separate worker run).

### Tests

- `tests/test_embedding_queue.py` (new) — indexing enqueues every chunk as `PENDING`; the worker moves `PENDING` → `DONE` and `queue_status` reflects it; re-running the indexer over unchanged files keeps jobs `DONE` (not reset to `PENDING`) and the worker claims zero; a failing provider marks jobs `FAILED` and a later run with a working provider retries and completes exactly those jobs (retry-only-failed); `limit` caps how many jobs one worker run claims.
- `tests/test_embedding_indexer.py` (rewritten from the Phase 11 synchronous-embedding version) — first run embeds every chunk via the worker; a no-op reindex leaves the worker with nothing to claim; a body edit re-enqueues and re-embeds only the changed chunk while other embeddings are untouched; embeddings round-trip through persistence; skipping the worker after `reindex_index` leaves the embedding cache empty.
- `tests/test_index_store.py::test_round_trip_preserves_embeddings` — updated to go through `enqueue_embedding_jobs` + `run_embedding_worker` instead of a removed `persist_index(..., embeddings=...)` argument, since embeddings are no longer part of the persist transaction.
- `tests/test_context_builder.py`, `tests/test_hybrid_retrieval.py`, `tests/test_vector_store.py` — integration setups updated to `reindex_index(...)` followed by `run_embedding_worker(...)` in place of the removed `embedding_provider=` kwarg.

### Decision notes

- The worker is invoked explicitly (as a plain function call in these tests); no background thread/process/scheduler is introduced yet — nothing in the current CLI/consumer surface needs one (rule 1.5), and `run_embedding_worker` is the seam a future scheduled/async runner would call into.
- Retry has no attempt cap: `attempts` is tracked on every `EmbeddingJob` for future backoff/give-up policy, but nothing currently reads it. Adding a cap without a consumer would be speculative (rule 1.5).
- Stale-hash re-enqueue (job claimed for content that has since changed again) takes priority over embedding-with-stale-text: correctness (rule 1.1) over throughput, since the alternative is silently caching an embedding for text that no longer matches any chunk.

---

# 25. Phase 19 — Secure Local Indexing

Status: COMPLETE (ignore rules delivered here; derived-state boundary and content-addressed cache are pre-existing/covered by earlier phases, not revisited here)

Adopt local-safe ideas from production code indexing systems.

## Ignore rules

Honor:

```text
.gitignore
.ckgignore
```

before parsing or embedding.

### Implemented

- `ingestion/ignore_rules.py` — `IgnoreRules.is_ignored(relative_path, *, is_dir=False)` wraps a `pathspec.PathSpec` (the `gitignore` pattern factory, full gitwildmatch semantics including negation and directory-only patterns). `load_ignore_rules(root_dir)` reads `.gitignore` then `.ckgignore` from the repo root and concatenates their patterns — `.ckgignore` adds project-specific ignores on top of `.gitignore` rather than replacing it. Only root-level ignore files are read; nested per-directory ignore files are not supported yet (no consumer needs them — rule 1.5). Missing files simply contribute no patterns, so a repo with neither file ignores nothing (never `None`, so callers don't need extra branching).
- `ingestion/loader.py:iter_repo_files` — the single file-discovery choke point already used by `load_code_files` and (transitively, via `indexing/diff.py:scan_files`) by the incremental indexer. It now loads ignore rules once per call and skips any file whose repo-relative path matches, alongside the existing `EXCLUDE_DIRS`/`INCLUDE_EXTENSIONS` checks. Every consumer of `iter_repo_files` — `load_code_files`, `scan_files`, `reindex_index` — honors `.gitignore`/`.ckgignore` for free before parsing or embedding.
- `indexing/merkle.py:compute_merkle_tree` — walks the tree independently of `iter_repo_files` (it hashes all files, not just supported extensions), so it did **not** automatically inherit the new rule; `_build_directory` now also takes `ignore_rules` and checks it for every entry (`is_dir=True` for directories, so a directory-only pattern like `vendor/` prunes the whole subtree instead of only individual files) — otherwise a `.gitignore`'d directory would still perturb ancestor hashes.

### Tests

- `tests/test_ignore_rules.py` (new) — no ignore files ignores nothing; a `.gitignore` glob pattern; a directory pattern matches nested files at any depth; `.ckgignore` patterns are honored on their own; `.gitignore` and `.ckgignore` combine; negation (`!pattern`) un-ignores; `is_dir=True` applies a directory-only pattern that a same-named file wouldn't match.
- `tests/test_document_loading.py` — `load_code_files` skips a `.gitignore`'d glob and a `.ckgignore`'d directory.
- `tests/test_merkle.py` — `compute_merkle_tree` excludes both a `.gitignore`'d file and an entire `.gitignore`'d directory (neither the directory node nor anything under it appears in the tree).

### Decision notes

- Chose `pathspec` (the standard library for this) over hand-rolling gitignore semantics — directory pruning, negation, and glob edge cases are exactly the kind of thing rule 1.4 says not to guess at.
- `.gitignore` and `.ckgignore` are additive, not alternatives: a repo already has a `.gitignore` for its own reasons (build output, `node_modules`, etc.) and `.ckgignore` is for indexer-specific exclusions (e.g. fixtures/generated code a developer still wants tracked in git but not semantically indexed).

## Derived-state boundary

Treat the local index as disposable.

## Content-addressed cache

Use hashes for:

```text
chunks
embeddings
parsed artifacts where useful
```

## Optional future hosted mode

Only if a cloud product is later built:

```text
Merkle tree
shared index reuse
content proofs
tenant isolation
```

Do not build these distributed-system features in the local v1.

---

# 26. Phase 20 — Index Generations

Status: COMPLETE

Every successful indexing transaction should produce a consistent logical generation.

Example:

```text
generation 41
    ↓
changes
    ↓
generation 42
```

Readers should never observe half of generation 41 and half of generation 42.

Use SQLite transactions for atomic publication.

## Implemented

- Atomic publication already existed since Phase 7 (Task 7.3): `persist_index` does a full snapshot-replace — clear then re-insert every table — inside one `db.transaction`, so a reader never observes a half-written snapshot; a failure anywhere rolls back the whole thing. Phase 20 makes that guarantee _observable_ by adding an explicit, monotonic generation counter that publishes atomically with the data it labels.
- `storage/schema.py` — `current_generation(conn) -> int` / `bump_generation(conn) -> int` follow the existing `schema_version`/`set_schema_version` pattern: both read/write the `generation` key in the already-present `index_metadata` table (no new table — rule 1.5). `bump_generation` reads-then-writes `current + 1` and returns the new value; a database that has never had `create_schema` run, or has no `generation` row yet, reads as generation `0`.
- `storage/index_store.py` — `persist_index` calls `schema.bump_generation(conn)` as the **last** statement inside the same transaction that writes the snapshot (after `file_state_repository.insert_many`). Because it's in the same transaction: a successful persist always ends with `generation == N+1` exactly matching the just-committed data, and a failed persist (any exception, e.g. the existing FK-violation test) rolls back the bump along with everything else — the generation counter and the data it describes can never disagree. `current_generation(db_path) -> int` is a new reader wrapper (`db.connect` + `schema.current_generation`) for callers/tests/future CLI status.

### Tests

- `tests/test_storage_schema.py` — `current_generation` is `0` before `create_schema`; `bump_generation` increments (`1`, then `2`) and `current_generation` reflects the last bump.
- `tests/test_index_store.py` — `current_generation` is `0` for a database that has never been persisted; two successful `persist_index` calls produce generations `1` then `2`; a `persist_index` call that raises `sqlite3.IntegrityError` (the existing rollback fixture) leaves the generation at its last successful value instead of bumping.

### Decision notes

- No separate "generations" table or history: the spec only requires that readers never see a torn generation, not that past generations be enumerable or diffable — that would be speculative (rule 1.5) without a consumer needing generation history.
- `IndexRunReport` is intentionally not extended with a `generation` field yet: nothing in the current codebase reads it (Phase 21's `ckg status` is the natural future consumer). `current_generation(db_path)` is available as a plain reader in the meantime.

---

# 27. Phase 21 — Agent / CLI Integration

Status: COMPLETE

Only after retrieval is reliable.

Start with a local CLI/library:

```text
ckg index .
ckg status
ckg search "authentication flow"
ckg definition createAuth
ckg callers login
ckg callees login
ckg imports auth.ts
ckg context "how does login work?"
```

Then expose an agent protocol such as MCP.

The agent should be able to request:

```text
exact definition
graph neighborhood
semantic search
context pack
```

## Implemented

- `cli.py` (repo root) — a thin `argparse` dispatcher over pure, independently-testable `cmd_*` functions (`cmd_index`, `cmd_status`, `cmd_search`, `cmd_definition`, `cmd_callers`, `cmd_callees`, `cmd_imports`, `cmd_context`), each taking a `db_path` and returning a value (`IndexRunReport`, `HybridRetrieval`, `ContextPack`, a status `dict`, or a list of `(ImportReference, ResolvedImportReference | None)`). `main(argv)` parses arguments, formats, and prints; it contains no logic of its own, so tests exercise the `cmd_*` functions directly and only lightly touch `main()` for dispatch/exit-code behavior.
- `ckg index <path>` — `Path(db_path).parent.mkdir(parents=True, exist_ok=True)` then `reindex_index`; embedding is opt-in via `--embed` (loads `LocalEmbeddingProvider` and runs the Phase 18 worker after indexing), consistent with "embedding must not block indexing" — a plain `ckg index` never loads the ML model.
- `ckg status` — generation (Phase 20), document/symbol/chunk/embedding counts, and the embedding job queue breakdown (Phase 18's `queue_status`), so a user can see whether embeddings are still pending before running `search`.
- `ckg search` / `ckg context` — the only commands that can use vector search, since they alone reach `HybridRetriever`'s general `hybrid` strategy; `_resolve_provider` auto-detects whether embeddings exist (`has_embeddings`, via the Phase 11 embedding cache) and only then lazily imports and loads `LocalEmbeddingProvider` — `--no-vector` forces FTS/exact-only. `definition`/`callers`/`callees` route through `HybridRetriever`'s dedicated regex-matched strategies (`exact_symbol`/`graph_callers`/`graph_callees`), which never touch FTS or vectors, so they never load a provider at all.
- `ckg definition` / `ckg callers` / `ckg callees` — formats the query into the exact phrasing `HybridRetriever.retrieve` already routes deterministically (`"where is {name} defined"`, `"who calls {name}"`, `"what does {name} call"`) rather than duplicating routing logic in the CLI.
- `ckg imports <file>` — lists the file's own `import_reference`s (module path, imported name, local name) each paired with its `ResolvedImportReference` when one exists, matched by object identity (`id()`) within a single `load_index()` call — the same reused-instance pattern persistence already relies on (`ids_by_import_object` in `import_repository`). An import to a target outside the repo (no matching document) has no `ResolvedImportReference` at all and prints as `unresolved`, rather than being silently dropped.
- Read commands (`status`/`search`/`definition`/`callers`/`callees`/`imports`/`context`) check `Path(db_path).exists()` first and print a "run `ckg index` first" message with exit code `1` instead of a raw `sqlite3` error on a repo that was never indexed.
- No `[project.scripts]` entry point: this project isn't currently packaged (`uv sync` warned that entry points need `tool.uv.package = true` or a `[build-system]`, which would require restructuring the flat top-level module layout) — invoke via `uv run python cli.py <command>` for now. Revisit if/when the project is packaged for distribution.
- `mcp_server.py` (repo root) — an MCP server (`mcp` dependency, `mcp.server.mcpserver.MCPServer`) exposing eight `@mcp.tool()`-decorated functions that wrap the _same_ `cmd_*` functions the CLI uses: `index_repository`, `repository_status`, `definition`, `callers`, `callees`, `search`, `imports`, `context` — directly covering the spec's four agent requests (exact definition → `definition`; graph neighborhood → `callers`/`callees`; semantic search → `search`; context pack → `context`), plus indexing/status so an agent can bootstrap a repo through the same protocol without shelling out to the CLI first.
  - Every tool returns a plain JSON-serializable `dict` (never a raw dataclass/`HybridRetrieval`/`ContextPack`) via small `_candidate_dict`/`_import_dict`/`_context_entry_dict` helpers — deliberately not relying on the framework's dataclass-to-schema inference, so serialization is exactly what the docstring promises regardless of SDK internals.
  - Read tools (`definition`/`callers`/`callees`/`search`/`imports`/`context`) return `{"error": "...Call index_repository(path=...) first."}` instead of raising when nothing has been indexed yet — a _soft_ error (`is_error=False`, readable JSON) so an agent can read the message and self-correct by calling `index_repository`, rather than the call failing at the protocol level.
  - `search`/`context` reuse `cli.resolve_provider` (promoted from a CLI-private `_resolve_provider` to a shared function once this became its second caller — rule 1.5) to auto-detect whether embeddings exist before lazily loading `LocalEmbeddingProvider`, exactly mirroring the CLI's "vector is opt-in, never loaded just to answer an exact query" behavior.
  - `main()` runs `mcp.run(transport="stdio")` — the standard local-process transport for a coding-agent-invoked MCP server (Claude Code, Codex CLI, etc. all launch MCP servers over stdio).

### Tests

- `tests/test_cli.py` — `cmd_index` creates the db and reports parsed files; embeddings stay empty without a provider and populate with one (`FakeEmbeddingProvider`, no network/model download); `cmd_status` reports generation/counts/queue state; `cmd_search` without a provider still finds exact/FTS matches, and with a provider surfaces a `vector`-sourced candidate; `cmd_definition`/`cmd_callers`/`cmd_callees` return the expected symbol sets; `cmd_imports` pairs a resolved import with its target document/symbol and returns `[]` for an unknown file; `cmd_context` respects the token budget. `TestCliMain` exercises `main()` argv dispatch and exit codes (`index` creates the db; `status` before any index exits `1`; `status`/`search` after indexing exit `0`) — deliberately never passes `--embed`, so the test suite never loads a real ML model.
- `tests/test_mcp_server.py` (`unittest.IsolatedAsyncioTestCase`, calling `mcp.list_tools()`/`mcp.call_tool()` in-process — no subprocess or real stdio transport needed) — all eight tools are registered; `repository_status` on an unindexed path reports `{"indexed": False}` rather than erroring; a read tool before indexing returns the soft "call index_repository" error; indexing then status/definition/callers/callees/imports/search/context all round-trip through JSON with the expected values, including that `imports` resolves `api.ts`'s import of `login` to `auth.ts::login` and `search` without embedding reports `vector_search_used: False`.

### Decision notes

- The CLI resolves its own default database location (`<path>/.ckg/index.sqlite`) rather than requiring `--db` on every call, so the example commands in this spec (`ckg index .`, `ckg status`, ...) work as written from within a repo. `mcp_server.py` reuses the same `default_db_path`, so an agent and a human running the CLI against the same repo share one index.
- MCP tools take the same `path` parameter the CLI does (not an implicit cwd) because an MCP server is a long-lived process an agent may point at multiple repositories across a session, unlike the CLI which is invoked fresh per command from within a repo.
- `structured_content` on tool results is left as the framework default (no `structured_output=True`) because every tool's return type is a generic `dict`, not a `TypedDict`/pydantic model — forcing structured output would only yield an unhelpful `{"type": "object"}` schema. The JSON text content already carries the full structured payload, which is what every test asserts against.

---

# 28. Phase 22 — Evaluation

Status: COMPLETE

Do not claim "95% token savings" without measurement.

Create fixed benchmark repositories and fixed questions.

## Structural questions

```text
Where is createAuth defined?
Who calls login?
What does login call?
What imports auth.ts?
```

## Semantic questions

```text
How does authentication work?
Where is token validation implemented?
How does a request reach the database?
```

## Metrics

Measure:

```text
definition accuracy
relationship accuracy
import resolution accuracy
Recall@K
MRR
context tokens
baseline tokens
token reduction
query latency
initial indexing latency
incremental indexing latency
embedding cache hit rate
```

## Implemented

- `tests/fixtures/evaluation_repo/` — the fixed benchmark repository: `auth.ts` (`createAuth`, `login` which calls `validateToken` + `createAuth`, `logout`), `token.ts` (`validateToken`, `generateToken`), `db.ts` (`connect`, `queryUser`), `api.ts` (`handleRequest`, which imports `login` from `auth.ts` and `queryUser` from `db.ts`) — small enough to keep the suite fast, wired for a real cross-file call chain (`handleRequest -> login -> createAuth`/`validateToken`, `handleRequest -> queryUser -> connect`) and a real cross-file import.
- `evaluation/benchmark.py` — `Question(id, text, category, kind, target, relevant, expected_location)` and the fixed `BENCHMARK_QUESTIONS` tuple: the doc's four structural questions verbatim, plus its three semantic questions, each carrying hand-authored ground truth (`relevant` symbol/path names; `expected_location` for definitions).
- `evaluation/metrics.py` — pure, independently tested functions: `recall_at_k`, `reciprocal_rank` (the MRR term for one question), `mean`, `token_reduction`, `accuracy`.
- `evaluation/runner.py` — `run_evaluation(*, provider=None, top_k=5, token_budget=800) -> EvaluationReport`, copies the benchmark repo into a temp directory (the checked-in fixture is never mutated) and measures every metric in the spec's list:
  - **definition / relationship / import resolution accuracy** — computed directly against the semantic index (`result.symbols`, `result.graph.callers_of`/`callees_of`, `indexing.diff.importers_of`), _not_ through retrieval — these are compiler-correctness metrics (Phases 2-6), independent of how well the retrieval layer happens to rank things.
  - **Recall@K / MRR** — computed by asking `HybridRetriever.retrieve(question.text)` the question's exact natural-language text (which the router's regexes already match without any CLI-side phrasing duplication) and scoring the ranked candidates against `question.relevant`. Every question, structural and semantic alike, gets a retrieval-quality score this way.
  - **context tokens / baseline tokens / token reduction** — `context_tokens` is the mean `ContextPack.total_tokens` across all seven questions (budget 800); `baseline_tokens` is `estimate_tokens` (Phase 17) over the whole fixture repo's concatenated source — the "send everything" alternative.
  - **query latency** — wall-clock around each `retriever.retrieve()` call, reported per question.
  - **initial / incremental indexing latency** — wall-clock around the first `reindex_index` and a second, no-op `reindex_index` over the same unchanged repo (the cheapest realistic "steady state" run).
  - **embedding cache hit rate** — embeds every chunk once, edits exactly one symbol's body (a change outside every symbol span wouldn't touch any chunk, since chunk identity is keyed off symbol content), re-indexes, and re-embeds: `1 - (jobs claimed / total chunks)`. Only the edited chunk should ever reach the worker; every other chunk should stay `DONE` without being re-enqueued at all (Phase 18's queue, not Phase 11's in-run cache dict, is what's actually being measured here — that dict only ever holds the _current_ hash per chunk, so it can't demonstrate a hit across an edit-and-revert).
- `cli.py` — `ckg eval [--embed] [--top-k N]` runs the suite and prints a table (per-question PASS/FAIL/`-` for the deterministic checks, Recall@K, MRR) plus the aggregate metrics. `--embed` loads `LocalEmbeddingProvider` so vector search is actually exercised; without it, `eval` never touches the network/model, matching `search`/`context`'s existing "vector is opt-in" behavior.

### Tests

- `tests/test_evaluation_metrics.py` — unit tests for every function in `evaluation/metrics.py` (recall@k boundaries including the empty-expected-set edge case, MRR position/tie-breaking, mean, token reduction, accuracy).
- `tests/test_evaluation_runner.py` — `run_evaluation()` with and without a provider: all seven fixed questions are answered; deterministic ground truth (definition/relationship/import-resolution accuracy) is `1.0` on the fixture in both cases; structural questions always carry a `bool` `correct` flag while semantic questions carry `None` (no deterministic ground truth exists for them, honestly reported rather than faked); Recall@K/MRR are perfect for the three structural non-import questions once vectors are available; the embedding-cache-hit-rate scenario lands strictly between 0 and 1 (some chunks reused, one wasn't); the checked-in fixture repo is untouched after the run (the temp-copy isolation actually holds).
- `tests/test_cli.py` — `ckg eval` runs end-to-end via `main()` with exit code `0` and no `--db`/path (it's self-contained).

### Results

Actual `ckg eval` output on the fixed benchmark repo (`tests/fixtures/evaluation_repo`), captured 2026-08-20. Not simulated — this is the real CLI run against the real pipeline.

**Without vector search** (`ckg eval` — FTS + exact + graph only, no ML model loaded):

```text
[structural] PASS recall@k=1.00 mrr=1.00 Where is createAuth defined?
[structural] PASS recall@k=1.00 mrr=1.00 Who calls login?
[structural] PASS recall@k=1.00 mrr=1.00 What does login call?
[structural] PASS recall@k=0.00 mrr=0.00 What imports auth.ts?
[semantic  ] -    recall@k=0.00 mrr=0.00 How does authentication work?
[semantic  ] -    recall@k=0.00 mrr=0.00 Where is token validation implemented?
[semantic  ] -    recall@k=0.00 mrr=0.00 How does a request reach the database?

definition accuracy:        1.00
relationship accuracy:      1.00
import resolution accuracy: 1.00
mean recall@k:              0.43
mean reciprocal rank:       0.43
context tokens:             15 (baseline 182, 91.8% reduction)
initial indexing:           4.7 ms
incremental indexing:       0.6 ms
embedding cache hit rate:   0.00
```

**With vector search** (`ckg eval --embed` — real `LocalEmbeddingProvider`, `all-MiniLM-L6-v2`):

```text
[structural] PASS recall@k=1.00 mrr=1.00 Where is createAuth defined?
[structural] PASS recall@k=1.00 mrr=1.00 Who calls login?
[structural] PASS recall@k=1.00 mrr=1.00 What does login call?
[structural] PASS recall@k=1.00 mrr=0.20 What imports auth.ts?
[semantic  ] -    recall@k=0.67 mrr=1.00 How does authentication work?
[semantic  ] -    recall@k=1.00 mrr=1.00 Where is token validation implemented?
[semantic  ] -    recall@k=1.00 mrr=1.00 How does a request reach the database?

definition accuracy:        1.00
relationship accuracy:      1.00
import resolution accuracy: 1.00
mean recall@k:              0.95
mean reciprocal rank:       0.89
context tokens:             90 (baseline 182, 50.5% reduction)
initial indexing:           3.7 ms
incremental indexing:       0.5 ms
embedding cache hit rate:   0.89
```

**What these numbers say:**

- **Compiler correctness is perfect and vector-independent**, as it should be: definition/relationship/import-resolution accuracy are `1.00` in both runs, because those are computed against the semantic index directly (Phases 2-6), never through retrieval. Vector search cannot make the compiler more or less correct, and the results confirm it doesn't.
- **Vector search substantially improves retrieval quality on natural-language queries.** Without it, all three semantic questions score `0.00` recall — the fixture's source text never literally contains words like "authentication" or "database", so FTS has nothing to match and exact-symbol lookup doesn't apply. With real embeddings, the same three questions score `0.67`-`1.00` recall and `1.00` MRR (the truly relevant symbol is always ranked first when found at all). This is the concrete evidence for "hybrid retrieval has measurable quality" in `# 38. Definition of v1` — it is not asserted, it is measured.
- **"What imports auth.ts?" is a real, quantified gap** — not a bug, a missing capability. `import_resolution_accuracy` is `1.00` (the compiler correctly resolves `api.ts`'s import of `login` to `auth.ts`), but retrieval recall is `0.00` without vectors and, even with real embeddings, MRR is only `0.20` (the correct answer, `api.ts`, is retrieved but ranked _last_ out of 5 — `HybridRetriever` has no dedicated "importers of X" route, so the query falls through to generic hybrid search, which surfaces symbols _defined in_ `auth.ts` rather than symbols that _import_ it). Recorded here instead of tuned away or hidden behind a favorable fixture. Candidate follow-up: a dedicated `graph_importers` strategy backed by `indexing.diff.importers_of`, mirroring how `graph_callers`/`graph_callees` already work. *(Resolved by Phase 23 — see "Results after Phase 23" below; the follow-up was implemented against `resolved_import_references` rather than `importers_of`.)*
- **Token reduction is budget-dependent, not a fixed percentage** — 91.8% without vectors (fewer, more targeted candidates make it into the token-budgeted `ContextPack`) vs. 50.5% with them (more candidates surface, so more of the budget gets used, though absolute context size stays well under the 800-token cap either way). Either number would be misleading quoted alone; both are reported so the tradeoff is visible. This is precisely why `# 28. Phase 22` opens with "do not claim '95% token savings' without measurement" — the honest answer is "it depends on the budget and the query," not a single headline number.
- **Embedding cache hit rate of 0.89** confirms Phase 18/11's core promise on real chunks: editing one symbol's body in a 9-chunk repo caused exactly 1 chunk to be re-embedded — the other 8 were never even re-enqueued, let alone re-sent to the model.
- Indexing latency (single-digit milliseconds either way) is not yet meaningful at benchmark-fixture scale; it exists in the suite so a real regression (a change that makes indexing quadratic, say) would show up as an order-of-magnitude jump, not to characterize production-scale latency.

### Results after Phase 23 (captured 2026-08-21)

Same fixture, same commands, after the Phase 23 importers strategy landed.

**Without vector search** (`ckg eval`):

```text
[structural] PASS recall@k=1.00 mrr=1.00 Where is createAuth defined?
[structural] PASS recall@k=1.00 mrr=1.00 Who calls login?
[structural] PASS recall@k=1.00 mrr=1.00 What does login call?
[structural] PASS recall@k=1.00 mrr=1.00 What imports auth.ts?
[semantic  ] -    recall@k=0.00 mrr=0.00 How does authentication work?
[semantic  ] -    recall@k=0.00 mrr=0.00 Where is token validation implemented?
[semantic  ] -    recall@k=0.00 mrr=0.00 How does a request reach the database?

definition accuracy:        1.00
relationship accuracy:      1.00
import resolution accuracy: 1.00
mean recall@k:              0.57
mean reciprocal rank:       0.57
context tokens:             20 (baseline 182, 89.0% reduction)
initial indexing:           4.4 ms
incremental indexing:       0.6 ms
embedding cache hit rate:   0.00
```

**With vector search** (`ckg eval --embed`):

```text
[structural] PASS recall@k=1.00 mrr=1.00 What imports auth.ts?  (was mrr=0.20)
[semantic  ] -    recall@k=0.67 mrr=1.00 How does authentication work?
[semantic  ] -    recall@k=1.00 mrr=1.00 Where is token validation implemented?
[semantic  ] -    recall@k=1.00 mrr=1.00 How does a request reach the database?

mean recall@k:              0.95   (unchanged)
mean reciprocal rank:       1.00   (was 0.89)
context tokens:             77 (baseline 182, 57.7% reduction)
embedding cache hit rate:   0.89
```

- **The "What imports auth.ts?" gap is closed**: recall 0.00 → 1.00 and MRR 0.00 → 1.00 without vectors; with vectors, MRR 0.20 → 1.00 — the importing module (`api.ts`) is now the top-ranked hit instead of the last of five. Mean MRR across all seven questions reached 1.00 with vectors. All other metrics moved within noise (compiler accuracies stay 1.00 and vector-independent).

### Decision notes

- Semantic questions get a Recall@K/MRR score (against hand-authored `relevant` sets) but never a `correct` boolean: grading whether "How does authentication work?" was _answered well_ needs a human or an LLM judge, which is explicitly out of scope (`# 37. What Not To Build Yet` rules out LLM-based reranking/judging as a v1 dependency). The retrieval-quality score is a legitimate proxy; a correctness verdict would not be.
- No pytest-benchmark or statistical latency analysis: the fixture is tiny by design (fast, deterministic, no flakiness budget needed) and a single wall-clock sample per run is enough to catch a regression order of magnitude, which is what this suite is for. Rigorous perf benchmarking, if ever needed, is a different tool built on top of the same `run_evaluation()` measurements.
- The unit/integration tests in `tests/test_evaluation_runner.py` use `FakeEmbeddingProvider` (hash-based, not semantically meaningful), so they assert weaker things than the real numbers above — e.g. they check the importers-question recall is merely _not asserted to be nonzero_ rather than pinning `0.20` MRR, and don't assert the semantic questions score well, since a fake provider has no real notion of meaning. The **Results** section above, captured with the real model, is the trustworthy read on retrieval quality; the test suite's job is only to keep the measurement machinery itself correct and fast without a network dependency.

---

# 29. Phase 23 — Importers Retrieval Strategy

Status: COMPLETE

Goal:

> "What imports auth.ts?" must retrieve the importing module's symbols as
> top-ranked results through a dedicated strategy, instead of falling
> through to generic hybrid search.

This is the measured gap from Phase 22 (`# 28` Results): the question
scores `recall@k = 0.00` without vectors and `MRR = 0.20` with them,
because no routing regex matches import intent, so the query lands in
generic hybrid search which surfaces symbols _defined in_ `auth.ts`
rather than symbols that _import_ it.

## Task 23.1 — Intent Pattern and Routing

File:

```text
retrieval/hybrid_retriever.py
```

Add alongside the three existing patterns (lines 19–23):

```python
WHAT_IMPORTS_PATTERN = re.compile(
    r"(?:what|who|which)\s+(?:file|module)?s?\s+imports\s+([A-Za-z_][\w.]*)"
    r"|importers of\s+([A-Za-z_][\w.]*)",
    re.IGNORECASE,
)
```

Notes:

- The capture group allows dots so `auth.ts` captures as a full module
  reference, unlike the symbol-name captures of the existing patterns.
- Routing order in `retrieve()`: after `WHERE_IS_PATTERN`, before the
  generic `_hybrid_search` fallback. There is no overlap with
  `WHAT_CALLS_PATTERN` ("what does X call") or `WHO_CALLS_PATTERN`.
- The captured target is resolved in one of two modes:
  1. **Module mode** — target contains a dot (e.g. `auth.ts`). Match
     against `Document.relative_path` by exact match on relative path,
     falling back to basename equality.
  2. **Symbol mode** — target is a bare identifier (e.g. `login`).
     Resolve via `self.symbol_index.lookup_by_name(target)`; process
     **all** distinct resulting symbols (same loop discipline as
     `_graph_callers`; ambiguity is not an error here because every
     same-named symbol legitimately has importers).

### Tests

- Pattern matches: `what imports auth.ts?`, `who imports auth`,
  `which files imports x` (grammar variants are acceptable collateral),
  `importers of auth.ts`. Does **not** match `what does auth import`
  (callee direction) and does not alter existing routings.
- Module mode and symbol mode each produce candidates; unknown module
  and unknown symbol both return `candidates=[]` with
  `strategy="graph_importers"` (no guessing, Gate E).

---

## Task 23.2 — Importer Candidate Selection

File:

```text
retrieval/hybrid_retriever.py
```

New private method `_graph_importers(target_text)` returning
`HybridRetrieval(strategy="graph_importers", query=target_text, ...)`.

Importer discovery uses only `self.resolved_imports` (already injected;
no new constructor parameter — `ResolvedImportReference.target_document`
carries the target document):

```text
module mode:  ri.target_document matched against target per Task 23.1
symbol mode:  ri.target_symbol.symbol_id ∈ seed symbol ids
```

Candidate emission per distinct importing document
(`ri.import_reference.document_id`), deterministic order:

1. Module-scope symbols of the importing document whose names appear in
   that document's `Export` rows (`self.exports`), sorted by
   `qualified_name`.
2. Then remaining module-scope symbols (`parent_symbol_id is None`),
   sorted by `qualified_name`.

Every candidate is built via the existing `_from_symbol(symbol,
sources=("graph",))`. Documents with zero module-scope symbols are
skipped. Duplicates across multiple seeds/imports collapse by
`stable_key` (first wins).

Rationale for emitting the importer's module surface rather than one
symbol: chunk identity is per-symbol, but the question targets a
_file_; the exported module scope is its semantic surface, consistent
with how Phase 15 treats document-scoped imports/exports.

### Tests

Stub-driven (`tests/test_hybrid_retrieval.py`):

- Module mode: two documents import `auth.ts`; both documents'
  exported module-scope symbols come back tagged `("graph",)`;
  `auth.ts`'s own symbols do not appear.
- Symbol mode: querying a function name returns importers of the
  defining file; ambiguous name processes all seeds; unknown name → empty.
- Ordering is deterministic across two calls.
- A document importing a module it gets nothing resolvable from
  (`target_symbol=None`, unresolved module) contributes nothing in
  symbol mode.

Integration (`tests/test_hybrid_retrieval.py`, via
`reindex_index` → `build_hybrid_retriever`, mirroring the existing
caller-intent integration test):

- Fixture equivalent to the benchmark repo: `retrieve("What imports
  auth.ts?")` returns candidates whose `relative_path == "api.ts"` at
  rank 1, strategy `"graph_importers"`.

### Done when

- All tests pass; existing router/retriever tests unchanged.
- Re-run `ckg eval` and `ckg eval --embed`; record actual numbers in
  `# 28` Results next to the old ones. Required direction: importers
  question improves over recall 0.00 / MRR 0.20. Do not tune weights to
  chase a number; the dedicated route either works or it doesn't.

## Implemented

- `retrieval/hybrid_retriever.py` — `WHAT_IMPORTS_PATTERN`
  (`(?:what|who|which)\s+(?:files?|modules?)?\s*imports\s+([A-Za-z_][\w.]*)` |
  `importers of\s+([A-Za-z_][\w.]*)`, case-insensitive) routed in
  `retrieve()` after `WHERE_IS_PATTERN`, before the hybrid fallback; the
  capture allows dots so `auth.ts` captures whole, and
  `what does auth import` still routes to generic hybrid.
- `_graph_importers(target)` resolves importers via
  `_resolved_importers`: module mode (dot in target → distinct
  `ResolvedImportReference.target_document`s matching exact
  `relative_path` or basename) or symbol mode (all distinct symbols from
  `lookup_by_name`, matched by `target_symbol.symbol_id`). No new
  constructor parameters — uses the Phase 15 injected
  `resolved_imports`/`exports`.
- Candidate emission: per importing document, exported module-scope
  symbols first, then remaining module-scope symbols (each group sorted
  by `qualified_name`), documents ordered by path; all tagged
  `("graph",)` via `_from_symbol`; deduplicated by `stable_key`;
  documents without module-scope symbols skipped. Unknown targets →
  empty candidates (Gate E).

### Tests

- `tests/test_hybrid_retrieval.py::TestImportersStrategyStubs` (7):
  module-mode surface per importer excluding the imported file's own
  symbols; exported-before-private ordering within a document;
  deterministic document ordering across calls and phrasings; unknown
  module → empty; symbol mode resolves both importers; unknown symbol →
  empty; callee-direction query not routed here.
- Integration (+1): via `reindex_index` → `build_hybrid_retriever`,
  `"What imports auth.ts?"` returns only `api.ts` candidates with
  `run` ranked first.

### Result

All 367 tests pass (was 359). Eval re-measured (`# 28`, post-Phase-23
addendum): the importers question went from recall 0.00 / MRR 0.00 to
**1.00 / 1.00** without vectors, and MRR 0.20 → **1.00** with vectors.

---

# 30. Phase 24 — Type-Level Symbols + IMPLEMENTS

Status: COMPLETE (2026-08-24)

Goal:

> `interface` and `type alias` declarations become first-class symbols
> and exports; imported type names resolve to symbols; `class X
> implements Y` emits IMPLEMENTS edges.

This removes the "Type-level constructs" bullet from README **Not Yet
Modelled** and unblocks the IMPLEMENTS relationship deferred during the
EXTENDS work (its targets could not resolve without type symbols).

Constraints inherited from earlier phases:

- Gate E: unresolved/ambiguous type references never produce edges.
- Rule 1.5: no chunk/embedding-text change in this phase (extends/
  implements facts stay out of chunks until retrieval evidence justifies
  a full re-embed).
- No schema migration: kinds persist as enum `.value` TEXT.

---

## Task 24.1 — AST Inspection

Fixtures (print ASTs before writing any handler, rule 1.3):

```ts
interface Shape { area(): number }
interface Named extends Shape { name: string }
export interface Point { x: number; y: number }
type Id = string
type Callback<T> = (value: T) => void
export type Status = "active" | "inactive"
class Impl implements Shape {}
```

Record: node types (`interface_declaration`, `type_alias_declaration`
expected), name node types, heritage clause shape under interfaces,
member structure of interface bodies, and how `export interface` /
`export type` wrap these nodes. Do not proceed until recorded.

### Implemented

Recorded against `tree_sitter_typescript.language_typescript()`:

| Construct | Actual AST |
|---|---|
| `interface Shape {...}` | `interface_declaration`; `name` field is a `type_identifier`; `body` field is `interface_body` |
| `type Id = string` | `type_alias_declaration`; `name` field `type_identifier`; **`value` field** holds the RHS; optional `type_parameters` |
| interface members | `property_signature` (fields `name`, `type`) and `method_signature` (fields `name`, `parameters`, `return_type`) |
| `interface Named extends Shape` | `extends_type_clause` — **not** `extends_clause` — with one `type_identifier` per base |
| `class Impl implements Shape` | `class_heritage` → `implements_clause` → one `type_identifier` per target |
| `class Both extends Base implements Shape, Named` | `class_heritage` holds `extends_clause` (child is a plain `identifier`) and `implements_clause` side by side |
| `export interface` / `export type` | `export_statement` wrapping the declaration, identical in shape to `export class` |

**Three deviations from this section's assumptions (Gate A):**

1. **Interface members do not extract cleanly.** `property_signature` /
   `method_signature` are unknown to `handle_variable_declarator` /
   `handle_method`. Per Task 24.2's own rule, members stay inside the
   interface signature rather than becoming half-extracted child symbols.
2. **`extends_type_clause`.** `in_extends_clause` matched only
   `extends_clause`, so `interface A extends B` would have emitted
   nothing even once interfaces became symbols. Handled — see Task 24.9.
3. **`type_identifier` was never extracted at all.** `reference_extractor.visit`
   handled only `identifier` / `property_identifier` / `member_expression`.
   This — not the missing symbols — is the mechanical reason `implements`
   stayed silent. Task 24.5 admits the node type narrowly.

---

## Task 24.2 — Symbol Kinds and Extraction

Files:

```text
models/entities/symbol_kind.py          (+ INTERFACE, + TYPE_ALIAS)
analysis/symbol_handlers/interface.py   (new, mirrors classes.py)
analysis/symbol_handlers/type_alias.py  (new)
analysis/registry.py                    (replace the two stub comments)
```

- `qualified_name`, `stable_key`, `content_hash` flow through the
  existing `build_symbol` chain unchanged.
- Interface members become child symbols only if they extract cleanly
  as METHOD/VARIABLE via existing handlers; if member extraction needs
  new node handling, keep members inside the interface signature
  instead and note it — do not half-extract.

### Implemented

- `models/entities/symbol_kind.py` — `INTERFACE = "interface"`,
  `TYPE_ALIAS = "type_alias"`.
- `analysis/symbol_handlers/interface.py` and `.../type_alias.py` mirror
  `classes.py`; both declarations expose a `name` field, so no special
  casing was needed and `build_symbol` carries `qualified_name`,
  `stable_key`, `content_hash` and `signature_hash` through unchanged.
- `analysis/registry.py` — the two stub comments became real entries.
- Interface members are **not** child symbols (Task 24.1 deviation 1).
- Registering the node types also flipped `creates_symbol` and
  `is_declaration_name`, so interfaces now stop the reference walk and
  their own names are suppressed. `test_pipeline_parity.py` and
  `test_name_resolution.py` pass unchanged.

### Fixed while testing

Interface member names are `property_identifier` nodes whose parent
(`property_signature` / `method_signature`) is not in `NODE_HANDLERS`, so
`is_declaration_name` returned `False` and every member name was
extracted as an identifier reference that could never resolve. Beyond the
noise, this broke incremental correctness: any edit to an interface
re-resolved its importers, because the file always carried unresolved
references. `analysis/semantic/is_declaration_name.py` now treats those
two node types as declaration sites alongside `NODE_HANDLERS`. Pinned by
`test_interface_member_names_are_not_extracted_as_references`.

---

## Task 24.3 — Signatures

File:

```text
analysis/signature.py
```

- INTERFACE: name-independent, body-free shape including public member
  surface, e.g. `interface[:{extends text}]{sorted "memberName:shape"}`
  — member names are part of the public interface (unlike parameter
  names), so they must invalidate importers when changed.
- TYPE_ALIAS: `type:<RHS source text>` (full right-hand side).
- Adjust shapes to what Task 24.1 actually shows (Gate A); update the
  Task 6.2 signature documentation when done.

### Implemented

`analysis/signature.py` gained `_interface_signature` and
`_type_alias_signature`, dispatched from `extract_signature`:

```text
INTERFACE   interface[:{comma-joined bases}]{sorted "member:shape"}
TYPE_ALIAS  type:<value field source text>
```

Member shapes reuse the existing helpers: a `method_signature` already
carries `parameters` / `return_type` fields, so `_callable_signature`
applies to it directly; a `property_signature` uses `_annotation_text`.
Members are sorted, so declaration order does not move the hash, but
member *names* are included — unlike parameter names — because they are
part of an interface's public surface and must invalidate importers.

Verified by `tests/test_interface_symbols.py::TestTypeLevelSignatures`:
determinism across builds, member rename and member type change both move
the hash, formatting-only edits and member reordering do not, and
heritage participates.

---

## Task 24.4 — Exports

File:

```text
analysis/export_handlers/declaration.py
```

Handle `export interface` / `export type Alias =` per the Task 24.1
AST findings, producing `Export` rows identical in shape to function
exports. After this task, `import { Shape } from "./shapes"` resolves
to a symbol through the existing export table + module-scope lookup
with **zero resolver changes expected** — verify, don't assume; if a
kind filter blocks it, fix the filter, not the resolver.

### Implemented

`analysis/export_handlers/declaration.py` — `interface_declaration` and
`type_alias_declaration` added to `DECLARATION_NODE_TYPES` and routed to
`_name_from_field`, which works because both expose a `name` field.

**The zero-resolver-changes prediction held, and was verified rather than
assumed.** `import { Shape } from "./shapes"` resolves to the interface
symbol with no change to the export table or the resolver, because
neither filters on `SymbolKind` — the only kind checks in the codebase
are in `analysis/signature.py` (dispatch) and
`analysis/semantic/member_resolver.py` (`SymbolKind.CLASS`, member
access). Covered by
`TestTypeLevelImportResolution::test_imported_interface_resolves_to_the_interface_symbol`.

---

## Task 24.5 — IMPLEMENTS Relationship

Files:

```text
models/entities/reference_kind.py            (+ IMPLEMENTS)
models/relationships/relationship_kind.py    (+ IMPLEMENTS = "implements")
analysis/reference_extractor.py              (+ implements_clause handling)
analysis/relationship_builder.py             (mapping += IMPLEMENTS)
```

Extractor rule: a `type_identifier` whose parent is an
`implements_clause` is extracted with `ReferenceKind.IMPLEMENTS`.
Type identifiers anywhere else stay unextracted (this is what kept
`implements` unextracted during the EXTENDS work). Multiple
implements targets yield one reference per target.

Resolution reuses the standard climb (scope → module → imports);
the builder emits `(subclass → resolved target, IMPLEMENTS)` exactly
like EXTENDS. Unresolved/ambiguous targets emit nothing (Gate E).

### Implemented

- `models/entities/reference_kind.py` — `+ IMPLEMENTS`.
- `models/relationships/relationship_kind.py` — `+ IMPLEMENTS = "implements"`.
- `analysis/semantic/reference_kind.py` — new `in_implements_clause`,
  checked next to `in_extends_clause` in `determine_reference_kind`.
- `analysis/reference_extractor.py` — `visit` admits `type_identifier`
  **only** under a heritage clause, via the new `in_heritage_clause`.
  Type positions elsewhere (annotations, generic arguments) stay
  unextracted: they have no resolvable target yet, and extracting them
  would flood the resolver with permanently-unresolved references.
- `analysis/relationship_builder.py` — one entry in
  `_RELATIONSHIP_BY_REFERENCE`.

Resolution and the builder needed no other change: `build_relationship`
already drops non-`RESOLVED` references, so Gate E holds for free, and
`implements A, B` yields two references because the clause carries one
`type_identifier` per target.

---

## Task 24.6 — Incremental Invalidation

Test in the `tests/test_incremental_indexer.py` style:

- Editing an implemented interface's member set changes its
  `interface_fingerprint` entry (via `signature_hash`) → implementers
  re-resolve and their IMPLEMENTS edges follow the edit.
- Editing an interface's non-exported trivia (comment/formatting) does
  not invalidate implementers.

### Implemented

`tests/test_incremental_indexer.py::TestImplementsIncrementalInvalidation`
— three cases, all passing without any change to `indexing/`:

- member rename → `signature_hash` moves → `interface_fingerprint`
  changes → implementers re-resolve and the IMPLEMENTS edge follows;
- comment/formatting edit → `resolved_references == 0`, the implementer
  file stays `UNCHANGED`, and the edge survives;
- removing the interface's `export` → the edge disappears (Gate E).

The middle case is what surfaced the member-name reference bug recorded
under Task 24.2 — it failed with `1 != 0` until that was fixed.

---

## Task 24.7 — Test Inventory

`tests/test_interface_symbols.py` (new):

- interface + type alias extracted with correct kind/qualified name
- nested interface ownership; generic alias (`Callback<T>`)
- `export interface` / `export type` produce Export rows
- cross-file `import { Shape }` resolves to the interface symbol
- missing type export stays UNRESOLVED, no edge
- signature determinism across two builds; member rename changes
  `signature_hash`, formatting-only edit does not

`tests/test_implements_relationship.py` (new):

- resolved implements → edge, source = subclass
- `implements A, B` → two edges
- extends + implements combined fixture → both edge kinds
- unresolved/ambiguous target → status recorded, no edge

Existing suites (`test_extends_relationship.py`,
`test_incremental_indexer.py`, `test_pipeline_parity.py`) must pass
unchanged except where this phase intentionally adds coverage.

### Implemented

- `tests/test_interface_symbols.py` — 17 tests across extraction,
  exports, import resolution and signatures.
- `tests/test_implements_relationship.py` — 7 tests, including
  cross-file imported interfaces and the "IMPLEMENTS is not a call"
  guard.
- `tests/test_extends_relationship.py` — one existing test intentionally
  replaced: `test_implements_clause_stays_unextracted` pinned the very
  limitation this phase removes. It is superseded by
  `test_type_identifier_outside_a_heritage_clause_stays_unextracted`,
  which pins the narrowness that still matters (annotations and return
  types produce no reference), plus a new `TestInterfaceExtends` class.

Full suite: **401 passing** (was 367). No other existing test changed.

---

## Task 24.9 — Interface Heritage (added: Task 24.1 deviation 2)

`interface A extends B` uses `extends_type_clause`, which this section
did not anticipate. Left alone, interfaces would have become symbols
whose own hierarchy was invisible — a half-finished type model.

### Implemented

- `analysis/semantic/reference_kind.py` — `in_extends_clause` matches
  both `extends_clause` (classes) and `extends_type_clause` (interfaces).
- `analysis/reference_extractor.py` — covered by `in_heritage_clause`.
- `analysis/signature.py` — `_interface_extends_text` feeds the interface
  signature, so a heritage change invalidates importers.

`interface C extends A, B` emits two EXTENDS edges. Covered by
`tests/test_extends_relationship.py::TestInterfaceExtends`.

---

## Task 24.8 — Documentation

- README: remove the type-level bullet from **Not Yet Modelled**
  (keep the type-analysis bullet); Relationship Pass current list adds
  IMPLEMENTS; Completed list gains type-level symbols.
- This file: convert Tasks 24.1–24.7 to `### Implemented` notes per
  rule 1.8, plus an Update Log entry.

### Done when

Full suite passes; README type gap removed; `ckg eval` output recorded
unchanged or improved (chunk texts untouched, so embeddings are not
invalidated).

### Implemented

- README: Symbol Pass gains INTERFACE/TYPE_ALIAS; Relationship Pass and
  the Knowledge Graph diagram gain IMPLEMENTS and note that EXTENDS now
  covers interface heritage; `CodeGraph` accessor list gains
  `base_types_of`/`subtypes_of` with the CALLS-only caveat; Completed
  gains the type-level entries; the "Type-level constructs" and "Class
  hierarchy" bullets leave **Not Yet Modelled**, replaced by an honest
  "Interface members" bullet and a widened "Type analysis" bullet.
- README *Planned* also corrected: it still listed `EXTENDS`, shipped
  before this phase.
- `# 25` Phase 19's status label corrected — it read `IN PROGRESS` while
  its own qualifier said the work was complete.

### Result

`ckg eval` and `ckg eval --embed` reproduce the post-Phase-23 numbers
**exactly**, including `embedding cache hit rate: 0.89`. That equality is
the evidence for Rule 1.5: new interface/alias symbols add new chunks,
but no existing chunk's `content_hash` moved, so nothing was re-embedded.

---

# 31. Regression Test Policy

Every bug found in production or during development becomes a fixture.

Example:

```text
tests/fixtures/regression/
    duplicate_symbol_names/
    import_alias/
    nested_scope/
    member_call/
    file_rename/
    symbol_rename/
```

Never fix the code without adding the fixture.

The fixture becomes permanent.

---

# 32. Decision Gates

An implementation agent must stop and reassess if any of these happen.

## Gate A — AST mismatch

If the actual Tree-sitter structure differs from the planned node shape:

```text
stop
inspect AST
update design
add fixture
continue
```

Do not force the existing abstraction onto the AST.

---

## Gate B — Model ambiguity

If a model starts accumulating fields such as:

```text
name
full_name
qualified_name
display_name
local_name
resolved_name
```

ask what each field means and who consumes it.

Remove duplicate concepts.

---

## Gate C — Duplicate abstraction

If two modules contain almost identical logic:

```text
compare responsibilities first
```

Only extract a shared abstraction if both consumers genuinely require the same behavior.

---

## Gate D — Performance problem

Do not optimize based on assumptions.

Measure first:

```text
parse time
DB time
embedding time
retrieval time
```

Then optimize the actual bottleneck.

---

## Gate E — Semantic uncertainty

If the resolver cannot determine the target confidently:

```text
mark unresolved / ambiguous
```

Do not guess.

False edges are worse than missing edges for code intelligence.

---

# 33. Coding Style

Match the existing style.

## Python

Prefer:

```python
def function_name(
    *,
    argument: Type,
) -> ReturnType:
```

Use:

- dataclasses with `slots=True`
- type annotations
- explicit names
- small functions
- keyword-only arguments for multi-argument semantic APIs

Avoid:

- large utility classes
- hidden global state
- generic `manager.py`
- broad `utils.py`
- unnecessary inheritance
- premature registries

---

# 34. Module Responsibilities

```text
ingestion/
    discover and load files

parsing/
    parse source into Tree-sitter trees

models/
    semantic data structures

analysis/
    semantic extraction and resolution

graph/
    in-memory graph operations

indexing/
    in-memory lookup indexes

storage/
    SQLite persistence

chunking/
    semantic retrieval units

embeddings/
    embedding provider abstraction

retrieval/
    exact / FTS / vector / graph retrieval

evaluation/
    correctness and retrieval benchmarks
```

Do not move a module across layers merely to make an import path look shorter.

---

# 35. Current Tasks

Update this section as work progresses.

## Completed

- [x] Document loading
- [x] Tree-sitter parsing
- [x] ParsedDocument IR
- [x] Parse-once pipeline
- [x] Symbol extraction
- [x] Symbol ownership
- [x] SymbolIndex
- [x] Reference extraction
- [x] Reference classification
- [x] Basic reference resolution
- [x] Scope-aware reference resolution
- [x] Local variable extraction / shadowing
- [x] Resolution status (resolved / unresolved / ambiguous)
- [x] CALL relationship builder
- [x] Type-level symbols (Phase 24: `INTERFACE` / `TYPE_ALIAS` declarations, their signatures and exports; imported type names resolve to symbols)
- [x] EXTENDS relationship builder (resolved `class X extends Y` and `interface X extends Y` heritage)
- [x] IMPLEMENTS relationship builder (Phase 24: resolved `class X implements Y`, one edge per implemented interface)
- [x] In-memory CodeGraph
- [x] Import pass (produces `import_references` in the pipeline)
- [x] Import module resolver (relative paths, ../, extensions, index.ts)
- [x] Import resolver pass wired into the pipeline
- [x] Import extraction for common TS/JS import forms
- [x] DocumentIndex
- [x] Module-level import resolution tested in isolation
- [x] Export model and export extraction
- [x] Export pass wired into the pipeline
- [x] Resolve imports to actual exported symbols (via export table)
- [x] Cross-file name resolution (references resolve through imports)
- [x] Member-expression resolution (access paths + namespace/this/class member calls)
- [x] Relationship deduplication (stable `(source, target, kind)` key, set internally in the graph)
- [x] Stable identities (qualified names, content/signature hashes, deterministic stable keys)
- [x] Symbol fingerprints (name-independent signatures, body-excluding)
- [x] Confidence-based rename / move matching across index runs
- [x] SQLite persistence (schema, db layer, repositories, atomic transactions, `persist_index`/`load_index` round-trip)
- [x] Incremental indexing (file state inventory, `mtime`-hint / hash-based change detection, selective re-resolution, interface-aware dependency invalidation)
- [x] Hierarchical / Merkle hashing (deterministic content+name subtree hashes over the repo tree)
- [x] Graph-aware retrieval (Phase 15: budgeted 1-hop seed neighborhoods over callers/callees/parent/imports/exports, 2-hop only for no-call-edge seeds)
- [x] Heuristic reranking (Phase 16: deterministic feature scoring — exact/path/kind/FTS/vector/graph-distance/relationship — graph-expanded candidates compete in `top_k`)
- [x] Context builder (Phase 17: budgeted `ContextPack` — primary/supporting definitions, important relationships, file paths, symbol-bounded source excerpts, hard token budget)
- [x] Async embedding worker / incremental embedding (Phase 18: PENDING/PROCESSING/DONE/FAILED queue, retry-only-failed, no re-embedding of unchanged content hashes)
- [x] Ignore rules (Phase 19: `.gitignore`/`.ckgignore` honored by file discovery and the Merkle walk)
- [x] Index generations (Phase 20: atomic generation counter published in the same transaction as the snapshot it labels)
- [x] Local CLI (Phase 21: `ckg index/status/search/definition/callers/callees/imports/context/eval`)
- [x] Evaluation suite (Phase 22: fixed benchmark repo + questions, compiler-accuracy + retrieval-quality + latency + cache-hit-rate metrics, `ckg eval`)
- [x] MCP / agent protocol integration (Phase 21: `mcp_server.py`, eight tools over stdio, wrapping the same `cmd_*` functions the CLI uses)

## In Progress

(none)

## Next

No phase is scheduled. **Every item in `# 38. Definition of v1` is now
met**, including "hybrid retrieval has measurable quality", which the
post-Phase-23 `ckg eval` numbers in `# 28` settle: mean recall 0.95,
mean MRR 1.00 with vectors, measured rather than asserted.

~~Phase 23 (`# 29`) — importers retrieval strategy~~ — COMPLETE
(2026-08-21); the importers question now scores recall 1.00 / MRR 1.00
with and without vectors.

~~Phase 24 (`# 30`) — type-level symbols + IMPLEMENTS~~ — COMPLETE
(2026-08-24); interfaces and type aliases are symbols and exports,
type-only imports resolve, and IMPLEMENTS / interface-EXTENDS edges are
emitted. Eval unchanged, so no embeddings were invalidated.

Candidates for the next phase, none scheduled, in rough order of the
evidence behind them:

1. **Benchmark on a real repository.** The eval fixture is 4 files and
   9 chunks. Every latency number and the token-reduction percentage are
   honestly labelled as not yet meaningful at that scale, and the
   "Interface members" and reranker-weight decisions have no real-repo
   evidence behind them. This is the gap most likely to be hiding
   something.
2. **Re-export resolution** (`export { x } from` / `export * from`) —
   deferred since Phase 2; currently produces no export rows at all, so
   barrel-file repositories under-resolve silently.
3. **Incremental persistence** — each run rewrites the whole snapshot.
   Gate D applies: measure before optimizing.
4. `ckg` console-script packaging; background embedding worker.

---

# 36. Immediate Execution Order

The implementation agent should execute exactly this order unless a decision gate requires a change:

```text
1. ParsedDocument model
2. Parse pass
3. Migrate Symbol Pass
4. Migrate Reference Pass
5. Migrate Import Pass
6. Migrate any remaining AST-based passes
7. Add import pass tests
8. Wire import resolver pass
9. Add export model
10. Add export extraction
11. Resolve imported symbols
12. Fix scope-aware reference resolution
13. Add member-expression resolution
14. Stabilize CodeGraph
15. Add relationship deduplication
16. Add stable identities/fingerprints
17. Add SQLite schema
18. Add SQLite repositories
19. Persist BuildResult
20. Add file hashing/change detection
21. Add incremental indexing
22. Add Merkle/hierarchical hashes
23. Add semantic chunk builder
24. Add content-addressed chunk cache
25. Add embedding provider abstraction
26. Add local embedding store
27. Add FTS5 retrieval
28. Add vector retrieval
29. Add hybrid retrieval
30. Add graph expansion
31. Add heuristic reranking
32. Add context builder
33. Add async embedding updates
34. Add index generations
35. Add CLI
36. Add MCP/agent integration
37. Add evaluation suite
38. Add importers retrieval strategy (Phase 23)
39. Add type-level symbols + IMPLEMENTS relationship (Phase 24)
```

All 39 steps are complete as of 2026-08-24. See `# 35. Next` for
unscheduled candidates.

---

# 37. What Not To Build Yet

Do not add these before the required phases are stable:

```text
cloud vector databases
cloud embeddings
Neo4j / separate graph database
multi-language support
training custom embedding models
LLM-based query rewriting
LLM-based reranking
agent orchestration
UI dashboards
```

They may become useful later.

They are not prerequisites for a correct local-first CKG.

---

# 38. Definition of v1

v1 is complete when:

- TS/JS indexing is reliable
- files are parsed once per run
- symbols/imports/exports/references are resolved for common cases
- graph relationships are deterministic
- the graph persists in SQLite
- incremental indexing works
- unchanged chunks reuse their embeddings
- FTS and vector retrieval work locally
- graph expansion works
- hybrid retrieval has measurable quality
- context building respects a token budget
- evaluation is repeatable
- an agent can query the local index

---

# 39. Update Log

After each task, append:

```md
## YYYY-MM-DD — Task X.Y

Status: COMPLETE

Files changed:

- ...

Implementation:

- ...

Tests:

- ...

Result:

- ...

Decision / deviation:

- ...

Next:

- ...
```

If a task changes architecture, record why.

## 2026-09-02 — Hardening: interface members, re-exports, HAS_TYPE, delta persistence, secrets, coverage

Status: COMPLETE

Files changed:

- `analysis/symbol_handlers/interface_members.py` (new), `analysis/registry.py` (interface members as child symbols), `tests/test_interface_symbols.py` flipped `are_not_extracted`→`are_extracted_as_child_symbols` (`Shape.{area,name}` now `METHOD`/`VARIABLE` children)
- `analysis/export_handlers/re_export.py` (new), `analysis/export_registry.py` composite `_ts_export_statement`, `tests/test_re_export.py` (new), `tests/test_export_pass.py` updated `reexport_from_is_deferred`→`is_now_modeled` (`("login",None)`/`("*",None)`)
- `models/entities/reference_kind.py` (+HAS_TYPE, +RETURNS), `analysis/semantic/reference_kind.py` (`_in_type_annotation`/`_in_return_type`), `analysis/reference_extractor.py` volume guard 20/owner, `tests/test_extends_relationship.py` `stays_unextracted`→`is_now_has_type` (expects resolved `Shape`)
- `storage/index_store.py` `persist_index(..., reresolve_paths=)` + `_clear_analysis_tables_for_paths`, `indexing/indexer.py:189` wires `plan.reresolve`
- `parsing/tree_sitter_parser.py:8` thread-local `Parser`, `storage/db.py:11` `PRAGMA synchronous=NORMAL/temp_store=MEMORY/cache_size=-64000`, `indexing/resource_governor.py:1` adaptive batch
- `indexing/secrets.py:1` (`AKIA/ghp/PRIVATE KEY`), `ingestion/loader.py:69` `redact_secrets`+`should_skip_file_content`, `session_memory/service.py:24` `_bounded` redacts, `tests/test_secrets.py:1`
- `pyproject.toml:36` `pytest-cov` + `[tool.coverage.run]` branch, `[tool.coverage.report] fail_under=65`, `tests/conftest.py:1` `tmp_db` WAL cleanup, `tests/test_watcher.py:9` `@pytest.mark.slow`, `.github/workflows/ci.yml:57` `pytest --cov --cov-fail-under=65`
- `retrieval/hybrid_retriever.py:55` `PER_FILE_CAP_CANDIDATES`, `retrieval/context_builder.py:28` `ContextPack.baseline_tokens`, `retrieval/index_queries.py:67` honest baseline, `ckg/mcp_server.py:265` fixes always-0
- `README.md` token methodology box `retrieval/tokenizer.py:15` `o200k_base` + `benchmarks/run_external.py` + `evaluation/external.py:184` ground-truth files

Result: 612 passed, 1 skipped, 82.93% cov (gate 65). Still requires `benchmarks/run_external.py --recompute` on real repos before publishing `X%`.

## 2026-08-24 — Phase 24 Type-Level Symbols + IMPLEMENTS

Status: COMPLETE

Files changed:

- `models/entities/symbol_kind.py` (+INTERFACE, +TYPE_ALIAS),
  `models/entities/reference_kind.py` (+IMPLEMENTS),
  `models/relationships/relationship_kind.py` (+IMPLEMENTS)
- `analysis/symbol_handlers/interface.py`, `.../type_alias.py` (new),
  `analysis/registry.py`, `analysis/signature.py`,
  `analysis/export_handlers/declaration.py`,
  `analysis/reference_extractor.py`,
  `analysis/semantic/reference_kind.py`,
  `analysis/semantic/is_declaration_name.py`,
  `analysis/relationship_builder.py`
- `graph/code_graph.py` (prerequisite fix, separate commit)
- `tests/test_interface_symbols.py`, `tests/test_implements_relationship.py`
  (new); `tests/test_extends_relationship.py`,
  `tests/test_incremental_indexer.py`, `tests/test_code_graph.py`
- `README.md`, `IMPLEMENTATION.md`

Implementation:

- As specified in `# 30`, with three Gate A deviations recorded under
  Task 24.1 and one added task (24.9, interface heritage).
- Exports and import resolution needed no resolver change, as the spec
  predicted — verified, not assumed.

Tests:

- 34 new tests; full suite 401 passing (was 367).

Result:

- `ckg eval` and `ckg eval --embed` reproduce the post-Phase-23 numbers
  exactly, cache hit rate included. Rule 1.5 held: new symbols added new
  chunks, no existing chunk text moved.
- End-to-end spot check on a scratch TS repo: `Shape (interface)` and
  `ShapeId (type_alias)` are searchable symbols, `Circle --implements-->
  Shape/Named` and `Named --extends--> Shape` round-trip through SQLite,
  and both type-only imports resolve to interface symbols.

Decision / deviation:

- **Prerequisite fix, committed separately.** `callers_of`/`callees_of`
  did not filter on relationship kind, so since EXTENDS landed they had
  been reporting subclasses as callers — leaking into the CLI, the MCP
  tools, graph expansion, reranking, and chunk embedding text. IMPLEMENTS
  would have compounded it. Both now filter to CALLS, with
  `base_types_of`/`subtypes_of` added for hierarchy queries. This changes
  the chunk text of any class involved in an `extends`, so those chunks
  re-embed once; the eval fixture has no classes, which is also why the
  benchmark never caught the bug.
- **One existing test intentionally replaced.**
  `test_implements_clause_stays_unextracted` pinned the exact limitation
  this phase removes. Replaced by a test pinning the narrowness that
  still matters: a `type_identifier` outside a heritage clause produces
  no reference.
- **Interface members are not child symbols** (Task 24.1 deviation 1),
  per Task 24.2's own "do not half-extract" rule. Recorded in README
  **Not Yet Modelled** rather than papered over.
- **A bug found while testing became a fixture** (`# 31`): interface
  member names were extracted as unresolvable identifier references,
  which silently invalidated importers on every interface edit.

Next:

- No phase scheduled; v1 is complete. See `# 35. Next` for candidates —
  benchmarking on a real repository is the most valuable.

## 2026-08-21 — Phase 23 Importers Retrieval Strategy

Status: COMPLETE

Files changed:

- retrieval/hybrid_retriever.py (`WHAT_IMPORTS_PATTERN`, routing, `_graph_importers` / `_resolved_importers` / `_target_documents` / `_importer_surface_symbols`)
- tests/test_hybrid_retrieval.py (`TestImportersStrategyStubs`, 7 stub tests; 1 integration test; `IMPORTERS` fixture)
- IMPLEMENTATION.md (`# 29` Implemented notes, `# 28` post-Phase-23 results, `# 35` Next)

Implementation:

- As specified in `# 29`: intent regex routed before the hybrid fallback; module mode matches `target_document.relative_path` exactly or by basename; symbol mode matches all distinct same-named symbols via `target_symbol.symbol_id`; candidates are each importer's exported module-scope symbols (then remaining module scope), ordered exported-first within a document and by document path across documents; deduplicated by `stable_key`; tagged `("graph",)`. No constructor changes — reuses Phase 15's injected `resolved_imports`/`exports`.

Tests:

- 8 new tests (7 stub + 1 integration); full suite 367 passing (was 359).

Result:

- Eval: importers question recall 0.00 → 1.00 and MRR 0.00 → 1.00 without vectors; MRR 0.20 → 1.00 with vectors; mean MRR with vectors now 1.00. Numbers recorded in `# 28` Results after Phase 23.

Decision / deviation:

- Used the injected `resolved_import_references` directly instead of the spec's original `importers_of` suggestion: `importers_of(import_references, documents_by_id)` maps module paths to importer ids but would need a document-id → path map the retriever does not hold, while `ResolvedImportReference.target_document` already carries everything needed. Same semantics, one less dependency.
- "which files imports X" grammar oddity accepted per spec; the canonical phrasings all match.

Next:

- Phase 24 type-level symbols + IMPLEMENTS (`# 30`).

## 2026-08-21 — Plan authored: Phase 23 + Phase 24

Status: SPEC AUTHORED (no code change)

Files changed:

- IMPLEMENTATION.md only (`# 29` Phase 23, `# 30` Phase 24; sections
  formerly numbered 29–37 renumbered to 31–39 with all cross-references
  updated; `# 35` Next and `# 36` execution order extended)

Content:

- Phase 23 specifies the importers retrieval strategy against the
  measured gap in `# 28` Results (importers question: recall 0.00
  without vectors, MRR 0.20 with). Routing regex, module-mode vs
  symbol-mode target resolution, candidate selection from the importer's
  exported module scope, and the required eval re-measurement are all
  fixed in the spec.
- Phase 24 specifies type-level symbols (`INTERFACE`, `TYPE_ALIAS`),
  their exports and signatures, and the IMPLEMENTS relationship deferred
  from the EXTENDS work. AST inspection (Task 24.1) is a mandatory
  predecessor per rule 1.3; chunk texts are explicitly out of scope.

Decision / deviation:

- Phases are ordered retrieval-fix-first (Phase 23 before the larger
  Phase 24) because its payoff is already quantified, not because of
  dependency — neither phase depends on the other.

## 2026-08-21 — EXTENDS relationship

Status: COMPLETE

Files changed:

- models/entities/reference_kind.py (`EXTENDS` added)
- models/relationships/relationship_kind.py (`EXTENDS` added)
- analysis/semantic/reference_kind.py (`in_extends_clause`; heritage identifiers classified as `ReferenceKind.EXTENDS`)
- analysis/relationship_builder.py (kind-mapped `build_relationship`; emits `CALLS` and `EXTENDS`)
- tests/test_extends_relationship.py (new)
- tests/test_incremental_indexer.py (extends-edge survival across base-class body edit)
- README.md (Knowledge Graph, Relationship Pass, Current Status)

Implementation:

- AST inspection first (rule 1.3): `class_heritage` contains an `extends_clause` whose value is a plain `identifier`, so the existing reference walk already extracted heritage names — they were only misclassified as generic `IDENTIFIER`. `determine_reference_kind` now returns `EXTENDS` when the node's parent is an `extends_clause`.
- `implements_clause` children are `type_identifier`s, which the extractor does not handle; they stay unextracted. IMPLEMENTS is deferred until type-level symbols exist — until then its targets cannot resolve, and emitting machinery with no resolvable targets would be speculative (rule 1.5).
- Resolution needed no change: single-path references resolve kind-agnostically through scope → module → imports. Gate E applies unchanged: unknown base → UNRESOLVED, ambiguous base → AMBIGUOUS, neither produces an edge.
- `relationship_builder.build_call_relationship` became kind-mapped `build_relationship` (`CALL → CALLS`, `EXTENDS → EXTENDS`); source is always the reference owner (the subclass), target the resolved symbol. Graph deduplication by `(source, target, kind)` is unchanged. Persistence needs no migration: relationship kinds round-trip as enum `.value` TEXT.

Tests:

- `test_extends_relationship.py` (11): heritage extraction + classification; no-heritage class extracts nothing; implements stays unextracted; same-file edge; cross-file imported-base edge; two subclasses → two distinct edges; CALLS unchanged; unknown/ambiguous base → no edge; module-scope shadowing of an imported base resolves locally.
- `test_incremental_indexer.py` (+1): editing the base class body keeps the EXTENDS edge without re-resolving the untouched subclass (signature excludes bodies, so no interface invalidation fires).

Result:

- 359 tests pass (was 348). The graph now emits `CALLS` and `EXTENDS`.

Decision / deviation:

- Semantic chunks deliberately do not embed extends facts: it would change every chunk's `content_hash` and force a full re-embed for unproven retrieval value (rule 1.5). Revisit when retrieval evidence justifies it.

## 2026-08-21 — Refactor: make `models` a leaf layer

Status: COMPLETE

Files changed:

- models/build_result.py -> analysis/build_result.py
- models/indexing_context.py -> analysis/indexing_context.py
- 22 import sites updated

Problem:

- `models/build_result.py` imported `graph.CodeGraph` and `indexing.SymbolIndex`; `models/indexing_context.py` imported three indexes from `indexing`. `# 32` describes `models/` as "semantic data structures", but it depended on two higher layers, which put every package-level cycle in the codebase through it. `BuildResult` had already worked around one of these with a `TYPE_CHECKING` guard for `SemanticChunk`.

Implementation:

- Neither type is a semantic data structure: `BuildResult` is the pipeline accumulator and `IndexingContext` is the shared pass state, both mutated by passes. That is `analysis/`'s responsibility, so both moved there. `models/` now holds only entity dataclasses and imports no other layer.
- Verified no module-level cycle is introduced: `indexing/{symbol,document,export}_index.py` and `graph/code_graph.py` import only `models.entities` / `models.relationships`, which are leaves.

Result:

- 348 tests pass, unchanged. `models` imports no other layer. Distinct package-level cycles 136 -> 5.
- The 5 remaining cycles are `analysis <-> chunking` and `analysis <-> indexing`, inherent to `BuildResult` holding `SemanticChunk` and `SymbolIndex` while those packages consume analysis types. Left alone: breaking them means splitting `BuildResult`'s data from its derived indexes, which touches ~35 call sites for no functional gain.

## 2026-08-21 — Refactor: storage stops depending on retrieval

Status: COMPLETE

Files changed:

- retrieval/index_queries.py (new — `load_vector_store`, `build_hybrid_retriever`, `build_context_pack_from_index`)
- storage/index_store.py (those three removed; new `load_chunk_vectors`; no longer imports `retrieval`)
- cli.py, evaluation/runner.py, tests/test_vector_store.py, tests/test_context_builder.py, tests/test_hybrid_retrieval.py (import sites)
- models/indexing_context.py (stale TODO removed — `export_index` is already a field)

Problem:

- `storage/index_store.py` imported `retrieval.context_builder`, `retrieval.hybrid_retriever` and `retrieval.numpy_vector_store`, so the persistence layer depended on the retrieval layer, inverting `# 34. Module Responsibilities`. Three of its eleven functions were retrieval wiring rather than persistence.

Implementation:

- The three retrieval-assembly functions moved to `retrieval/index_queries.py`. `storage` keeps a new `load_chunk_vectors`, which returns `(chunk, vector)` pairs and knows nothing about `NumpyVectorStore`.
- Dependency direction is now `retrieval -> storage` only; `storage` imports no higher layer.

Result:

- 348 tests pass, unchanged. `storage/index_store.py` 267 -> 223 lines, 11 -> 9 functions.

Remaining known inversion: `models/build_result.py` imports `CodeGraph` and `SymbolIndex`, and `models/indexing_context.py` imports three indexes, so `models` is not yet a leaf. Tracked as the `BuildResult` decomposition.

## 2026-08-21 — Refactor: extract the incremental rebuild plan

Status: COMPLETE

Files changed:

- indexing/rebuild_plan.py (new — `FilePartition`, `RebuildPlan`, `PreviousSnapshot`, `partition_files`, `build_previous_snapshot`, `plan_rebuild`, `group_by_path`)
- indexing/indexer.py (`_incremental_rebuild` 185 -> 105 lines; new `_importers_for`, `_merge_reused_state`; five helpers moved out)
- tests/test_rebuild_plan.py (new)

Problem:

- `_incremental_rebuild` was a 185-line function doing seven jobs: loading the previous snapshot, grouping seven collections by path, running passes, reconciling identity, computing invalidation, merging reuse, and persisting. `# 1.2` forbids exactly this. The Task 8.3 invalidation bug was a missing term in one set union buried at line 187, and could only be caught by indexing a real repository.

Implementation:

- `FilePartition` buckets every path by change kind; `PreviousSnapshot` replaces seven `prev_*_by_path` locals; `plan_rebuild` returns the `reresolve` / `untouched` decision along with the `invalidation_sources` it derived them from. The invalidation rule is now one readable expression with a comment explaining why new paths bypass the fingerprint comparison.
- `group_by_path` absorbed `_group_resolved_references` and `_group_resolved_imports` via a `document_id` accessor, replacing three near-identical functions with one.
- `_merge_reused_state` isolates the reuse folding and returns the carried-in reference count the run report needs.

Tests:

- `test_rebuild_plan.py` (8): partition bucketing; new / deleted / changed-interface / changed-signature files invalidate importers; identical interface does not; `untouched` excludes rebuilt and re-resolved paths.
- Regression net verified: removing `partition.new` from the invalidation sources fails 4 tests across all three layers (unit, parity, integration).

Result:

- 348 tests pass (was 340). `indexing/indexer.py` 522 -> 404 lines.

## 2026-08-21 — Refactor: define the pass sequence once

Status: COMPLETE

Files changed:

- analysis/pipeline.py (new — `run_extraction_passes`, `run_resolution_passes`)
- analysis/build_graph.py (reduced to document loading + the two phases + chunking)
- indexing/indexer.py (`_incremental_rebuild` calls the same two functions)
- tests/test_pipeline_parity.py (new)

Problem:

- The full build (`analysis/build_graph.py`) and the incremental rebuild (`indexing/indexer.py::_incremental_rebuild`) each hard-coded the complete pass sequence, and ran two of the passes in different relative orders. Nothing tied them together, so a pass added to one and not the other would make the two paths silently produce different indexes for the same repository — with no failing test, because the incremental tests seed their database through the incremental path.

Implementation:

- `analysis/pipeline.py` defines the sequence once, split into the two phases the incremental path needs to interleave reuse merging between: `run_extraction_passes` (parse, symbol, import, export, reference) and `run_resolution_passes` (import resolver, reference resolver, relationship, graph). The per-document `run_symbol_pass` loop, previously duplicated in both callers, moved inside `run_extraction_passes`.
- `build_graph` now runs reference extraction before import resolution, matching the incremental order. Safe because reference extraction reads only symbol nodes.
- In `_incremental_rebuild`, re-attaching untouched files' raw imports and references moved after `run_resolution_passes`. Equivalent because the relationship and graph passes read `resolved_references`, not those lists; a comment records why the merge cannot move earlier (it would re-resolve reused imports).

Tests:

- `test_pipeline_parity.py` (3): reaching a repository state in one shot and reaching it through incremental edits must produce the same symbols, relationships, resolution statuses and import targets, compared via `stable_key` rather than UUID entity ids. Covers files added one at a time, an importer indexed before its dependency exists, and an edited file.
- Verified the parity suite catches the Phase 8 Task 8.3 invalidation bug independently: with that fix reverted, the importer-before-dependency case fails on a missing `calls` edge.

Result:

- 340 tests pass (was 337).

Decision / deviation:

- Kept two functions rather than one `run_all_passes`, because the incremental path must merge reused symbols, exports and resolutions between extraction and resolution. A single entry point would have needed a callback, which is the more complicated design.

## 2026-08-21 — Docs/model accuracy: drop never-emitted enum values, refresh README status

Status: COMPLETE

Files changed:

- models/relationships/relationship_kind.py (`IMPORTS`, `EXTENDS`, `IMPLEMENTS`, `USES` removed)
- models/entities/symbol_kind.py (`INTERFACE`, `TYPE_ALIAS` removed)
- models/entities/reference_kind.py (`IMPORT`, `TYPE` removed)
- README.md (`Current Status`, `Knowledge Graph`)

Problem:

- Eight enum values were declared but never assigned anywhere in the codebase, in any commit in history. Indexing a fixture exercising every construct confirms the emitted vocabulary is exactly `SymbolKind` {FUNCTION, CLASS, METHOD, VARIABLE}, `RelationshipKind` {CALLS}, `ReferenceKind` {CALL, IDENTIFIER, MEMBER_ACCESS}. The unused values advertised a semantic model broader than the one the pipeline builds, which is the same failure mode `# 3. Current Project Rules` warns about for language support.
- README `Current Status` was roughly fourteen phases stale: it listed sixteen delivered features under `Planned`, and named SQLite persistence and incremental indexing under `Completed` *and* `Planned` simultaneously. `Immediate Next Tasks` prescribed fifteen already-completed steps.
- README `Knowledge Graph` presented five relationship kinds as the graph model and listed `imports_of(document)` / `imported_by(document)` as supported operations; `CodeGraph` implements only `callers_of`, `callees_of`, `children_of`, `parents_of`.

Implementation:

- Removed the eight unused enum values per `# 1.5` (no abstraction without a concrete use). Verified safe: `git grep` across all refs shows they were never emitted, so no persisted database can contain them and the `Kind(row["kind"])` round-trip in the repositories cannot encounter them. The storage schema stores `kind` as plain `TEXT` with no `CHECK` constraint, so no migration is required.
- Rewrote README `Current Status` to match this file's `## Completed` checklist, and pointed readers here as the authoritative status document.
- Added a README `Not Yet Modelled` section recording the three real gaps: type-level constructs (`interface` / `type` produce no symbol and no export, so their imports resolve to a document with `target_symbol` unset), class hierarchy (`extends` / `implements` emit no relationships), and type analysis.
- Corrected the `Knowledge Graph` section to state that `CALLS` is the only emitted kind, that import edges live in the semantic model rather than the graph, and to list only the four operations `CodeGraph` actually exposes.

Tests:

- No behaviour change; 337 tests pass unchanged, ruff clean.

Decision / deviation:

- Deleted the unused values rather than annotating them as reserved. They are recorded as intended work in README `Planned`, which keeps the intent visible without an enum member that no code can produce.
- Interface / type-alias extraction was documented as a gap rather than implemented. Adding it requires AST inspection first per `# 1.3`, plus symbol/export/fingerprint handling, and does not belong in a documentation-accuracy change.
- README now states the CLI is invoked as `python cli.py <command>`; `ckg` is used as shorthand elsewhere in this file but no console script is installed.

## 2026-08-21 — Phase 8 Task 8.3 Fix: new files must invalidate importers

Status: COMPLETE

Files changed:

- indexing/indexer.py (`_incremental_rebuild` adds `new_paths` to the invalidation sources)
- tests/test_incremental_indexer.py (new regression test)

Problem:

- `_incremental_rebuild` built its invalidation set as `interface_changed_paths | deleted_paths`. `interface_changed_paths` is derived only from `FileChange.CHANGED` paths, so `FileChange.NEW` was never an invalidation source. A file whose import previously failed to resolve stayed stale after the missing target was added: the importer is `UNCHANGED`, so it was never re-resolved. Reproduced as `b.ts` importing `./a` before `a.ts` exists — after adding `a.ts` the reference stayed `UNRESOLVED` until `b.ts` was independently edited. This is the ordinary "write the call site, then create the module" editing pattern, so every graph edge into a newly added file was missing for a full edit cycle.

Implementation:

- `new_paths` (the `FileChange.NEW` set) is unioned into `invalidation_sources`, so `_reresolve_paths` pulls the new file's importers out of `untouched_paths` and back into re-resolution. NEW paths are added directly rather than routed through `_interface_changed_paths`, which compares against a previous interface fingerprint and has none for a new file (`prev_docs_by_path[path]` would `KeyError`).

Tests:

- `test_new_file_invalidates_importers_of_previously_missing_module`: index `b.ts` alone and assert `createAuth` is `UNRESOLVED`, add `a.ts`, then assert the change set is `{a.ts: NEW, b.ts: UNCHANGED}` and the reference is `RESOLVED` without touching `b.ts`. Verified to fail before the fix and pass after.

Result:

- 337 tests pass (was 336).

Decision / deviation:

- The existing suite covered `interface_change` and `deleted_file` invalidation — the two cases the implementation actually wired up — which is why the gap survived. The NEW case is the third sibling and is now covered alongside them.

## 2026-08-19 — Phase 17 Context Builder

Status: COMPLETE

Files changed:

- retrieval/context_builder.py (new — `estimate_tokens`, `ContextEntry`, `ContextPack`, `build_context_pack`)
- storage/index_store.py (`build_context_pack_from_index`)
- tests/test_context_builder.py (new)

Implementation:

- `build_context_pack(candidates, *, query, graph, symbols_by_key, token_budget)` turns the reranked candidate list into a `ContextPack` with `primary_definitions`, `supporting_definitions`, `relationships`, and `file_paths`. Candidates are deduplicated by the stable `chunk_key`; candidates whose only source is `("graph",)` are `supporting`, everything else `primary`. Primaries are added in rank order before supporting (direct evidence wins). Each symbol is added whole (header + full source) or, when only the source does not fit the remaining budget, as a header-only entry — never a truncated body — so the hard budget is never exceeded even for a single oversized symbol. Relationships are `source -> callee (calls)` edges among selected symbols; `file_paths` is the sorted unique path set. `estimate_tokens` uses `max(1, len(text) // 4)` (deterministic, no tokenizer dependency).
- `build_context_pack_from_index(db_path, query, *, token_budget, provider=None, top_k=5)` wires `load_index` + `build_hybrid_retriever` + `retrieve` + `build_context_pack` so the persisted-index path produces a pack end-to-end.

Tests:

- `test_context_builder.py` (17): token estimation; primary/supporting role split; hard budget across a range of budgets; header-only fallback (symbol boundaries preserved); symbol skipped when its header alone does not fit; primary-before-supporting on a tight budget; dedup of duplicate candidates; relationships only among selected symbols; file-path dedup/sort; unknown keys skipped; determinism; empty candidates → empty pack; integration with and without an embedding provider.

Result:

- 260 tests pass via `.venv/bin/python -m unittest discover -s tests` (was 243).

Decision / deviation:

- Token budget is approximated with the standard 4-chars-per-token heuristic (`len(text) // 4`); a real tokenizer is not a dependency and would not change the hard-budget guarantee.
- Role split reuses the Phase 15/16 convention that graph-expanded candidates are tagged `("graph",)`; routed strategies (`graph_callers`, etc.) return only graph/`exact`-tagged candidates, which are the primary answer and are therefore all treated as primary evidence.
- Source excerpts come from `Symbol.content` (== `SemanticChunk.display_text`), so no chunk-table join is needed; relationships are recomputed from `CodeGraph` on the selected set rather than persisted.

Next:

- Phase 18 incremental embedding / async worker.

## 2026-08-19 — Phase 16 Reranking

Status: COMPLETE

Files changed:

- retrieval/reranker.py (new — `RerankFeatures`, `detect_preference`, `rerank_candidates`)
- retrieval/hybrid_retriever.py (`_hybrid_search` reranks combined main + graph candidates; `_detect_seed`; `NAME_MATCH_BOOST` removed)
- tests/test_reranker.py (new)
- tests/test_hybrid_retrieval.py (caller-intent integration test)

Implementation:

- `rerank_candidates` adds a deterministic weighted boost to each candidate's base RRF score across all seven Phase 16 features (exact symbol, path, kind, FTS presence, vector presence, graph distance, relationship relevance), then stable-sorts by final score. `detect_preference` maps caller/callee/definition intent phrases to a preference so graph-intent queries prioritize the matching edge kind over vector similarity.
- `_hybrid_search` now detects a unique seed symbol (`_detect_seed`, ambiguous names → no seed), expands its neighborhood (Phase 15), reranks the combined main + expanded candidate set, then slices `top_k` — graph neighbors can now outrank vector-similar unrelated symbols instead of being appended after the slice.

Tests:

- `test_reranker.py` (12): intent mapping; exact-symbol boost; caller preference lifts the caller above a higher base score; graph-distance lifts a neighbor; kind/path boosts; FTS presence breaks a tie; determinism; `who calls login` ranks caller first.
- `test_hybrid_retrieval.py` (1 new): `callers of login` (hybrid path) returns `run`, the incoming CALLS edge, first.

Result:

- 243 tests pass via `.venv/bin/python -m unittest discover -s tests` (was 230).

Decision / deviation:

- No trained reranker (spec: measure the heuristic baseline first). Weights chosen so relationship relevance dominates for graph-intent queries and exact symbol match dominates for definition queries; FTS/vector rank position stays in the base RRF score.
- Graph-expanded candidates now compete in the main ranking rather than being appended after `top_k`; Phase 15's `expand_neighborhood` is unchanged.

Next:

- Phase 17 context builder (budgeted `ContextPack` over ranked candidates).

## 2026-08-19 — Phase 15 Graph-Aware Retrieval

Status: COMPLETE

Files changed:

- retrieval/neighborhood.py (new — `NeighborhoodHit`, `expand_neighborhood`)
- retrieval/hybrid_retriever.py (`resolved_imports`/`exports` params, `_expand_graph` uses `expand_neighborhood`)
- storage/index_store.py (`build_hybrid_retriever` passes resolved imports + exports)
- tests/test_graph_retrieval.py (new)
- tests/test_hybrid_retrieval.py (expansion stub + integration tests)

Implementation:

- `expand_neighborhood(seed, *, graph, symbol_index, resolved_imports=None, exports=None, one_hop_budget=6, two_hop_budget=2)` produces a deduplicated, budgeted, deterministic neighborhood. 1-hop covers callers, callees, parent, imports (seed document's resolved target symbols), and exports (seed document's module-scope exported symbols), ordered structural-first so the `one_hop_budget` never starves call context. 2-hop runs only when the seed has no direct call edges, walking the seed's children's callees once (`hop=2`), capped at `two_hop_budget`.
- `HybridRetriever` now injects `resolved_imports` / `exports` (optional); `_expand_graph` delegates to `expand_neighborhood` and tags every supporting candidate `("graph",)`. `build_hybrid_retriever` wires the persisted index's resolved imports and exports so the full 1-hop set is available in the integration path.

Tests:

- `test_graph_retrieval.py` (12): five 1-hop relations present + deduped; import relation without a call; parent relation; dedup across call/import; 2-hop only for no-call-edge seeds; no 2-hop with a direct callee; budget caps exports and is configurable; deterministic order; isolated leaf empty; imports/exports skipped when not supplied.
- `test_hybrid_retrieval.py` (3 new): stub-driven expansion surfaces callers/callees/exports and an import neighbor; integration `reindex_index` → `build_hybrid_retriever` surfaces an imported `helper` tagged `graph`.

Result:

- 230 tests pass via `.venv/bin/python -m unittest discover -s tests` (was 215).

Decision / deviation:

- 2-hop trigger chosen: "no direct call edges → walk children's callees". Children are a 2-hop bridge only, not a 1-hop relation (spec lists five kinds). Imports/exports are document-scoped, matching the Phase 10 chunker.
- `_expand_graph` no longer hard-caps appended supporting candidates at 3; the neighborhood budgets own the cap (Phase 15 owns hop semantics and context budgets per the Phase 14 decision note).

Next:

- Phase 16 heuristic reranking (deterministic features; no trained model yet).

## 2026-08-17 — Phase 10 Semantic Chunking

Status: COMPLETE

Files changed:

- chunking/symbol_chunker.py (rewrite)
- storage/repositories/chunk_repository.py (new)
- models/build_result.py (add `chunks`)
- analysis/build_graph.py (compute chunks after `run_graph_pass`)
- storage/index_store.py (persist/load chunks in the same transaction)
- indexing/indexer.py (recompute chunks before `persist_index`)
- tests/test_semantic_chunking.py (new)
- tests/test_index_store.py (chunk round-trip + rollback coverage)
- tests/test_incremental_indexer.py (second run keeps identical chunks)

Implementation:

- Task 10.1: `SemanticChunk` is now content-addressed and stable — `chunk_key == symbol.stable_key` (never a UUID), `content_hash` = SHA-256 of `embedding_text` via the existing `compute_content_hash`, and a constant `chunk_version = "v1"`. The old UUID-derived `chunk_id` was dropped. `build_semantic_chunks(result)` produces one chunk per symbol and groups imports/exports by `document_id`.
- Task 10.2: `build_semantic_chunk(symbol, graph, *, document_imports, exports)` embeds every spec field — kind+name, qualified name, file path, parent context (`graph.parents_of` → parent qualified name), calls, called by, imports (document's, sorted, `import { imported_name } from "module_path"`), exports (only this symbol's aliases, sorted, `symbol as alias` when renamed), then source; empty relations render as `none`.
- Persistence: `chunk_repository.insert_many` maps `chunk_key` → the existing `chunks.chunk_id` PK column and runs inside the same transaction as the rest of the snapshot (after relationships); `load_index` reconstructs `result.chunks`. The incremental indexer recomputes `result.chunks = build_semantic_chunks(result)` from the merged result right before persist (cheap, no per-file merge), and the full-build path already gets chunks from `build_graph`.

Tests:

- `test_semantic_chunking.py`: login's chunk contains qualified name, `file: auth.ts`, `calls: createAuth`, `called by: run`, `exports: login`; excludes `format`/`util.ts`/`logout`. Deterministic `chunk_key`/`content_hash` across two builds; body edit → changed `content_hash`, same `chunk_key`; distinct symbols → distinct keys; one chunk per symbol; run's chunk embeds its import.
- `test_index_store.py`: `persist_index`/`load_index` round-trip preserves `(chunk_key, content_hash, chunk_version)` and full embedding/display/relative-path fidelity; `chunks` added to the rollback table list.
- `test_incremental_indexer.py`: a second no-op `reindex_index` keeps identical `chunk_key` / `content_hash` / `embedding_text` sets.

Result:

- 170 tests pass via `.venv/bin/python -m unittest discover -s tests` (was 159).

Decision / deviation:

- `chunk_key` reuses `symbol.stable_key` directly (path|language|qualified_name|kind) instead of a separate hash, so distinct symbols are guaranteed distinct keys while body edits keep the key stable — exactly what embedding reuse needs.
- To avoid an import cycle between `models/build_result` and `chunking/symbol_chunker`, `build_result.py` uses `from __future__ import annotations` + a `TYPE_CHECKING` import for `SemanticChunk`; `symbol_chunker` imports `BuildResult` normally.

Next:

- Phase 12 SQLite FTS5 (after persistence) — see section 18.

## 2026-08-17 — Phase 11 Local Embedding Store

Status: COMPLETE

Files changed:

- embeddings/provider.py (new — `EmbeddingProvider` ABC)
- embeddings/local_provider.py (new — `LocalEmbeddingProvider`)
- embeddings/fake_provider.py (new — `FakeEmbeddingProvider`)
- embeddings/encoder.py (deleted)
- indexing/vector_index.py (refactor to `EmbeddingProvider`)
- indexing/embedding_store.py (new — `embed_chunks`)
- storage/repositories/embedding_repository.py (new)
- storage/index_store.py (`persist_index` embeddings param + `load_embedding_cache`)
- indexing/indexer.py (optional `embedding_provider` + `new_embeddings` report)
- pyproject.toml (add `numpy`, `sentence-transformers`), uv.lock, uv sync
- tests/test_embedding_provider.py (new)
- tests/test_embedding_store.py (new)
- tests/test_embedding_indexer.py (new)
- tests/test_index_store.py (embeddings round-trip + rollback coverage)

Implementation:

- Task 11.1: `EmbeddingProvider` exposes `dimension`, `embed(text)`, `embed_batch(texts)`, `embed_query(query)`. `LocalEmbeddingProvider` is the only place `SentenceTransformer` is referenced (model `all-MiniLM-L6-v2`, normalized float32 vectors); `indexing/vector_index.py` now consumes the abstraction via `embed_batch`/`embed_query`, and the old `embeddings/encoder.py` was deleted.
- Task 11.2: `FakeEmbeddingProvider(dimension=8)` derives a deterministic, L2-normalized vector from the SHA-256 of the text — no ML model in unit tests.
- Cache + persistence: `indexing/embedding_store.py::embed_chunks(chunks, provider, cache)` returns `(embeddings_by_key, new_count)`, reusing vectors by `content_hash` and embedding only the missing chunks. `persist_index` writes embeddings in the same transaction (after chunks); `load_embedding_cache(db_path)` returns a `content_hash → vector` map (float32 blobs).
- Indexer wiring: `reindex_index(db_path, root_dir, *, embedding_provider=None)`. Provider `None` → embeddings skipped (existing behavior, no model load); provider supplied → cache reuse + persistence + `IndexRunReport.new_embeddings`, threaded through both the full-build and `_incremental_rebuild` paths.

Tests:

- `test_embedding_provider.py`: dimension, determinism, distinct vectors for distinct texts, batch shape/dtype, L2 normalization, `embed_query == embed`, empty batch.
- `test_embedding_store.py`: empty cache embeds all; full cache is a no-op (no `embed_batch` call); partial cache embeds only missing; empty chunk list.
- `test_embedding_indexer.py`: first run embeds every chunk; no-op run reuses all (0 new, vectors unchanged); body edit re-embeds only the changed chunk (`new_embeddings == 1`, unchanged chunks keep their cached vectors); persistence round-trip (float32, dim 8, normalized); no-provider run skips embeddings entirely.
- `test_index_store.py`: `persist_index(..., embeddings=...)` round-trips through `load_embedding_cache`; `embeddings` added to the rollback table list.

Result:

- 188 tests pass via `.venv/bin/python -m unittest discover -s tests` (was 170).

Decision / deviation:

- Cache is keyed by `content_hash`, so any chunk whose embedding text is unchanged reuses its stored vector across runs; a body edit changes the hash and re-embeds only that chunk (same `chunk_key`, new vector).
- `embed_batch` returns a float32 2-D `numpy` array; blobs are stored raw as float32 bytes.

Next:

- Phase 12 SQLite FTS5 (after persistence) — see section 18.

## 2026-08-17 — Phase 9 Hierarchical / Merkle Hashing

Status: COMPLETE

Files changed:

- indexing/merkle.py (new)
- tests/test_merkle.py (new)

Implementation:

- `compute_merkle_tree(root_dir)` builds a deterministic Merkle tree over the repo file tree: file leaves hash content via the existing `compute_content_hash`; directories and the root hash children (names + child hashes) sorted by basename and encoded as `name\0child_hash\0`. Only content and normalized names are hashed — never mtime, size, or random IDs — so a change to one leaf changes only its ancestor hashes.
- `EXCLUDE_DIRS` are skipped via the existing `is_inside_excluded_dir`; unreadable files are skipped cleanly (mirrors `scan_files`). Single-file roots produce a single `FILE` node whose hash is the content hash.
- Deliberately no persistence or indexer wiring (rule 1.5): later phases (content-addressed chunk cache in Phases 10/11, content proofs in Phase 19) are the consumers.

Tests:

- `test_merkle.py`: file leaf == `compute_content_hash(content)`; directory nodes are `DIRECTORY` kind; tree hash deterministic across runs; changing one file changes its hash + affected dir + root but leaves the unrelated `lib/` dir unchanged; adding and deleting a file change only affected subtrees; hash independent of file creation order; single-file root hashes content.

Result:

- 159 tests pass via `.venv/bin/python -m unittest discover -s tests` (was 151).

Decision / deviation:

- Chose a pure content+name hash with NUL-separated `name\0hash\0` entries so no delimiter collision is possible; sibling order is fixed by basename sort.
- Scoped Phase 9 to the tree module and tests per the spec (rules + tests only); cross-run "detect unchanged subtrees cheaply" comparison is deferred to the persistence consumers.

Next:

- Phase 10 semantic chunking (done — see entry above).

## 2026-08-17 — Phase 8 Incremental Indexing

Status: COMPLETE

Files changed:

- indexing/diff.py (new)
- indexing/indexer.py (new)
- storage/repositories/file_state_repository.py (new)
- tests/test_file_state.py (new)
- tests/test_change_detection.py (new)
- tests/test_incremental_indexer.py (new)
- ingestion/loader.py (refactor: `iter_repo_files` / `build_document`)
- analysis/passes/parse_pass.py (optional `documents` filter)
- storage/index_store.py (`persist_index(..., file_states)`, `load_file_states`)

Implementation:

- Task 8.1: `file_state_repository` (upsert + `fetch_all`) fills the `file_state` table created in Phase 7. `persist_index` writes the inventory in the same transaction; `load_file_states` reads it back.
- Task 8.2: `indexing/diff.py:scan_files` classifies `NEW` / `CHANGED` / `UNCHANGED` / `DELETED`. `mtime_ns` + `size_bytes` is the cheap hint (no content read); the SHA-256 content hash is the correctness signal (a pure `touch` stays `UNCHANGED`).
- Task 8.3: `interface_fingerprint` (sorted `(exported_name, signature_hash)`) distinguishes content change from public-interface change; `importers_of` (via `resolve_module_path`) finds importers. `indexing/indexer.py:reindex_index` rebuilds only `NEW`/`CHANGED` files, re-resolves only importers of interface-changed/deleted files, reuses everything else, reconciles symbol identity via Phase 6 `match_symbols`, and persists a merged snapshot.
- First run (no prior `file_state`) falls back to `build_graph` + `persist_index`, so the existing pipeline is untouched.

Tests:

- `test_file_state.py`: repository round-trip, upsert replace, schema creation on load.
- `test_change_detection.py`: first scan all NEW; unchanged scan skips content reads; `touch` still UNCHANGED; edit → CHANGED; add/delete → NEW/DELETED.
- `test_incremental_indexer.py`: second run is a no-op (0 parses, 0 re-resolves, 0 embeddings); editing one file rebuilds only that file; body edit preserves symbol identity and does not invalidate importers; export rename re-resolves the importer to UNRESOLVED; deletion removes symbols and invalidates importers.

Result:

- 151 tests pass via `.venv/bin/python -m unittest discover -s tests` (was 136).

Decision / deviation:

- `persist_index` remains a full snapshot replace; the win is skipping parse/extraction/resolution for unchanged files, not writing less data. Change detection / merging is the Phase 8 scope; Phase 9 adds subtree hashing on top.
- Re-resolution re-runs the existing resolvers over stored `Reference`/`ImportReference` objects (no re-parse of importers), matching the doc's "affected semantic data may need re-resolution".
- Symbol identity carry-over (Phase 6 `match_symbols`) is required for correctness: it lets untouched importers keep pointing at edited symbols without re-resolution.

Next:

- Phase 9 hierarchical / Merkle hashing.

## 2026-08-15 — Phase 7 SQLite Persistence

Status: COMPLETE

Files changed:

- storage/**init**.py (new)
- storage/db.py (new)
- storage/schema.py (new)
- storage/_rows.py (new)
- storage/index_store.py (new)
- storage/repositories/**init**.py (new)
- storage/repositories/document_repository.py (new)
- storage/repositories/symbol_repository.py (new)
- storage/repositories/import_repository.py (new)
- storage/repositories/export_repository.py (new)
- storage/repositories/reference_repository.py (new)
- storage/repositories/resolved_reference_repository.py (new)
- storage/repositories/resolved_import_repository.py (new)
- storage/repositories/relationship_repository.py (new)
- tests/test_db.py (new)
- tests/test_storage_schema.py (new)
- tests/test_index_store.py (new)

Implementation:

- Task 7.1: `storage/schema.py` creates all 10 suggested tables plus `resolved_references` and `resolved_imports` (BuildResult carries resolution data `load_index` must reconstruct), with PK/FK (`ON DELETE CASCADE`) and a `schema_version` in `index_metadata`.
- Task 7.2: `storage/db.py` (connection + pragmas + `transaction`) and one repository module per entity under `storage/repositories/`; shared row helpers in `storage/_rows.py`.
- Task 7.3: `storage/index_store.py:persist_index` does a full snapshot replace in a single transaction (clear + insert, FK-safe order); any failure rolls back so a partial index is never visible. `load_index` reconstructs `BuildResult` + rebuilds `SymbolIndex` and `CodeGraph`.

Tests:

- `test_db.py`: WAL / foreign_keys / busy_timeout pragmas; transaction commit and rollback; foreign-key enforcement.
- `test_storage_schema.py`: all tables created; idempotent re-create; schema version; relationships unique index.
- `test_index_store.py`: round-trip preserves documents, symbols (stable keys / qualified names / hashes), imports, exports, resolutions, references, resolved statuses/targets, relationships; rebuilt graph (`callees_of(login)`); re-persist does not duplicate; forced FK failure rolls back the entire index.

Result:

- 136 tests pass via `.venv/bin/python -m unittest discover -s tests` (was 121).

Decision / deviation:

- `references` is a SQLite keyword and must be quoted as `"references"` in every statement.
- Persist relationships from the deduplicated graph view (`result.graph.relationships()`); the raw per-occurrence list stays only in memory.
- Resolved-import rows are linked to import rows by object identity within a single `persist_index` call (imports are occurrence rows with no in-memory id).
- `chunks`, `embeddings`, and `file_state` tables exist but have no writers yet (Phases 8/10/11); no speculative repositories (rule 1.5).
- Full snapshot replace per `persist_index`; change detection/merging is Phase 8.

Next:

- Phase 8 file hashing / change detection / incremental indexing.

## 2026-08-15 — Phase 0 Regression Tests

Status: COMPLETE

Files changed:

- tests/test_document_loading.py
- tests/test_language_support.py
- tests/test_location_access.py

Implementation:

- Phase 0 was already marked complete; added explicit regression tests for its four untested required outcomes (single document load, language/parser support alignment, location access).

Tests:

- Single-file and directory loading, excluded-dir and unsupported-extension skipping
- Every `INCLUDE_EXTENSIONS` entry maps to a parser; unknown extensions do not
- Symbol and reference `SourceLocation` values against known fixture sources

Result:

- 17 tests pass via `.venv/bin/python -m unittest discover -s tests`

Decision / deviation:

- Location assertions reflect actual Tree-sitter node semantics: a `variable_declarator` covers `x = 1`, a `function_declaration` covers the full declaration, and a reference covers just the identifier.

Next:

- Phase 1 (ParsedDocument IR)

## 2026-08-15 — Phase 1 ParsedDocument IR

Status: COMPLETE

Files changed:

- models/parsed_document.py
- analysis/passes/parse_pass.py
- models/indexing_context.py
- analysis/build_graph.py
- tests/test_parsed_document.py
- tests/test_parse_pass.py

Implementation:

- Added `ParsedDocument(document, tree, file_hash)` model.
- Added `run_parse_pass` that produces one `ParsedDocument` per supported document, skips unsupported languages cleanly, and flags `has_parse_errors`.
- Added `parsed_documents` to `IndexingContext`; kept `extracted_symbols` since the reference pass still depends on it.
- `build_graph` now parses once via the parse pass; the symbol pass consumes parsed trees. No semantic pass reparses a `Document`.

Tests:

- One `.ts` fixture produces one `Document`/`ParsedDocument` with a valid tree root and deterministic hash.
- Supported language parsed; unsupported language skipped; parse errors represented without crashing.

Result:

- 24 tests pass via `.venv/bin/python -m unittest discover -s tests`.
- `test_repo` build output unchanged (2 docs, 9 symbols, 11 references, 6 relationships).

Decision / deviation:

- Added `has_parse_errors` beyond the doc's suggested model because Task 1.2 requires parse errors to be represented; derived from `tree.root_node.has_error`.

Next:

- Phase 2 import pass wiring (Task 2.1).

## 2026-08-15 — Phase 3 Semantic Name Resolution

Status: COMPLETE

Files changed:

- models/entities/resolved_reference.py
- analysis/semantic/name_resolver.py
- analysis/passes/resolver_pass.py
- analysis/relationship_builder.py
- analysis/symbol_handlers/variable.py
- tests/test_name_resolution.py
- tests/test_variable_extraction.py

Implementation:

- Replaced first-match global name lookup in the resolver pass with scope-aware resolution climbing `owner → parent → module`.
- Added `ResolutionStatus` (resolved / unresolved / ambiguous); every reference now gets a `ResolvedReference` with a status.
- Module scope is restricted to the reference's document so identical names in other files do not create false ambiguity.
- Extracted local variables as nested symbols (removed the module-scope-only restriction) so shadowing works via the existing parent chain.
- Relationship builder only emits CALLS edges for RESOLVED references.
- Imports step of resolution order is an explicit `UNRESOLVED` stub until Phase 2 wiring lands.

Tests:

- Scope climb: inner → outer → module resolves `login()`.
- Shadowing fixture (mandatory Task 3.2): local `login` wins over module `login`.
- Cross-file: references in a file resolve to that file's symbol.
- Ambiguity: duplicate module declarations → AMBIGUOUS, no CALLS edge, no guessed target.
- Unresolved: unknown name → UNRESOLVED, no CALLS edge.
- Updated variable-extraction nested test: nested `const x` is now extracted as a VARIABLE owned by its function.

Result:

- 30 tests pass via `.venv/bin/python -m unittest discover -s tests`.
- `test_repo` build stable: 9 symbols, 6 relationships; references now carry explicit statuses.

Decision / deviation:

- Chose Option A (extract local variables as symbols) so shadowing uses the existing `children_by_parent` chain instead of a parallel scope table.
- Proceeded before Phase 2 as agreed; the imports branch of resolution order is stubbed.

Next:

- Phase 2 import pass wiring (Task 2.1).

## 2026-08-15 — Phase 2 Task 2.1 Import Pass

Status: COMPLETE

Files changed:

- analysis/passes/import_pass.py
- analysis/build_graph.py
- tests/test_import_pass.py

Implementation:

- Added `run_import_pass` that walks each `ParsedDocument` tree and appends `ImportReference`s to `BuildResult.import_references`.
- Wired the import pass into `build_graph` after the symbol pass and before reference resolution.

Tests:

- named, multiple named, aliased, default, namespace, and mixed imports.

Result:

- 36 tests pass via `.venv/bin/python -m unittest discover -s tests`.
- `test_repo` now produces 9 import references from `imports.ts` through the real pipeline.

Decision / deviation:

- Import resolver wiring (Task 2.2) remains pending.

Next:

- Task 2.2 import module resolver wiring.

## 2026-08-15 — Phase 2 Task 2.2 Import Module Resolver

Status: COMPLETE

Files changed:

- analysis/semantic/normalize_path.py
- analysis/semantic/import_resolver.py
- analysis/build_graph.py
- tests/test_import_resolver.py

Implementation:

- Reworked module path resolution to be relative to the importing document's directory, supporting `./file`, `../file`, explicit `.ts/.tsx/.js/.jsx`, and `./directory/index.ts`.
- Bare module specifiers (e.g. `lodash`) are out of scope and resolve to nothing.
- Deterministic candidate order: explicit extension first, otherwise `.ts → .tsx → .js → .jsx`.
- Wired `run_import_resolver_pass` into `build_graph` after the import pass.

Tests:

- `resolve_module_path`: relative-only filtering, extension order, extension preservation, parent-directory resolution.
- `resolve_import`: sibling file with/without extension, parent directory, `.jsx`, directory index, missing module → None, bare specifier → None.

Result:

- 47 tests pass via `.venv/bin/python -m unittest discover -s tests`.
- `test_repo`: all 9 imports resolve `./auth → auth.ts` through the real pipeline.

Decision / deviation:

- Kept resolution intentionally narrow per the task; no tsconfig/paths/node_modules resolution yet.

Next:

- Task 2.3 export model / Task 2.4 resolve imported symbols.

## 2026-08-15 — Phase 2 Task 2.3 Export Model + Task 2.4 Resolve Imported Symbol

Status: COMPLETE

Files changed:

- models/entities/exports.py (new)
- indexing/export_index.py (new)
- analysis/export_builder.py (new)
- analysis/export_handlers/declaration.py (new)
- analysis/export_handlers/specifier.py (new)
- analysis/export_registry.py (new)
- analysis/export_extractor.py (new)
- analysis/passes/export_pass.py (new)
- analysis/semantic/import_symbol_resolver.py (new)
- analysis/passes/import_resolver_pass.py
- models/entities/resolved_import_reference.py
- models/build_result.py
- models/indexing_context.py
- analysis/build_graph.py
- tests/test_export_pass.py (new)
- tests/test_import_symbol_resolution.py (new)

Implementation:

- Added `Export(document_id, exported_name, symbol_name, location)` and an `ExportIndex` keyed by `(document_id, exported_name)`.
- Added an export extractor following the import pipeline pattern (node-type-keyed handlers in `analysis/export_handlers/`), wired in via `run_export_pass`.
- Inspected Tree-sitter ASTs first (rule 1.3). Handled `export function`, `export const` (including multiple declarators), `export default <anonymous/named/class/identifier>`, `export { name }`, `export { name as alias }`, `export { name as default }`. Deferred re-exports (`export { a } from "./x"`, `export * from "./x"`) by skipping statements with a `source` field.
- Extended `ResolvedImportReference` with `target_symbol: Symbol | None` instead of adding a duplicate model.
- `resolve_imported_symbol` resolves imported name → export → module-scope symbol; returns `None` (never guesses) for namespace imports, missing exports, anonymous defaults, and ambiguous/duplicate exports.

Tests:

- `test_export_pass.py`: all supported export forms, multi-declarator, deferred re-exports, non-exported statements produce nothing.
- `test_import_symbol_resolution.py`: alias/named/default/namespace imports, missing export, unresolved module, plus a `test_repo` pipeline test asserting `authLogin → auth.ts::login` and `signOut → auth.ts::logout`.

Result:

- 68 tests pass via `.venv/bin/python -m unittest discover -s tests`.
- `test_repo` build: 5 exports extracted; 9 imports resolved to `auth.ts`, 6 of which resolve to a concrete symbol.

Decision / deviation:

- `export default function() {}` (anonymous) records `Export("default", None)` so the module is known to have a default export even though no named symbol exists.
- Re-export resolution (`export * from`, `export { x } from`) intentionally deferred per the task spec.

Next:

- Cross-file name resolution (consult imports in the reference resolver).
- Phase 4 member-expression resolution.

## 2026-08-15 — Phase 3 Cross-File Name Resolution

Status: COMPLETE

Files changed:

- analysis/semantic/name_resolver.py
- analysis/passes/resolver_pass.py
- tests/test_cross_file_resolution.py (new)

Implementation:

- Completed the `imports` step of the Phase 3 resolution order (`current scope → parent → module → imports → unresolved`), replacing the `UNRESOLVED` stub in `resolve_symbol`.
- `resolve_symbol` now takes `resolved_import_references` and, after module-scope lookup fails, resolves the reference name against the document's imports by `local_name`.
- Candidates are deduplicated by `target_symbol.symbol_id`; exactly one distinct target is `RESOLVED`, more than one is `AMBIGUOUS`.
- Namespace imports, missing exports, and unresolved modules carry `target_symbol=None` and therefore never resolve a bare reference (no guessing, Gate E).
- `run_reference_resolver_pass` passes `result.resolved_import_references` into the resolver.

Tests:

- Named import call resolves to the exported symbol in `auth.ts` and emits a cross-file CALLS edge.
- Aliased import (`authLogin()`) and default import resolve to the correct exported symbol.
- Duplicate imports of the same symbol stay `RESOLVED` (dedup by symbol id).
- Nested-scope call falls through to the imports step.
- Module-scope symbol shadows an imported name (module step runs before imports).
- Duplicate `local_name` bound to two different modules is `AMBIGUOUS`, no edge.
- Namespace import, missing export, and unresolved module are all `UNRESOLVED`, no edge.

Result:

- 79 tests pass via `.venv/bin/python -m unittest discover -s tests`.
- `test_repo` build stable: 2 docs, 9 symbols, 11 references, 6 relationships.

Decision / deviation:

- No new index/abstraction (rule 1.5): the resolver filters the resolved-import list directly. If performance warrants it later, add a document → local_name import index (Gate D).
- Imported names bind at module scope of the importing document, so they are consulted only after module-scope symbol lookup fails, per the documented resolution order.

Next:

- Phase 4 member-expression resolution.

## 2026-08-15 — Phase 4 Member Expressions

Status: COMPLETE

Files changed:

- models/entities/references.py
- analysis/reference_builder.py
- analysis/reference_extractor.py
- analysis/semantic/reference_kind.py
- analysis/semantic/member_resolver.py (new)
- analysis/semantic/import_symbol_resolver.py
- analysis/passes/resolver_pass.py
- tests/test_member_expressions.py (new)

Implementation:

- Inspected Tree-sitter ASTs first (rule 1.3). Dot access is `member_expression` with `object`/`property` fields; called members sit in `call_expression.function`; `this`/`super` are distinct node types; object-literal keys are `property_identifier` in `pair` nodes (not member expressions).
- Added `Reference.path: tuple[str, ...]` as the single access-path representation (`("auth", "client", "createAuth")`); `name` stays the property name.
- The extractor now emits one reference per `member_expression` with the full path and does not descend into it, so `auth`/`client`/`createAuth` are no longer separate references.
- `determine_reference_kind` returns `CALL` for called member expressions and the existing `MEMBER_ACCESS` for non-call access.
- New `member_resolver.resolve_member_reference` resolves `this.<m>` via the enclosing class, `<namespace import>.<m>` via the target document's export table, and `<class>.<m>` via class children; deep paths and unknown bases stay `UNRESOLVED` (no guessing, Gate E).
- Extracted `resolve_exported_symbol` in `import_symbol_resolver.py`, now shared by the import and member resolvers (rule 1.5: second concrete consumer).
- `run_reference_resolver_pass` dispatches member references (path length > 1) to the member resolver and passes `context.export_index`.

Tests:

- Representation: single path reference per member expression, CALL vs MEMBER_ACCESS kinds, object/property parts not emitted separately.
- Namespace import `auth.createAuth()` resolves to `auth.ts::createAuth` and emits a CALLS edge; deep path `auth.client.createAuth()` is UNRESOLVED.
- `this.logout()` resolves to the class method; duplicate class methods are AMBIGUOUS.
- `AuthService.create()` resolves to the class member.
- Member on unknown object is UNRESOLVED; member property never falls back to module scope; non-call member access produces no CALLS edge.

Result:

- 89 tests pass via `.venv/bin/python -m unittest discover -s tests`.
- `test_repo` build: 2 docs, 9 symbols, 8 references (was 11 — object/property noise removed), 6 relationships, no false module-scope resolution on member properties.

Decision / deviation:

- Member resolution is limited to deterministic cases (namespace import, `this`, class scope). Computed access (`obj[key]`), `super.foo()`, and inheritance remain out of scope.
- Object-literal keys are still extracted as references (pre-existing behavior); left unchanged to keep this phase focused on member expressions.

Next:

- Phase 5 knowledge-graph stabilization / relationship deduplication.

## 2026-08-15 — Phase 5 Knowledge Graph Stabilization

Status: COMPLETE

Files changed:

- models/relationships/relationships.py
- graph/code_graph.py
- tests/test_code_graph.py (new)

Implementation:

- Added `Relationship.key` returning the stable `(source_symbol_id, target_symbol_id, kind)` tuple.
- `CodeGraph.add_relationships` deduplicates via an internal `_relationship_keys` set; `BuildResult.relationships` remains the raw per-occurrence list.
- `CodeGraph` now exposes `symbols()` and `relationships()` as immutable tuples (no internal state leaking), plus `children_of()` (parent → children map) and `parents_of()` (immediate parent).
- `callers_of()` / `callees_of()` are unchanged and become duplicate-free as a side effect of dedup.

Tests:

- Graph API: symbols/children/parents accessors, empty lookups, immutable copy behavior.
- Dedup: `login(); login();` in one owner → 2 references, 1 unique CALLS edge, `callers_of(login)` returns the owner once; direct `add_relationships` dedup.

Result:

- 100 tests pass via `.venv/bin/python -m unittest discover -s tests` (was 89).

Decision / deviation:

- Chose deduplication inside the graph (internal set) per the doc's option, keeping occurrence info recoverable in `BuildResult.relationships`.

Next:

- Phase 6 stable identities / fingerprints.

## 2026-08-15 — Phase 6 Stable Identity

Status: COMPLETE

Files changed:

- models/entities/symbols.py
- analysis/signature.py (new)
- analysis/fingerprints.py (new)
- analysis/symbol_builder.py
- analysis/symbol_matching.py (new)
- tests/test_fingerprints.py (new)
- tests/test_symbol_matching.py (new)

Implementation:

- Task 6.1: `Symbol` keeps `symbol_id` (UUID, internal entity identity) and gains `qualified_name` and `stable_key` (source identity). `qualified_name` is derived from the extraction-time owner chain; `stable_key = "{relative_path}|{language}|{qualified_name}|{kind.value}"` is deterministic across runs. `document_id` stays a UUID; `relative_path` is the stable document identity.
- Task 6.2: `content_hash` (SHA-256 of symbol source) and `signature_hash` (SHA-256 of a name-independent, body-excluding signature) are computed once in `build_symbol`. `analysis/signature.py:extract_signature` produces `function({param types})[:{return type}]` / `class[:{extends}]` / `variable:{annotation}` / `variable:<{value type}>`. Signature inspection followed rule 1.3.
- Task 6.3: `analysis/symbol_matching.py:match_symbols` matches old vs new symbol sets: exact stable key → HIGH; same scope + signature → MEDIUM (rename); same content hash at a new path → MEDIUM (move). LOW-confidence "similar source" matches are never accepted (Gate E: no guessing). Unique unclaimed candidates only.

Tests:

- `test_fingerprints.py`: determinism across two builds; qualified names for module/class-method/nested symbols; stable-key sensitivity to kind and path; signature excludes name and body but includes parameter types / return type / extends; content hash changes on any edit.
- `test_symbol_matching.py`: unchanged repo → all HIGH; rename in place → MEDIUM; file move with unchanged content → MEDIUM; signature change keeps identity (HIGH); rename + signature change → new identity; ambiguous scope+signature → new identity; moved + edited → new identity.

Result:

- 121 tests pass via `.venv/bin/python -m unittest discover -s tests` (was 100).

Decision / deviation:

- Signature is shape-based and name-independent so that rename matching (step 2) can work; bodies are excluded per the task spec.
- Step 3 of the matching ladder ("same signature + similar source") is recognized as LOW confidence and never produces a match, per the doc's "do not guess" rule.
- Discovered `class_heritage` is a named child, not a registered field, in the current tree-sitter-typescript grammar; `_class_signature` finds it by child type (rule 1.3 AST inspection).

Next:

- Phase 7 SQLite persistence.

---

# Final Engineering Rule

Do not ask:

> "What code can I add next?"

Ask:

> "What semantic fact is missing, what is the smallest correct implementation, and how will I prove it works?"

The target system is:

```text
Correct semantic model
        ↓
Persistent local index
        ↓
Incremental updates
        ↓
Semantic chunks
        ↓
Exact + lexical + vector retrieval
        ↓
Graph expansion
        ↓
Reranking
        ↓
Minimal context
        ↓
LLM
```

Graph gives structural precision.

FTS gives lexical recall.

Embeddings give semantic recall.

Graph expansion restores missing context.

Reranking improves ordering.

Incremental indexing makes the system usable on real repositories.

The LLM is the final reasoning layer, not the repository indexer.
