import tempfile
import unittest
from pathlib import Path

from analysis.build_graph import build_graph
from models.entities.symbol_kind import SymbolKind


def _build(content: str):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "auth.ts").write_text(content, encoding="utf-8")
        return build_graph(str(root))


def _symbols_by_name(result, name: str):
    return [s for s in result.symbols if s.name == name]


class TestStableIdentity(unittest.TestCase):
    FIXTURE = (
        "export function login(username: string): Promise<boolean> {\n"
        "  return true;\n"
        "}\n"
        "export default class AuthService {\n"
        "  validateUser(name: string) { return true; }\n"
        "}\n"
        "function outer() {\n"
        "  function inner() { return 1; }\n"
        "  return inner;\n"
        "}\n"
    )

    def test_identity_is_deterministic_across_runs(self):
        first = _build(self.FIXTURE)
        second = _build(self.FIXTURE)

        first_ids = {
            s.name: (s.qualified_name, s.content_hash, s.signature_hash, s.stable_key)
            for s in first.symbols
        }
        second_ids = {
            s.name: (s.qualified_name, s.content_hash, s.signature_hash, s.stable_key)
            for s in second.symbols
        }

        self.assertEqual(first_ids, second_ids)
        self.assertTrue(
            all(key for key in first_ids.values()),
            "all symbols must have non-empty identity fields",
        )

    def test_qualified_name_for_module_scope(self):
        result = _build("export function login() {}\n")

        login = _symbols_by_name(result, "login")[0]
        self.assertEqual(login.qualified_name, "login")

    def test_qualified_name_for_class_method(self):
        result = _build(
            "export default class AuthService {\n"
            "  validateUser() { return true; }\n"
            "}\n"
        )

        method = _symbols_by_name(result, "validateUser")[0]
        self.assertEqual(method.qualified_name, "AuthService.validateUser")

    def test_qualified_name_for_nested_function(self):
        result = _build(
            "function outer() {\n"
            "  function inner() { return 1; }\n"
            "  return inner;\n"
            "}\n"
        )

        inner = _symbols_by_name(result, "inner")[0]
        self.assertEqual(inner.qualified_name, "outer.inner")

    def test_stable_key_differs_by_kind(self):
        result = _build("function auth() {}\nconst auth = 1;\n")

        by_kind = {s.kind: s for s in result.symbols}
        function_key = by_kind[SymbolKind.FUNCTION].stable_key
        variable_key = by_kind[SymbolKind.VARIABLE].stable_key

        self.assertNotEqual(function_key, variable_key)

    def test_stable_key_differs_by_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "auth.ts").write_text("export function login() {}\n", encoding="utf-8")
            (root / "api.ts").write_text("export function login() {}\n", encoding="utf-8")

            result = build_graph(str(root))

            keys = {s.relative_path: s.stable_key for s in result.symbols}
            self.assertEqual(
                len({s.relative_path for s in result.symbols}),
                2,
            )
            self.assertNotEqual(keys["auth.ts"], keys["api.ts"])


class TestSignatureFingerprints(unittest.TestCase):
    def test_signature_excludes_function_name(self):
        renamed = _build("function login(name: string) { return 1; }\n")
        original = _build("function logout(name: string) { return 1; }\n")

        self.assertEqual(
            renamed.symbols[0].signature_hash,
            original.symbols[0].signature_hash,
        )

    def test_signature_excludes_function_body(self):
        body_a = _build("function login(name: string) { return 1; }\n")
        body_b = _build("function login(name: string) { return 2; return 3; }\n")

        self.assertEqual(
            body_a.symbols[0].signature_hash,
            body_b.symbols[0].signature_hash,
        )

    def test_signature_includes_parameter_types(self):
        string_param = _build("function login(name: string) {}\n")
        number_param = _build("function login(name: number) {}\n")

        self.assertNotEqual(
            string_param.symbols[0].signature_hash,
            number_param.symbols[0].signature_hash,
        )

    def test_signature_includes_return_type(self):
        with_return = _build("function login(): boolean { return true; }\n")
        without_return = _build("function login() { return true; }\n")

        self.assertNotEqual(
            with_return.symbols[0].signature_hash,
            without_return.symbols[0].signature_hash,
        )

    def test_signature_omits_untyped_parameters(self):
        untyped = _build("function login(name) { return 1; }\n")
        differently_named = _build("function login(user) { return 1; }\n")

        self.assertEqual(
            untyped.symbols[0].signature_hash,
            differently_named.symbols[0].signature_hash,
        )

    def test_class_signature_includes_extends(self):
        extends = _build("class AuthService extends BaseService {}\n")
        plain = _build("class AuthService {}\n")

        self.assertNotEqual(
            extends.symbols[0].signature_hash,
            plain.symbols[0].signature_hash,
        )

    def test_variable_signature_uses_type_annotation(self):
        typed = _build("const count: number = 5;\n")
        untyped = _build("const count = 5;\n")

        self.assertNotEqual(
            typed.symbols[0].signature_hash,
            untyped.symbols[0].signature_hash,
        )

    def test_content_hash_changes_on_any_edit(self):
        original = _build("function login() { return 1; }\n")
        edited = _build("function login() { return 2; }\n")

        self.assertNotEqual(
            original.symbols[0].content_hash,
            edited.symbols[0].content_hash,
        )


if __name__ == "__main__":
    unittest.main()
