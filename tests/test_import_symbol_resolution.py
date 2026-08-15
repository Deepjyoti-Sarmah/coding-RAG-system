import tempfile
import unittest
from pathlib import Path

from analysis.build_graph import build_graph


def _resolved_by_local_name(result, local_name: str):
    return next(
        r
        for r in result.resolved_import_references
        if r.import_reference.local_name == local_name
    )


class TestImportSymbolResolution(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

        root = Path(self._tmp.name)
        (root / "auth.ts").write_text(
            "export function login() {}\n"
            "export function logout() {}\n"
            "export default class AuthService {}\n",
            encoding="utf-8",
        )

    def _build(self, api_content: str):
        root = Path(self._tmp.name)
        (root / "api.ts").write_text(api_content, encoding="utf-8")
        return build_graph(str(root))

    def test_alias_import_resolves_to_exported_symbol(self):
        result = self._build('import { login as authLogin } from "./auth";\n')

        resolved = _resolved_by_local_name(result, "authLogin")

        self.assertIsNotNone(resolved.target_symbol)
        self.assertEqual(resolved.target_symbol.name, "login")
        self.assertEqual(resolved.target_symbol.relative_path, "auth.ts")

    def test_named_import_resolves_to_exported_symbol(self):
        result = self._build('import { logout } from "./auth";\n')

        resolved = _resolved_by_local_name(result, "logout")

        self.assertEqual(resolved.target_symbol.name, "logout")
        self.assertEqual(resolved.target_symbol.relative_path, "auth.ts")

    def test_default_import_resolves_to_default_export(self):
        result = self._build('import AuthService from "./auth";\n')

        resolved = _resolved_by_local_name(result, "AuthService")

        self.assertEqual(resolved.target_symbol.name, "AuthService")
        self.assertEqual(resolved.target_symbol.relative_path, "auth.ts")

    def test_namespace_import_has_no_single_symbol(self):
        result = self._build('import * as auth from "./auth";\n')

        resolved = _resolved_by_local_name(result, "auth")

        self.assertIsNotNone(resolved.target_document)
        self.assertIsNone(resolved.target_symbol)

    def test_missing_export_has_no_target_symbol(self):
        result = self._build('import { missing } from "./auth";\n')

        resolved = _resolved_by_local_name(result, "missing")

        self.assertIsNotNone(resolved.target_document)
        self.assertIsNone(resolved.target_symbol)

    def test_unresolved_module_produces_no_resolved_import(self):
        result = self._build('import { x } from "./does-not-exist";\n')

        self.assertEqual(result.resolved_import_references, [])


class TestPipelineImportResolution(unittest.TestCase):
    def test_test_repo_imports_resolve_to_exported_symbols(self):
        root = Path(__file__).resolve().parent.parent / "test_repo"
        result = build_graph(str(root))

        by_local = {
            r.import_reference.local_name: r
            for r in result.resolved_import_references
        }

        self.assertEqual(by_local["authLogin"].target_symbol.name, "login")
        self.assertEqual(
            by_local["authLogin"].target_symbol.relative_path,
            "auth.ts",
        )

        self.assertEqual(by_local["signOut"].target_symbol.name, "logout")
        self.assertEqual(by_local["login"].target_symbol.name, "login")

        # test_repo/auth.ts exports AuthService as a *named* export, so a
        # default import of it is a missing-export case.
        self.assertIsNone(by_local["AuthService"].target_symbol)


if __name__ == "__main__":
    unittest.main()
