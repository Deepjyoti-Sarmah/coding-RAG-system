# Code Knowledge Graph (CKG)

> _"The best way to reduce tokens is to stop sending irrelevant code."_

---

# Why this project exists

Most AI coding assistants work by retrieving pieces of text from a repository and sending them to a Large Language Model.

The problem is that **source code is not text**.

Source code is a structured system made of declarations, scopes, references, imports, types, ownership, and relationships.

If we treat code as plain text, we lose almost all of that structure.

As a result, current systems usually:

- embed entire files
- retrieve large chunks
- send unnecessary context
- waste tokens
- confuse the model with unrelated code

This project takes a different approach.

Instead of asking:

> "Which text looks similar to the user's question?"

we ask:

> **"Which semantic entities are actually required to answer the question?"**

That difference is the foundation of this project.

---

# The Long-Term Goal

The goal is to build a **Code Knowledge Graph** that understands a repository before any request reaches an LLM.

Instead of sending:

```text
20 files

↓

35,000 tokens

↓

LLM
```

the system should send something closer to:

```text
3 Symbols

2 Imports

5 References

1 Call Chain

↓

1,500 tokens

↓

LLM
```

The exact reduction depends on the repository and query, but the architecture is designed to make large reductions possible by retrieving semantic information instead of entire files.

The LLM should become the final consumer of the graph—not the system responsible for understanding the repository.

---

# Think Like a Compiler

When people first build Code RAG systems, they usually think:

```text
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

That architecture treats code like documentation.

A compiler thinks differently.

```text
Repository

↓

Parser

↓

AST

↓

Semantic Analysis

↓

Program Understanding
```

We are borrowing that mindset.

The output of this project is **not embeddings**.

The output is a semantic understanding of the repository.

Embeddings become one consumer of that understanding.

---

# Think Like a Graph Database

Another useful mental model is a graph database.

A graph consists of only two things:

```text
Nodes

Edges
```

For source code:

```text
Entities

Relationships
```

Everything we build should belong to one of those two categories.

If something exists independently, it is an **Entity**.

If something connects two entities, it is a **Relationship**.

Keeping this distinction clear makes the architecture easy to extend.

---

# Project Architecture

```text
  Repository
        │
        ▼
  Document Loader
        │
        ▼
  Tree-sitter Parser
        │
        ▼
  Semantic Analysis Pipeline
        │
  ┌────┴────────────────────┐
  ▼                         ▼
  Entities              Relationships
  │                         │
  └──────────┬──────────────┘
             ▼
    Code Knowledge Graph
             │
    ┌────────┼─────────┐
    ▼        ▼         ▼
  Search   Navigation   AI Context Builder
              │
              ▼
             LLM
```

Notice that the LLM is at the very end of the pipeline.

The graph—not the LLM—is responsible for understanding the repository.

---

# First Principle

Every compiler pass should answer exactly one question.

Not two.

Not five.

Exactly one.

This keeps the system easy to reason about and easy to extend.

---

# Semantic Analysis Pipeline

## Pass 1 — Document Pass ✅

Question answered:

> **What files exist in this repository?**

Produces:

```text
Document
```

A document contains metadata about a source file.

Examples:

- language
- path
- size
- content
- line count

---

## Pass 2 — Symbol Pass ✅

Question answered:

> **What declarations exist?**

Produces:

```text
Symbol
```

Current support:

- Function
- Method
- Class
- Variable

Planned:

- Interface
- Type Alias
- Enum
- Namespace

A Symbol represents something that can be referenced elsewhere.

---

## Pass 3 — Declares Pass

Question answered:

> **Which document owns which symbols?**

Produces:

```text
Document

DECLARES

