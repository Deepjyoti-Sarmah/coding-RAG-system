# Code Knowledge Graph (CKG)

> A local-first semantic code intelligence engine for AI coding agents.

## Quick start

Install from a checkout (installs `ckg` and `ckg-mcp` via `[project.scripts]`):

```bash
uv tool install .      # from the repository root
ckg --version
# 0.1.0
```

Index a project and search it:

```bash
cd /path/to/your/project
ckg index .
# Indexed into .ckg/index.sqlite
#   parsed files:        2
#   resolved references: 4
#   new: 2

ckg search "login"
# vector search inactive: 3 chunks pending embedding — run `ckg embed`
# login (function) — auth.ts [score=1.433 sources=exact,fts]
# run (function) — api.ts [score=0.466 sources=fts]
# createAuth (function) — auth.ts [score=0.449 sources=fts]

ckg status --oneline
# symbols 3 chunks 3 pending 3 gen 1
```

Wire up the MCP server for your agent (writes `.mcp.json` by default):

```bash
ckg init
# Wrote .mcp.json
# cat .mcp.json
# {
#   "mcpServers": {
#     "ckg": {
#       "command": "ckg-mcp"
#     }
#   }
# }
```

Restart your editor/agent after `ckg init`. Every question now hits the local index instead of re-reading files.

## What you get

- **Hybrid retrieval** — exact symbol match + graph expansion (`CALLS`/`IMPORTS`) + SQLite FTS5 lexical + vector similarity, fused by reciprocal rank and heuristic reranking
- **Incremental indexing** — file hashes + Merkle-style change detection; only changed files are reparsed and re-resolved, embeddings are content-addressed and reused
- **Local-first, no cloud** — SQLite + sqlite-vec + local embeddings; the index is disposable derived state, source files are the source of truth
- **MCP integration** — `ckg-mcp` server exposes `index_repository`, `search`, `definition`, `callers`, `callees`, `imports`, `context`, and `repository_status` to Claude Code, Cursor, VS Code, and other MCP clients; `ckg init` wires it up
- **Supported languages** — Python, TypeScript/TSX, JavaScript/JSX, Go (tree-sitter grammars via `parsing/registry.py`)

## CLI at a glance

All commands are available as `ckg <command>` (installed via `[project.scripts]` in `pyproject.toml`; `python cli.py <command>` also works from a source checkout).

| Command | Usage | What it does |
|---------|-------|--------------|
| `ckg index <path> [--embed] [--no-background]` | `ckg index .` | Build or update the semantic index for `<path>` |
| `ckg status [path] [--oneline]` | `ckg status --oneline` | Show index generation and counts; `--oneline` for shell prompts |
| `ckg search <query> [path] [--top-k N] [--no-vector]` | `ckg search "login"` | Hybrid search over the index |
| `ckg definition <name> [path]` | `ckg definition createAuth` | Find where a symbol is defined |
| `ckg callers <name> [path]` | `ckg callers login` | Find callers of a symbol (graph) |
| `ckg callees <name> [path]` | `ckg callees login` | Find callees of a symbol (graph) |
| `ckg imports <file> [path]` | `ckg imports api.ts` | List a file's imports and resolutions |
| `ckg context <query> [path] [--budget N] [--top-k N] [--no-vector]` | `ckg context "how does login work?"` | Build a token-budgeted context pack |
| `ckg eval [--embed] [--top-k N]` | `ckg eval --embed` | Run the fixed benchmark and report retrieval/indexing metrics |
| `ckg watch <path> [--no-embed] [--debounce SEC]` | `ckg watch .` | Keep the index fresh by watching for file changes |
| `ckg init [path]` | `ckg init` | Configure MCP for this project (writes `.mcp.json`) |
| `ckg embed [path] [--limit N]` | `ckg embed` | Drain the embedding queue |

Top-level options: `ckg --version` (from `importlib.metadata`), `ckg --db <path>` to override the index database path, `ckg --help`.


---

CKG builds a semantic model of a repository, stores it locally, derives retrieval-ready chunks from that model, and gives coding agents only the code that is relevant to the current task.

The goal is not to make the LLM read the repository.

The goal is to make the repository **queryable before the LLM sees it**.

---

# Why CKG Exists

