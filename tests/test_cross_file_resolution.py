import tempfile
import unittest
from pathlib import Path

from analysis.build_graph import build_graph
from models.entities.resolved_reference import ResolutionStatus
from models.relationships.relationship_kind import RelationshipKind


def _build(*, files: dict[str, str]):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for name, content in files.items():
            (root / name).write_text(content, encoding="utf-8")
        return build_graph(str(root))


def _symbol_by_name(result, name: str):
    return next(s for s in result.symbols if s.name == name)


def _resolved_for(result, owner_symbol_name: str, reference_name: str):
    owner = _symbol_by_name(result, owner_symbol_name)
    return [
        r
        for r in result.resolved_references
        if r.reference.owner_symbol_id == owner.symbol_id
        and r.reference.name == reference_name
    ]


def _calls_from(result, source_symbol_name: str) -> list[str]:
    source = _symbol_by_name(result, source_symbol_name)
    return [
        r.target_symbol_id
        for r in result.relationships
        if r.kind == RelationshipKind.CALLS
        and r.source_symbol_id == source.symbol_id
    ]


def _auth_api(api_content: str) -> dict[str, str]:
    return {
        "auth.ts": "export function login() {}\n"
        "export function logout() {}\n"
        "export default class AuthService {}\n",
        "api.ts": api_content,
    }


class TestCrossFileResolution(unittest.TestCase):
    def test_named_import_call_resolves_to_exported_symbol(self):
        result = _build(
            files=_auth_api(
                'import { login } from "./auth";\n'
                "function callIt() {\n"
                "  login();\n"
                "}\n"
            )
        )

        resolved = _resolved_for(result, "callIt", "login")

        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].status, ResolutionStatus.RESOLVED)
        self.assertEqual(resolved[0].target_symbol.name, "login")
        self.assertEqual(resolved[0].target_symbol.relative_path, "auth.ts")

    def test_named_import_call_emits_cross_file_relationship(self):
        result = _build(
            files=_auth_api(
                'import { login } from "./auth";\n'
                "function callIt() {\n"
                "  login();\n"
                "}\n"
            )
        )

        calls = _calls_from(result, "callIt")

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], _symbol_by_name(result, "login").symbol_id)

    def test_alias_import_call_resolves_to_exported_symbol(self):
        result = _build(
            files=_auth_api(
                'import { login as authLogin } from "./auth";\n'
                "function callIt() {\n"
                "  authLogin();\n"
                "}\n"
            )
        )

        resolved = _resolved_for(result, "callIt", "authLogin")

        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].status, ResolutionStatus.RESOLVED)
        self.assertEqual(resolved[0].target_symbol.name, "login")
        self.assertEqual(resolved[0].target_symbol.relative_path, "auth.ts")

    def test_default_import_call_resolves_to_default_export(self):
        result = _build(
            files=_auth_api(
                'import AuthService from "./auth";\n'
                "function callIt() {\n"
                "  AuthService();\n"
                "}\n"
            )
        )

        resolved = _resolved_for(result, "callIt", "AuthService")

        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].status, ResolutionStatus.RESOLVED)
        self.assertEqual(resolved[0].target_symbol.name, "AuthService")
        self.assertEqual(resolved[0].target_symbol.relative_path, "auth.ts")

    def test_duplicate_imports_of_same_symbol_stay_resolved(self):
        result = _build(
            files=_auth_api(
                'import { login } from "./auth";\n'
                'import { login as login } from "./auth";\n'
                "function callIt() {\n"
                "  login();\n"
                "}\n"
            )
        )

        resolved = _resolved_for(result, "callIt", "login")

        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].status, ResolutionStatus.RESOLVED)
        self.assertEqual(resolved[0].target_symbol.relative_path, "auth.ts")

    def test_nested_scope_falls_through_to_imports(self):
        result = _build(
            files=_auth_api(
                'import { login } from "./auth";\n'
                "function outer() {\n"
                "  function inner() {\n"
                "    login();\n"
                "  }\n"
                "}\n"
            )
        )

        resolved = _resolved_for(result, "inner", "login")

        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].status, ResolutionStatus.RESOLVED)
        self.assertEqual(resolved[0].target_symbol.relative_path, "auth.ts")


class TestImportShadowing(unittest.TestCase):
    def test_module_scope_symbol_shadows_imported_name(self):
        result = _build(
            files=_auth_api(
                'import { login } from "./auth";\n'
                "function login() {}\n"
                "function callIt() {\n"
                "  login();\n"
                "}\n"
            )
        )

        resolved = _resolved_for(result, "callIt", "login")

        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].status, ResolutionStatus.RESOLVED)
        self.assertEqual(resolved[0].target_symbol.relative_path, "api.ts")


class TestImportAmbiguity(unittest.TestCase):
    def test_duplicate_local_name_from_two_modules_is_ambiguous(self):
        result = _build(
            files={
                "a.ts": "export function dup() {}\n",
                "b.ts": "export function dup() {}\n",
                "api.ts": 'import { dup } from "./a";\n'
                'import { dup } from "./b";\n'
                "function callIt() {\n"
                "  dup();\n"
                "}\n",
            }
        )

        resolved = _resolved_for(result, "callIt", "dup")

        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].status, ResolutionStatus.AMBIGUOUS)
        self.assertIsNone(resolved[0].target_symbol)
        self.assertEqual(_calls_from(result, "callIt"), [])


class TestUnresolvedImports(unittest.TestCase):
    def test_namespace_import_is_not_guessed(self):
        result = _build(
            files=_auth_api(
                'import * as auth from "./auth";\n'
                "function callIt() {\n"
                "  auth();\n"
                "}\n"
            )
        )

        resolved = _resolved_for(result, "callIt", "auth")

        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].status, ResolutionStatus.UNRESOLVED)
        self.assertIsNone(resolved[0].target_symbol)
        self.assertEqual(_calls_from(result, "callIt"), [])

    def test_missing_export_import_is_not_guessed(self):
        result = _build(
            files=_auth_api(
                'import { missing } from "./auth";\n'
                "function callIt() {\n"
                "  missing();\n"
                "}\n"
            )
        )

        resolved = _resolved_for(result, "callIt", "missing")

        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].status, ResolutionStatus.UNRESOLVED)
        self.assertIsNone(resolved[0].target_symbol)
        self.assertEqual(_calls_from(result, "callIt"), [])

    def test_unresolved_module_import_is_not_guessed(self):
        result = _build(
            files=_auth_api(
                'import { x } from "./does-not-exist";\n'
                "function callIt() {\n"
                "  x();\n"
                "}\n"
            )
        )

        resolved = _resolved_for(result, "callIt", "x")

        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].status, ResolutionStatus.UNRESOLVED)
        self.assertIsNone(resolved[0].target_symbol)
        self.assertEqual(_calls_from(result, "callIt"), [])


if __name__ == "__main__":
    unittest.main()
