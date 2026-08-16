# Code Knowledge Graph (CKG)

> A local-first semantic code intelligence engine for AI coding agents.

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
```

Planned:

```text
INTERFACE
TYPE_ALIAS
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

Current:

```text
CALLS
```

Planned:

```text
IMPORTS
DECLARES
EXPORTS
REFERS_TO
EXTENDS
IMPLEMENTS
USES
OVERRIDES
HAS_TYPE
RETURNS
```

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

Conceptually:

```text
Symbol
   │
   ├── CALLS ───────────→ Symbol
   ├── IMPORTS ─────────→ Document / Symbol
   ├── EXTENDS ─────────→ Symbol
   ├── IMPLEMENTS ──────→ Symbol
   └── USES ────────────→ Symbol
```

The graph should support:

```text
callers_of(symbol)
callees_of(symbol)
imports_of(document)
imported_by(document)
children_of(symbol)
parents_of(symbol)
```

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
- In-memory code graph
- Import extraction
- Module-level import resolution
- Local compiler pass structure
- Document index
- Local semantic models
- Stable symbol identities (qualified names, content/signature hashes, stable keys)
- Confidence-based rename / move matching across index runs

## In Progress

- Resolve imported names to exported symbols
- Parse each document once using `ParsedDocument`
- Wire import passes into the main pipeline

## Planned

- Export extraction
- Export resolution
- Cross-file symbol resolution
- Better lexical scope resolution
- Member-expression resolution
- Type analysis
- SQLite persistence
- Incremental indexing
- Merkle/hierarchical hashing
- Semantic chunk generation
- Local embeddings
- FTS5
- Vector index
- Hybrid retrieval
- Reranking
- Context builder
- Agent integration
- Evaluation suite

---

# Immediate Next Tasks

Implement in this order:

1. Finish `ParsedDocument`
2. Parse every file once
3. Add `import_pass`
4. Run import resolver in the pipeline
5. Resolve imports to actual exported symbols
6. Add export extraction
7. Improve cross-file semantic resolution
8. Add SQLite persistence
9. Add incremental indexing
10. Rebuild semantic chunking on top of the graph
11. Add local vector indexing
12. Add hybrid retrieval
13. Add reranking
14. Add context building
15. Integrate with coding agents

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
