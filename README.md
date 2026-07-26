
````markdown
# Code Knowledge Graph (CKG)

> **A compiler-inspired semantic engine for source code.**
>
> The goal is to understand a repository before an LLM sees it, allowing AI coding assistants to retrieve only the code that actually matters instead of entire files.

---

# Vision

Traditional Code RAG:

```
Repository
    ↓
Chunk Files
    ↓
Embeddings
    ↓
Vector Search
    ↓
LLM
```

CKG:

```
Repository
    ↓
Parser
    ↓
Semantic Analysis
    ↓
Knowledge Graph
    ↓
Context Builder
    ↓
LLM
```

The LLM should answer questions.

The Code Knowledge Graph should understand the repository.

---

# Philosophy

- Think like a **compiler**, not a chatbot.
- Think in **entities and relationships**, not text chunks.
- Every compiler pass answers **one question**.
- Parse once, reuse forever.
- Keep semantic analysis independent from retrieval.

---

# Current Architecture

```
Repository
      │
      ▼
Document Loader
      │
      ▼
Tree-sitter Parser
      │
      ▼
Semantic Compiler Pipeline
      │
      ▼
Knowledge Graph
      │
      ▼
Context Builder
      │
      ▼
LLM
```

---

# Current Compiler Pipeline

```
Load Documents                     ✅

↓

Parse Documents                    ✅

↓

Extract Symbols                    ✅

↓

Extract Imports                    ✅

↓

Resolve Imports (Module)           ✅

↓

Extract References                 ✅

↓

Resolve References                 ✅

↓

Build Relationships                ✅

↓

Knowledge Graph                    ✅
```

---

# Implemented Entities

### Document

Represents a source file.

### Symbol

Represents declarations such as:

- Function
- Class
- Method
- Variable

### ImportReference

Represents an import statement.

Example:

```ts
import { login } from "./auth";
```

### ResolvedImportReference

Represents the resolved module.

```
"./auth"

↓

auth.ts
```

### Reference

Represents every symbol usage.

Example:

```ts
login();
login();
```

These are two different references.

### ResolvedReference

Maps a reference to the declaration it points to.

---

# Current Relationships

Implemented

```
CALLS
```

Planned

```
IMPORTS
DECLARES
EXPORTS
REFERS_TO
EXTENDS
IMPLEMENTS
HAS_TYPE
```

---

# Current Project Status

## Completed ✅

- Document loading
- Tree-sitter parsing
- Symbol extraction
- Symbol ownership
- Symbol index
- Import extraction
- Import resolution (module level)
- Reference extraction
- Reference resolution
- Relationship builder
- Call graph
- Knowledge graph

---

## In Progress 🚧

### Imported Symbol Resolution

Current:

```
ImportReference

↓

ResolvedImportReference

↓

Document
```

Target:

```
ImportReference

↓

ResolvedImportReference

↓

Symbol
```

This will enable true cross-file symbol resolution.

---

# Immediate Refactor

## Parse Once

Currently every compiler pass reparses the same source file.

Current:

```
Symbol Pass

↓

Parse
```

```
Import Pass

↓

Parse
```

```
Reference Pass

↓

Parse
```

Target:

```
Load Documents

↓

Parse Once

↓

ParsedDocument[]

↓

Symbol Pass

↓

Import Pass

↓

Reference Pass
```

This matches how production compilers and language servers work.

---

# Next Milestones

1. Resolve imported symbols
2. Parse documents once (`ParsedDocument`)
3. Export extraction
4. Export resolution
5. Cross-file symbol resolution
6. Member expression resolution
7. Type analysis
8. Semantic chunk generation
9. Embedding pipeline
10. Incremental indexing

---

# Long-Term Roadmap

```
Repository

↓

Semantic Compiler

↓

Knowledge Graph

↓

Semantic Retrieval

↓

Context Compression

↓

LLM
```

Eventually the graph should power:

- Semantic Search
- Find References
- Go To Definition
- Rename Symbol
- Dependency Analysis
- AI Context Building
- CLI Coding Agents
- IDE Extensions

---

# Technical Debt

Current improvements planned:

- Parse every file only once
- Better lexical scope resolution
- Export analysis
- Namespace resolution
- Alias import resolution
- Type analysis
- Incremental indexing
- Multi-language support

---

# Design Principles

## One Responsibility Per Pass

Every compiler pass answers exactly one question.

---

## Semantic Before Retrieval

Understand the code first.

Search later.

---

## Build Intermediate Representations

```
Source Code

↓

AST

↓

Symbols

↓

References

↓

Relationships

↓

Knowledge Graph

↓

Semantic Chunks

↓

Embeddings
```

---

## Language Agnostic

The graph should remain language-independent.

Adding a new language should require implementing new analysis passes—not rewriting the architecture.

---

# End Goal

A production-grade semantic engine that can be shared by coding assistants like:

- Claude Code
- Codex CLI
- Gemini CLI
- Cursor
- Continue
- Custom AI Agents

Instead of sending entire files to an LLM, the system should send only the semantic entities required to answer the user's question.

The graph understands the repository.

The LLM reasons over that understanding.
````