Traditional Code RAG usually looks like:

```text
Repository
    ↓
Text Chunks
    ↓
Embeddings
    ↓
Vector Search
    ↓
LLM
```

This treats source code mostly as text.

But source code is a structured system:

```text
Files
Symbols
Scopes
References
Imports
Exports
Types
Calls
Dependencies
Relationships
```

CKG therefore uses a compiler-inspired pipeline:

```text
Repository
    ↓
Parser
    ↓
Semantic Analysis
    ↓
Code Knowledge Graph
    ↓
Semantic Chunks
    ↓
Local Search / Vector Index
    ↓
Hybrid Retrieval
    ↓
Context Builder
    ↓
LLM
```

The graph is the semantic source of truth.

The vector index is a retrieval optimization.

---

# Core Principles

## 1. Understand code before retrieving code

Do not embed raw files blindly.

First understand:

```text
what exists
who owns it
what references it
what it imports
what imports it
what it calls
what calls it
what it exports
what it resolves to
```

Then build retrieval data from that information.

---

## 2. The graph is not the vector database

The graph answers exact structural questions:

```text
Who calls login()?
Where is createAuth defined?
What imports auth.ts?
What does AuthService depend on?
```

The vector index answers semantic questions:

```text
Where is authentication handled?
Where is token validation implemented?
How does the login flow work?
```

Use both.

```text
Graph     → precision
FTS       → lexical recall
Vectors   → semantic recall
Reranking → relevance
```

---

## 3. Source files are the source of truth

Everything else is derived from source code:

```text
Source
   ↓
Hashes
   ↓
Semantic Index
   ↓
Chunks
   ↓
Embeddings
```

The SQLite index, graph, chunks, and embeddings are disposable derived state.

Deleting the local index must never delete or modify source code.

---

## 4. Incremental by default

Repositories change constantly.

A one-line edit should not require:

```text
parse 100,000 files
rebuild entire graph
re-embed everything
```

Instead:

```text
File changed
    ↓
Hash changed?
    ↓
Reindex only affected data
    ↓
Reuse everything unchanged
```

---

## 5. Local-first

The initial system should work entirely on the developer's machine.

No cloud database is required.

No hosted embedding API is required.

Target architecture:

```text
Repository
    ↓
Local SQLite
    ↓
Local FTS
    ↓
Local vector storage
    ↓
Local retrieval
    ↓
Agent
```

---

# Architecture

```text
                         REPOSITORY
                              │
                              ▼
                       File Scanner
                              │
                              ▼
                      Ignore Rules
                 .gitignore / .ckgignore
                              │
                              ▼
                    Change Detection
                 Hashes / Merkle Structure
                              │
                              ▼
                      ParsedDocument
                              │
                              ▼
                  ┌─────────────────────┐
                  │ Semantic Compiler   │
                  │                     │
                  │ Symbol Pass         │
                  │ Import Pass         │
                  │ Export Pass         │
                  │ Reference Pass      │
                  │ Resolution Pass     │
                  │ Relationship Pass   │
                  └──────────┬──────────┘
                             │
                             ▼
                    Code Knowledge Graph
                             │
                 ┌───────────┴───────────┐
                 ▼                       ▼
           Exact Queries          Semantic Chunking
                 │                       │
                 │                       ▼
                 │                  Content Hash
                 │                       │
                 │                  Embedding Cache
                 │                       │
                 │                       ▼
                 │                 Vector Index
                 │                       │
                 └───────────┬───────────┘
                             ▼
                     Hybrid Retrieval
                  /          |          \
               Exact        FTS        Vector
                  \          |          /
                           Graph
                          Expansion
                             │
                             ▼
                          Reranker
                             │
                             ▼
                      Context Builder
                             │
                             ▼
                  Claude / Codex / Gemini
                         / Pi / OpenCode
```

---

# Compiler Pipeline

Each pass should have one responsibility.

## Document Pass

Answers:

> What files exist?

Produces:

```text
Document
```

---

## Parse Pass

Answers:

> What is the syntax tree for this document?

Produces:

```text
ParsedDocument
```

A parsed document contains:

```text
Document
Tree-sitter Tree
File Hash
```

The tree should be parsed once and reused by all syntax-based passes.

---

## Symbol Pass

