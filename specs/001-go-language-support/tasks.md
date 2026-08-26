# Tasks: Go Language Support

**Input**: [plan.md](plan.md) | **Branch**: `001-go-language-support`

## 1. Registration wiring (P1 — US1)

- [ ] 1.1 Add `tree-sitter-go` dependency; register `go` parser
- [ ] 1.2 Map `.go` in `ingestion/language.py`; add `.go` to
      `INCLUDE_EXTENSIONS`, `vendor/` to `EXCLUDE_DIRS` in `config.py`
- [ ] 1.3 Go symbol handlers (`function_declaration` → function,
      `method_declaration` → method, struct/interface `type_spec` → class)
      registered in `analysis/registry.py`
- [ ] 1.4 Guardrail updates: `test_language_support.py`,
      `test_document_loading.py`, `test_parse_pass.py`

## 2. Imports + resolution (P2 — US2)

- [ ] 2.1 `analysis/import_handlers/go_imports.py`: single + block form,
      alias support, blank-import tolerance; register in `import_registry`
- [ ] 2.2 `_resolve_go` in `normalize_path.py`: `<path>.go` candidate from
      repo root; register under `go`

## 3. Exports + references + chunks (P3 — US3)

- [ ] 3.1 `analysis/export_handlers/go_exports.py`: uppercase-initial rule;
      register for Go symbol node types
- [ ] 3.2 `LanguageProfile("go")`: call/member/identifier vocabulary
- [ ] 3.3 Chunker: Go import paths render unquoted-style (no `{ }` braces)

## 4. Fixture + end-to-end validation

- [ ] 4.1 Fixture repo `tests/fixtures/go_repo/` (auth.go, api.go with
      cross-file calls, imports incl. external)
- [ ] 4.2 `tests/test_go_pipeline.py`: extraction kinds, import resolution,
      exports rule, call edges, chunk presence, hybrid retrieval,
      incremental parity
- [ ] 4.3 Full suite green; basedpyright clean on touched modules
