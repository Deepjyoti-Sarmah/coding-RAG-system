# Implementation Plan: Go Language Support

**Branch**: `001-go-language-support` | **Date**: 2026-08-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-go-language-support/spec.md`

## Summary

Add Go as a third supported language by registering a Go entry in every
per-language table: parser registry, extension/language maps, symbol/import/
export handler tables, a `LanguageProfile("go")`, and an import resolver.
Zero edits to shared pipeline code (Constitution IV). Grammar research
(Phase 0) verified node shapes empirically against tree-sitter-go 0.25.

## Technical Context

**Language/Version**: Python 3.14 (existing project)
**Primary Dependencies**: tree-sitter-go 0.25 (added), existing tree-sitter stack
**Storage**: unchanged (SQLite via storage/)
**Testing**: existing unittest suite; new fixture repo + end-to-end tests
**Target Platform**: Linux CLI / MCP server (unchanged)
**Performance Goals**: unchanged — Go files ride the existing incremental pipeline
**Constraints**: offline-safe bundled grammar; no shared-pipeline edits
**Scale/Scope**: one new language; ~6 new/changed registration files

## Constitution Check

| Principle | Status |
|---|---|
| I Local-first | PASS — tree-sitter-go is a bundled pip dep |
| II Incremental = full | PASS — rides existing diff/persist; SC-4 asserts parity |
| III Tests first | PASS — fixture + e2e tests land with handlers |
| IV Neutral core | PASS — only registrations + new handler files |
| V Layering | PASS — handlers import builder/utils only |
| VI Measure | PASS — retrieval asserted in tests |
| VII Simplicity | PASS — no go.mod parsing, no IMPLEMENTS edges in v1 |

## Phase 0 Research (verified empirically)

tree-sitter-go node shapes (from live parse of representative source):

- `function_declaration`: `name` field → identifier. Generics use a
  separate `type_parameters` field; name extraction unaffected.
- `method_declaration`: `receiver`, `name` (a `field_identifier`),
  parameters/result/body. Method kind regardless of receiver; ownership
  follows the enclosing-type rule below.
- Types: `type_declaration` → `type_spec` (`name` + `type`), where `type`
  is `struct_type` or `interface_type`. Extracted as class-kind symbols.
- Imports: `import_declaration` → `import_spec_list` → `import_spec`
  (`path` = interpreted_string_literal, optional `name` = package_identifier
  alias). Both single and parenthesized block forms.
- Calls: `call_expression` (`function` field) — same shape as Python.
- Members: `selector_expression` (`operand` + `field`); leaf identifiers:
  `identifier`, `field_identifier`; type names: `type_identifier`.
- No extends/implements clauses (implicit satisfaction) — v1 emits none.

## Decisions

1. **Method→class ownership**: methods are top-level in Go's AST. v1 keeps
   them as method-kind symbols without parent linking (qualified names are
   file-scoped); receiver-type modeling deferred (matches "instance-blind
   resolution" TS/Python v1 stance).
2. **Export rule**: uppercase-initial name ⇒ export, applied to top-level
   functions/types and methods. Implemented as a handler on the same node
   types as symbols, mirroring the Python implicit-export pattern.
3. **Import local_name**: alias if present, else last path segment
   (`myrepo/token` → `token`). Raw path kept in module_path verbatim.
4. **Resolution**: candidates `[<path>.go]` relative to repo root;
   anything unresolvable stays unresolved (external modules). No go.mod
   prefix stripping in v1.
5. **Profile**: call_parent=`call_expression`/function field (TS-like),
   member_node=`selector_expression` (operand/field),
   identifier_nodes={identifier, field_identifier},
   heritage_only_nodes={type_identifier} restricted to nothing (no heritage
   clauses) — but type_identifier must NOT flood references, so it is
   excluded from reference extraction entirely in v1 except where already
   covered by declaration filtering.
6. **vendor/**: added to EXCLUDE_DIRS.

## Project Structure

```text
analysis/symbol_handlers/go_function.py      # function + method handlers
analysis/export_handlers/go_exports.py       # capitalized-name rule
analysis/import_handlers/go_imports.py       # import_spec handling
specs/001-go-language-support/{plan,tasks}.md
```

Changed registrations: `parsing/registry.py`, `ingestion/language.py`,
`config.py`, `analysis/{registry,import_registry,export_registry}.py`,
`analysis/languages.py`, `analysis/semantic/normalize_path.py`.

Tests: `tests/fixtures/go_repo/*`, `tests/test_go_pipeline.py`,
updates to `tests/test_language_support.py`, `test_document_loading.py`,
`test_parse_pass.py` (language lists).