Answers:

> What declarations exist?

Current:

```text
FUNCTION
CLASS
METHOD
VARIABLE
INTERFACE
TYPE_ALIAS
```

Planned:

```text
ENUM
NAMESPACE
```

---

## Import Pass

Answers:

> What modules and names are imported?

Examples:

```ts
import { login } from "./auth";
import { login as authLogin } from "./auth";
import AuthService from "./auth";
import * as auth from "./auth";
```

Produces:

```text
ImportReference
```

---

## Export Pass

Answers:

> What symbols are visible outside this module?

Planned support:

```ts
export function login() {}
export const auth = ...
export default AuthService
export { login }
export { login as authLogin }
```

Produces:

```text
Export
```

---

## Reference Pass

Answers:

> Where are symbols used?

Example:

```ts
login();
login();
```

produces two references.

A reference records:

```text
name
kind
location
owner_symbol_id
```

---

## Resolution Pass

Answers:

> Which declaration does this reference refer to?

Example:

```text
Reference(login)

↓

ResolvedReference

↓

Symbol(login)
```

Resolution should eventually consider:

```text
local scope
    ↓
parent scope
    ↓
module scope
    ↓
imports
    ↓
exports
```

Never resolve by simply taking the first global symbol with the same name.

---

## Relationship Pass

Answers:

> What semantic relationships exist?

Current, as symbol-to-symbol edges:

```text
CALLS
EXTENDS
IMPLEMENTS
DECLARES
```

Each edge carries a `count`: repeated references fold into one edge and
accumulate rather than being discarded.

Current, as document-scoped adjacency on the graph:

```text
IMPORTS
EXPORTS
```

Imports and exports are file-level facts with no owning symbol, so they are not
symbol-to-symbol rows. They are indexed on the graph instead
(`imports_of_document`, `exports_of_document`, `importers_of_document`,
`importers_of_symbol`) and rebuilt from the `resolved_imports` and `exports`
tables, which remain their single source of truth.

Planned:

```text
REFERS_TO
USES
OVERRIDES
HAS_TYPE
RETURNS
```

`USES` / `REFERS_TO` are deferred deliberately: identifier references are the
highest-volume artifact the reference pass produces, and they need a volume
guard plus neighborhood ranking work before they earn a place in the graph.
`HAS_TYPE` / `RETURNS` need per-language type-annotation extraction.

Relationships are built from resolved semantic information rather than repeatedly walking the AST.

---

# Current Semantic Model

## Document

Represents a source file.

Contains file-level information such as:

```text
document_id
absolute_path
relative_path
file_name
extension
language
size
line_count
content
```

---

## Symbol

Represents a declaration.

Current shape:

```text
symbol_id
document_id
name
kind
relative_path
location
content
parent_symbol_id
qualified_name
content_hash
signature_hash
stable_key
```

`symbol_id` is an internal entity identity (UUID). `stable_key` (`relative_path|language|qualified_name|kind`) is the deterministic source identity used to match symbols across index runs. `signature_hash` is a name-independent, body-excluding shape fingerprint used for rename matching.

---

## Reference

Represents a usage of a name.

```text
reference_id
document_id
name
kind
location
owner_symbol_id
```

---

## ResolvedReference

Connects a reference to the declaration it refers to:

```text
Reference
    ↓
Symbol
```

---

## ImportReference

Represents import syntax:

```text
module_path
imported_name
local_name
document_id
location
```

---

## ResolvedImportReference

Currently resolves:

```text
ImportReference
    ↓
Target Document
```

Next milestone:

```text
ImportReference
    ↓
Target Document
    ↓
Exported Symbol
```

---

# Current Indexes

## SymbolIndex

Maintains:

```text
by_id
by_name
children_by_parent
```

Used for:

```text
symbol lookup
scope traversal
parent/child ownership
resolution
```

---

## DocumentIndex

Maintains:

```text
by_id
by_relative_path
```

Used for:

```text
module resolution
document lookup
cross-file analysis
```

---

# Knowledge Graph

The graph stores semantic relationships between entities.

Currently emitted:

```text
Symbol
   └── CALLS ───────────→ Symbol
Symbol
   └── EXTENDS ──────────→ Symbol (base class or base interface)
Symbol
   └── IMPLEMENTS ──────→ Symbol (implemented interface)
```