Symbol
```

Notice that ownership is represented as a graph edge rather than hidden inside objects.

---

## Pass 4 — Import Pass

Question answered:

> **Which names become visible inside this document?**

Produces:

```text
Import
```

This pass does not resolve symbols.

It only extracts import declarations.

---

## Pass 5 — Export Pass

Question answered:

> **Which symbols are exposed outside this document?**

Produces:

```text
Export
```

---

## Pass 6 — Reference Pass

Question answered:

> **Where are symbols used?**

Example:

```ts
login();
login();
login();
```

These are three different references.

Not one.

This distinction becomes important for:

- Find References
- Rename Symbol
- Context Retrieval

---

## Pass 7 — Name Resolution Pass

Question answered:

> **Which declaration does this reference actually point to?**

Today we resolve calls using symbol names.

Eventually we will resolve references using:

- imports
- exports
- lexical scope
- namespaces

Exactly like a compiler.

---

## Pass 8 — Call Graph Pass ✅ (Initial Version)

Question answered:

> **Who calls whom?**

Current support:

```ts
foo();

auth.login();

client.auth.login();
```

Future versions will resolve calls through imports instead of relying only on symbol names.

---

## Pass 9 — Type Analysis Pass

Question answered:

> **What type does this symbol represent?**

Future features:

- Return types
- Parameter types
- Generic types
- Interface implementations

---

## Pass 10 — Chunk Pass ✅

This is where semantic information becomes retrieval-friendly.

Instead of chunking raw text, we chunk semantic entities.

Each chunk can include:

- symbol
- callers
- callees
- ownership
- file
- surrounding context

The chunk is already enriched before embeddings are created.

---

## Pass 11 — Embedding Pass

Embeddings belong to retrieval.

Not parsing.

Not semantic analysis.

This separation allows us to swap embedding models without rebuilding the graph.

---

# Current Graph Model

## Entities

Current:

```text
Document

Symbol
```

Planned:

```text
Import

Export

Reference

Type

Chunk

Embedding
```

Every entity has its own identity because it may be referenced by future analysis passes.

---

## Relationships

Current:

```text
CALLS
```

Planned:

```text
DECLARES

IMPORTS

EXPORTS

REFERS_TO

RESOLVES_TO

EXTENDS

IMPLEMENTS

USES

RETURNS

HAS_PARAMETER

HAS_TYPE
```

Relationships never duplicate information.

They only connect existing entities.

---

# Software Engineering Principles

## 1. One Source of Truth

Relationships are stored once.

Indexes are derived from them.

```text
Relationships

↓

Outgoing Index

Incoming Index
```

Indexes should never own data.

---

## 2. One Responsibility Per Pass

Every pass answers one question.

If a pass starts answering multiple unrelated questions, split it.

---

## 3. Separate Semantics from Retrieval

Semantic analysis should understand code.

Retrieval should understand search.

Embedding models should understand vectors.

Do not mix these concerns.

---

## 4. Build Intermediate Representations

Every stage should produce an intermediate representation that another stage can consume.

For example:

```text
AST

↓

Symbols

↓

Knowledge Graph

↓

Semantic Chunks

↓

Embeddings
```

Each layer builds on the previous one.

---

## 5. Design for Extension

Adding support for another language should require implementing new analysis passes—not rewriting the architecture.

The graph should remain language-independent.

---

# Why This Matters

Imagine a user asks:

> "Where is authentication implemented?"

A traditional RAG system retrieves text that happens to mention "authentication."

This system should instead traverse the graph.

For example:

```text
Reference

↓

Symbol

↓

Call Graph

↓

Imports

↓

Related Symbols

↓

Semantic Chunk

↓

LLM
```

Only the information required to answer the question is sent to the model.

The repository itself never leaves the machine.

---

# Future Vision

Eventually this project should become the semantic engine underneath coding assistants.

Instead of every assistant reparsing the repository independently, they should query the same Code Knowledge Graph.

That graph should power:

- Semantic Search
- Context Compression
- Find References
- Go to Definition
- Rename Symbol
- Dependency Analysis
- Repository Navigation
- AI Context Building
- IDE Extensions
- CLI Agents
- Automated Refactoring

The LLM should answer questions.

The Code Knowledge Graph should understand the repository.
