# CKG Constitution

## Core Principles

### I. Local-First, Zero-Ops
Every capability runs offline against files the user already owns. No cloud APIs,
no database servers, no daemons required for core function: one SQLite file plus
bundled extensions is the entire footprint. New dependencies must preserve this
(sqlite-vec over a vector DB service; local embedding models over remote APIs),
and every external integration needs a graceful in-repo fallback (NumpyVectorStore,
chars/4 token heuristic) so failure degrades rather than breaks.

### II. Incremental Equals Full (NON-NEGOTIABLE)
Any incremental path (reindex, re-resolution, delta persistence) must produce
state equivalent to a cold full rebuild. This invariant is enforced by tests
(`test_pipeline_parity.py`, `TestDeltaPersistence`) and no optimization is
acceptable if it weakens it. Change detection uses cheap hints only as hints;
content hashes remain the source of truth.

### III. Tests Before Moving Forward
One task at a time, small changes, tests before advancing. Every bug fix lands
with a regression test reproducing it; every feature lands with unit coverage
plus end-to-end pipeline coverage where behavior crosses layers. The full suite
must stay green before any commit.

### IV. Language-Neutral Core, Profiles at the Edge
Models, chunking, diffing, storage, retrieval, and evaluation never see
tree-sitter node types or language names. All grammar-specific knowledge lives
in per-language handler tables and `LanguageProfile`. Adding a language means
registering handlers and a resolver - not editing shared code.

### V. Layered Dependencies Point Downward
`cli`/`mcp_server` -> indexing/retrieval -> analysis/chunking -> models ->
storage. Storage knows nothing about analysis; models know nothing about
anything. Interfaces (`EmbeddingProvider`, `VectorStore`) isolate the outside
world; fakes replace real providers in tests.

### VI. Measure, Then Decide
Retrieval-quality decisions are driven by the evaluation harness (recall@k,
MRR, definition accuracy, token reduction), not intuition. Performance claims
(cache hits, incremental speedups) get tests that assert them.

### VII. Simplicity Over Speculation
No speculative abstractions. YAGNI applies to code and schema alike; design may
change when implementation evidence shows the current approach is wrong.
Complexity must be justified by a measured need.

## Additional Constraints

- Python 3.11+; dependencies added only through `pyproject.toml` with rationale
  in the commit message.
- SQLite is the sole persistence engine; WAL mode on; all writes transactional
  with snapshot-consistent reads.
- Type-checked with basedpyright: new/modified modules land with zero errors;
  pre-existing debt is not expanded.
- Public data models are immutable-ish frozen/slots dataclasses; keyword-only
  arguments at internal call sites.

## Development Workflow

- Work proceeds spec-first through Spec Kit: `/speckit.specify` ->
  `/speckit.plan` -> `/speckit.tasks` -> `/speckit.implement` ->
  `/speckit.converge`, with `/speckit.clarify` when requirements are ambiguous.
- Commits are thematic and conventional (`feat:`/`fix:`/`perf:`/`refactor:`/
  `chore:`); the suite must pass at every pushed HEAD.
- Feature work touching retrieval quality requires an eval run before/after.

## Governance

This constitution supersedes ad-hoc practice where they conflict. Amendments
require updating this file with a version bump and a commit message explaining
the change. Anything not covered here defaults to `IMPLEMENTATION.md` guidance.

**Version**: 1.1.0 | **Ratified**: 2026-08-26 | **Last Amended**: 2026-08-27