`CALLS`, `EXTENDS` and `IMPLEMENTS` are the relationship kinds the graph
produces today. Both heritage kinds are built from resolved heritage
references and owned by the declaring symbol — `EXTENDS` from
`class Child extends Base` and `interface Child extends Base`,
`IMPLEMENTS` from `class Impl implements Shape` (one edge per implemented
interface). Unresolved or ambiguous heritage names produce no edge.
`IMPORTS` and `USES` are part of the intended model but are not built
yet, so they are not present in `RelationshipKind`; see
**Not Yet Modelled** under _Current Status_.

Import edges are not stored in the graph. They live in the semantic
model as `ImportReference` / `ResolvedImportReference` and are queried
through the index rather than through `CodeGraph`.

`CodeGraph` exposes:

```text
callers_of(symbol)
callees_of(symbol)
children_of(symbol)
parents_of(symbol)
base_types_of(symbol)
subtypes_of(symbol)
```

`callers_of` / `callees_of` report `CALLS` edges only; heritage is queried
through `base_types_of` / `subtypes_of`.

The graph is primarily an **exact structural index**.

---

# Semantic Chunking

Do not embed raw files as the primary unit.

Instead create symbol-centered semantic chunks.

Example:

```text
Symbol:
    AuthService.login

Kind:
    method

File:
    src/auth/service.ts

Parent:
    AuthService

Calls:
    createAuth
    validateUser

Called By:
    loginRoute
    sessionHandler

Imports:
    UserRepository
    JWTService

Exports:
    login

Source:
    ...
```

This chunk contains both:

```text
local source
+
semantic neighborhood
```

That is what gets embedded.

---

# Vector Index

Embeddings are derived from semantic chunks.

```text
Knowledge Graph
      ↓
Semantic Chunk
      ↓
Content Hash
      ↓
Embedding
      ↓
Vector Index
```

A graph should **not** be serialized into one giant embedding.

Instead, embed:

```text
symbol-centered subgraphs
```

Examples:

```text
AuthService.login
PaymentService.charge
UserRepository.findUser
```

Each embedding represents a useful semantic unit.

---

# Hybrid Retrieval

Retrieval should combine several methods.

## Exact Search

For:

```text
where is createAuth?
find AuthService
```

Use the symbol index.

---

## Graph Search

For:

```text
who calls login?
what does login call?
what imports auth.ts?
```

Use the graph.

---

## Lexical Search

Use SQLite FTS5 for exact text and identifier matches.

---

## Vector Search

Use embeddings for semantic questions:

```text
where is authentication handled?
where is token validation implemented?
how does the payment flow work?
```

---

## Combined Retrieval

```text
Query
  ↓
Exact candidates
  +
FTS candidates
  +
Vector candidates
  +
Graph-expanded candidates
  ↓
Candidate merge
  ↓
Reranking
  ↓
Context Builder
```

---

# Local Persistence

SQLite will become the persistent local index.

Potential tables:

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

SQLite should be the default persistence layer before introducing a separate graph database.

---

# Incremental Indexing

A production repository cannot be rebuilt from scratch after every edit.

We therefore need:

```text
file hashing
content hashing
Merkle / hierarchical hashing
dirty-file detection
dependency invalidation
incremental graph updates
incremental chunk updates
incremental embeddings
```

---

## File Hashing

For every indexed file:

```text
path
hash
last_indexed_at
```

If the hash is unchanged:

```text
skip
```

---

## Merkle / Hierarchical Hashing

Eventually maintain hashes like:

```text
repo
 ├── src
 │    ├── auth.ts
 │    └── api.ts
 │
 └── package.json
```

with:

```text
auth.ts hash
api.ts hash

       ↓

src hash

       ↓

repository hash
```

Changing one file invalidates only the affected subtree.

This makes large repositories cheaper to re-index.

---

# Content-Addressed Semantic Chunks

Each semantic chunk gets a content hash.

```text
semantic chunk
      ↓
SHA-256
      ↓
chunk_hash
```

The embedding cache is keyed by this hash.

Therefore:

```text
unchanged chunk
    ↓
reuse embedding
```

and:

```text
changed chunk
    ↓
new embedding
```

