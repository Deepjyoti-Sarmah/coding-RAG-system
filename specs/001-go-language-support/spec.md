# Feature Specification: Go Language Support

**Feature Branch**: `001-go-language-support`

**Created**: 2026-08-26

**Status**: Draft

**Input**: User description: "Add Go to the set of supported languages: parse Go files, extract symbols (functions, methods, structs, interfaces), imports and exports, resolve imports across the repository, chunk symbols for embedding, and make everything retrievable through hybrid search — following the same per-language-profile architecture used for TypeScript/JavaScript and Python."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Index a Go repository end-to-end (Priority: P1)

A developer points CKG at a repository containing `.go` files. Running
`ckg index` extracts every top-level function, struct type, interface type,
and method with correct kinds, persists them alongside documents/chunks,
and reports parsed-file counts in the run summary.

**Why this priority**: Without correct extraction nothing else (search,
graph, context packs) works. This is the standalone MVP slice.

**Independent Test**: Index a fixture Go repository; assert symbol names,
kinds, and file paths match expectations.

**Acceptance Scenarios**:

1. **Given** a repo with Go functions, structs, interfaces and methods,
   **When** `ckg index` runs, **Then** every construct appears as a Symbol
   with kind `function`, `class`, or `method` and the right relative path.
2. **Given** a Go file with syntax errors, **When** indexing runs, **Then**
   the file is flagged as having parse errors without crashing the run.
3. **Given** any mixed TS/Python/Go repository, **When** indexed twice,
   **Then** the second run reports all Go files UNCHANGED (mtime+hash fast
   path works for Go too).

---

### User Story 2 - Go imports resolve across files (Priority: P2)

When one Go file imports another package/file inside the same repository,
the import resolves to that document and its exported symbols, so callers/
callees queries and import listings return exact answers.

**Why this priority**: Cross-file resolution is what elevates CKG above
text search; it depends on extraction but is independently verifiable.

**Independent Test**: Index two Go files where `main.go` imports
`"myrepo/auth"`; assert the resolved import target document is `auth.go`
and named symbols link up.

**Acceptance Scenarios**:

1. **Given** `import "myrepo/auth"` in one file and `auth.go` at the repo
   root, **When** resolution runs, **Then** the import resolves to
   `auth.go`.
2. **Given** an import of an external module (`github.com/x/y`), **When**
   resolution runs, **Then** it stays unresolved without errors.
3. **Given** a dot-separated import path, **When** resolution runs,
   **Then** candidates are tried as `<path>.go`.

---

### User Story 3 - Capitalized names are exports; retrieval works (Priority: P3)

Go's export rule is lexical: names starting with an uppercase letter are
public. Exported functions/types/methods become Exports, chunks carry
Go-style import rendering in their embedding text, and hybrid search finds
Go symbols by natural-language query.

**Why this priority**: Completes parity with TS/Python support; retrieval
quality depends on chunks and exports from US1/US2.

**Independent Test**: Assert exports for a fixture repo contain exactly the
capitalized top-level names; run a semantic search query against an indexed
Go repo and confirm relevant Go symbols surface.

**Acceptance Scenarios**:

1. **Given** top-level `func CreateUser`, `func helper`, `type Store`,
   **When** exports are extracted, **Then** `CreateUser` and `Store` are
   exports and `helper` is not.
2. **Given** methods defined on receiver types, **When** export extraction
   runs, **Then** only uppercase method names are exported by their type's
   document.
3. **Given** an indexed Go repo, **When** querying "token validation",
   **Then** relevant Go symbols appear among hybrid-search results.

---

### Edge Cases

- Generic functions/types (`func Map[T any](...)`) must extract under their
  declared name.
- Blank imports (`import _ "x"`) and dot-less aliases must not crash
  extraction.
- Build-tagged duplicate declarations: last-wins is acceptable v1 behavior;
  no crash.
- Files under `vendor/` must be excluded like other dependency directories.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-1**: `.go` files are discovered, language-detected (`go`), and
  parsed via tree-sitter-go through the existing parser registry.
- **FR-2**: Symbols extracted: `function_declaration` → function,
  `method_declaration` → method (owned by receiver type when present),
  struct/interface `type_spec` → class.
- **FR-3**: Imports extracted from `import_declaration` (single and block
  form), recording module path, imported package name (last path segment),
  and local alias when present.
- **FR-4**: Module resolution maps an import path to candidate repo-relative
  paths `<path>.go`; external/unresolvable paths stay unresolved silently.
- **FR-5**: Exports follow Go visibility: uppercase-initial top-level
  declarations and methods.
- **FR-6**: References extracted for identifiers and selector expressions
  (`pkg.Symbol` member path); call relationships derived from resolved
  calls.
- **FR-7**: Chunks built per symbol with Go-style import rendering in
  embedding text.
- **FR-8**: All work follows the project constitution: incremental equals
  full rebuild parity, tests before forward, no shared-pipeline edits.

### Assumptions

- Repository root is the module root; module prefix stripping from
  `go.mod` is out of scope for v1 (documented limitation).
- Interfaces' implicit satisfaction produces no IMPLEMENTS edges in v1.
- Generics produce plain named symbols (no type-parameter modeling).

### Dependencies / Constraints

- Constitution principles I (local-first: tree-sitter-go grammar bundled
  as a normal pip dep), II (parity), IV (language-neutral core: changes
  confined to profiles/handlers/registries), VII (v1 simplicity).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-1**: A fixture Go repository indexes with 100% of expected symbols
  extracted with correct kinds (verified by test assertions).
- **SC-2**: Intra-repo imports resolve (≥ 90% of intra-repo imports in the
  fixture) while external imports stay unresolved.
- **SC-3**: Hybrid search on an indexed Go repo returns relevant Go symbols
  for natural-language queries (fixture assertions pass).
- **SC-4**: Incremental reindex after editing one Go file reparses only
  that file and preserves cross-file call edges (parity holds).
- **SC-5**: Full existing suite stays green (no regressions in TS/Python
  support).

## Key Entities *(include if feature involves data)*

- **Symbol**: existing model; Go fills kinds function/class/method with
  qualified names `file::name`.
- **ImportReference**: module_path = raw import string; local_name = alias
  or last path segment.
- **Export**: exported_name == symbol_name == capitalized declaration name.
- **LanguageProfile("go")**: node-type vocabulary for Go grammar
  (call_expression/function field, selector_expression member shape).

## Review & Acceptance Checklist

Gate content quality before planning:

- [x] Focused on user value, no implementation choices leaked into stories
- [x] All mandatory sections completed
- [x] Requirements are testable and unambiguous within stated assumptions
- [x] Success criteria measurable

*(Execution details live in plan.md and tasks.md per the SDD workflow.)*
