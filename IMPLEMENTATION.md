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

Status: AFTER SEMANTIC RESOLUTION

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

---

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

---

# 12. Phase 6 — Stable Identity

Status: REQUIRED BEFORE INCREMENTAL INDEXING

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

---

## Task 6.2 — Symbol Fingerprints

Compute:

```text
content_hash
signature_hash
```

Use these for matching and change detection.

Do not use body hash as the permanent identity because a function can change while remaining the same symbol.

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

---

# 13. Phase 7 — SQLite Persistence

Status: NOT STARTED

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

---

## Task 7.2 — Database Layer

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

---

## Task 7.3 — Transactions

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

---

# 14. Phase 8 — Incremental Indexing

Status: NOT STARTED

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

---

# 15. Phase 9 — Hierarchical / Merkle Hashing

Status: AFTER BASIC INCREMENTAL INDEXING

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

### Tests

Change one file.

Assert:

```text
changed file hash ≠ old hash
affected directory hash ≠ old hash
unrelated directory hash == old hash
```

---

# 16. Phase 10 — Semantic Chunking

Status: AFTER GRAPH + PERSISTENCE

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

---

## Task 10.2 — Chunk Tests

Given a fixture:

```text
login → createAuth
login ← api.login
```

assert the chunk contains the intended graph facts and excludes unrelated symbols.

---

# 17. Phase 11 — Local Embedding Store

Status: AFTER CHUNKING

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

---

# 18. Phase 12 — SQLite FTS5

Status: AFTER PERSISTENCE

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

---

# 19. Phase 13 — Vector Retrieval

Status: AFTER EMBEDDINGS

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

---

# 20. Phase 14 — Hybrid Retrieval

Status: AFTER FTS + VECTOR

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

---

# 21. Phase 15 — Graph-Aware Retrieval

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

---

# 22. Phase 16 — Reranking

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

---

# 23. Phase 17 — Context Builder

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

---

# 24. Phase 18 — Incremental Embedding / Async Worker

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

---

# 25. Phase 19 — Secure Local Indexing

Adopt local-safe ideas from production code indexing systems.

## Ignore rules

Honor:

```text
.gitignore
.ckgignore
```

before parsing or embedding.

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

---

# 27. Phase 21 — Agent / CLI Integration

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

---

# 28. Phase 22 — Evaluation

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

---

# 29. Regression Test Policy

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

# 30. Decision Gates

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

# 31. Coding Style

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

# 32. Module Responsibilities

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

# 33. Current Tasks

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

## In Progress

(none)

## Next

- [ ] Relationship deduplication
- [ ] Stable identities
- [ ] SQLite persistence

---

# 34. Immediate Execution Order

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
```

---

# 35. What Not To Build Yet

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

# 36. Definition of v1

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

# 37. Update Log

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