This prevents unnecessary embedding work after small source changes.

---

# Asynchronous Embeddings

Semantic indexing and embedding generation should be separate.

The semantic graph should become available first:

```text
Source
  ↓
Semantic Graph
  ↓
READY
```

Embedding generation happens afterward:

```text
Semantic Chunks
  ↓
Embedding Queue
  ↓
Local Embedding Worker
  ↓
Vector Index
```

A repository should still support structural queries while embeddings are being generated.

---

# Ignore Rules

The indexer should honor:

```text
.gitignore
.ckgignore
```

Files excluded from indexing should never enter the semantic or embedding pipeline.

This prevents indexing:

```text
secrets
credentials
build artifacts
dependencies
generated files
large binaries
```

unless explicitly requested.

---

# Index Generations

SQLite updates should be transactional.

Every successful indexing operation creates a new logical generation:

```text
generation 41
     ↓
apply update
     ↓
generation 42
```

Readers should see a consistent generation rather than a half-updated graph.

---

# Production Repository Flow

For a large repository:

```text
Repository
    ↓
Scan files
    ↓
Apply ignore rules
    ↓
Calculate hashes
    ↓
Detect changed files
    ↓
Parse only affected files
    ↓
Update semantic entities
    ↓
Update dependency relationships
    ↓
Invalidate affected chunks
    ↓
Regenerate changed embeddings
    ↓
Commit new index generation
```

The system should never rebuild all 100,000 files because one file changed.

---

# Retrieval Goal

For a query such as:

> How does authentication work?

We do not want:

```text
50 files
50,000 tokens
LLM
```

We want:

```text
Query
  ↓
Vector / FTS search
  ↓
AuthService.login
  ↓
Graph expansion
  ↓
validateUser
  ↓
createAuth
  ↓
JWTService
  ↓
Context Builder
  ↓
Only relevant source
  ↓
LLM
```

The exact token reduction must be measured, not assumed.

---

# Performance Goals

Measure:

```text
Initial indexing time
Incremental indexing time
Files changed per update
Symbols indexed
Relationships indexed
Chunk count
Embedding count
Embedding cache hit rate
Query latency
Retrieval recall@k
MRR
Context token count
```

A future benchmark should compare:

```text
Full-file baseline
vs
CKG retrieval
```

for a fixed query set.

Do not claim a specific token reduction until it is measured.

---

# Current Status

## Completed

- Tree-sitter parsing
- Document loading
- Symbol extraction
- Symbol ownership
- Symbol index
- Reference extraction
- Reference classification
- Basic name resolution
- Call relationship building
- Type-level symbols (`interface`, `type` alias) with exports, signatures,
  and resolution of imported type names
- Extends relationship building (resolved `class X extends Y` and
  `interface X extends Y` heritage)
- Implements relationship building (resolved `class X implements Y`)
- In-memory code graph
- Import extraction
- Module-level import resolution
- Local compiler pass structure
- Document index
- Local semantic models
- Stable symbol identities (qualified names, content/signature hashes, stable keys)
- Confidence-based rename / move matching across index runs
- SQLite persistence (schema, repositories, atomic snapshot persist / load round-trip)
- Incremental indexing (file-state inventory, hash-based change detection, selective re-resolution with interface-aware dependency invalidation)
- Export extraction and export resolution
- Cross-file name resolution (references resolve through imports)
- Member-expression resolution (access paths, namespace / `this` / class member calls)
- Merkle / hierarchical hashing
- Semantic chunking (content-addressed, keyed on each symbol's stable key)
- Local embedding provider and embedding store
- SQLite FTS5 lexical retrieval
- Local vector retrieval
- Hybrid retrieval (exact + graph + lexical + vector, fused by reciprocal rank)
- Graph-aware retrieval (budgeted seed neighbourhoods)
- Heuristic reranking
- Context builder (hard token budget)
- Asynchronous / incremental embedding worker
- Ignore rules (`.gitignore` / `.ckgignore`)
- Index generations
- Local CLI — `index`, `status`, `search`, `definition`, `callers`, `callees`, `imports`, `context`, `eval`, `watch`, `init`, `embed` (12 commands via `build_parser()`). Installed as `ckg` (and `ckg-mcp`) via `[project.scripts]` in `pyproject.toml`; invoke as `ckg <command>` (`python cli.py <command>` also works from a source checkout).
- MCP / agent integration (`mcp_server.py`)
- Evaluation suite

`IMPLEMENTATION.md` is the authoritative status document; its per-phase
`### Implemented` notes record exactly what each phase delivered.

## Not Yet Modelled

These are deliberate gaps, not oversights. They are listed here so the
semantic model is not mistaken for something broader than it is.

- **Interface members.** An interface's `property_signature` /
  `method_signature` members do not become child symbols — no existing
  handler understands those nodes, and half-extracting them would be
  worse than not extracting them. They are captured in the interface's
  signature instead, so a member change still invalidates importers.
- **Type analysis.** No inference; member resolution is structural. A
  `type_identifier` outside a heritage clause (an annotation, a generic
  argument) produces no reference, so `HAS_TYPE` / `RETURNS` edges do not
  exist. `CALLS`, `EXTENDS` and `IMPLEMENTS` are the only relationship
  kinds the graph emits.

## In Progress

(none)

## Planned

- Re-export resolution (`export { x } from` / `export * from`)
- Incremental persistence (each run currently rewrites the whole snapshot)

---

# Future Agent Integration

CKG should eventually run as a local service/library that coding agents can query before sending context to an LLM.

Target integrations:

```text
Claude Code
Codex CLI
Gemini CLI
Pi
OpenCode
Custom Agents
MCP clients
IDE extensions
```

Possible interface:

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

The agent should receive a small, relevant context pack rather than the entire repository.

---

# Long-Term Vision

```text
                 ┌─────────────────────┐
                 │    Code Repository  │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │ Semantic Compiler   │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │ Knowledge Graph     │
                 └──────────┬──────────┘
                            │
             ┌──────────────┴──────────────┐
             ▼                             ▼
      Exact Structural              Semantic Retrieval
          Search                         Search
             │                             │
             └──────────────┬──────────────┘
                            ▼
                      Context Builder
                            │
                            ▼
                           Agent
                            │
                            ▼
                           LLM
```

The graph provides structure.

The vector index provides semantic recall.

The retrieval layer combines both.

The context builder minimizes what reaches the model.

---

# Definition of Done for v1

v1 is complete when:

- TypeScript/JavaScript indexing is reliable.
- Source files are parsed once per indexing run.
- Symbols, imports, exports, references, and relationships are resolved correctly for common cases.
- The semantic graph is persisted in SQLite.
- File changes are detected incrementally.
- Unchanged chunks reuse their embeddings.
- FTS and vector search work locally.
- Graph expansion works during retrieval.
- Hybrid retrieval produces relevant top-k results.
- Context is assembled from semantic entities rather than whole files.
- Agent integrations can request context from CKG.
- Evaluation measures retrieval quality, latency, and token usage.

---

# Engineering Rule

When deciding what to build next, use this order:

```text
Correctness
    ↓
Semantic completeness
    ↓
Persistence
    ↓
Incremental indexing
    ↓
Retrieval quality
    ↓
Performance
    ↓
Agent integrations
```

Do not optimize embeddings before semantic resolution is trustworthy.

Do not optimize retrieval before the index is correct.

Do not optimize indexing before incremental updates are correct.

The central idea remains:

> **Understand the repository first. Retrieve only what matters. Then let the LLM reason over that context.**
## Session memory

CKG can keep a small, project-local memory of explicit decisions, code areas, and retrieval history so work can resume after an MCP restart. It is stored in `<project>/.ckg/session.sqlite` and is never synchronized to the cloud.

```bash
ckg sessions start .
ckg sessions list .
ckg sessions recall authentication .
ckg sessions export . --format markdown
ckg sessions prune . --days 30
```

MCP clients can use `session_start`, `session_status`, `session_recall`, `session_timeline`, `record_decision`, and `record_code_area`; `session_end` closes the active session. Omitting a session ID resumes or creates the active session for that normalized project path.

Only bounded explicit text and compact retrieval identifiers/metrics are stored. Raw source, complete tool output, transcripts, secrets, and environment variables are not stored. Use `ckg sessions prune` for age-based retention, or delete `.ckg/session.sqlite` to remove the local memory entirely.
