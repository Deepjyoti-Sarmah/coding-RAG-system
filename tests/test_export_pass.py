import unittest

from analysis.passes.export_pass import run_export_pass
from analysis.passes.parse_pass import run_parse_pass
from models.build_result import BuildResult
from models.entities.documents import Document
from models.indexing_context import IndexingContext


def _make_document(content: str) -> Document:
    return Document(
        document_id="doc-1",
        absolute_path="/tmp/exports.ts",
        relative_path="exports.ts",
        file_name="exports.ts",
        extension=".ts",
        language="typescript",
        size_bytes=len(content),
        line_count=len(content.splitlines()),
        content=content,
    )


def _extract_exports(content: str):
    document = _make_document(content)

    context = IndexingContext()
    result = BuildResult()

    context.document_index.add(document)
    run_parse_pass(context=context, result=result)
    run_export_pass(context=context, result=result)

    return result.exports


def _tuples(exports):
    return sorted((e.exported_name, e.symbol_name) for e in exports)


class TestExportPass(unittest.TestCase):
    def test_export_function(self):
        exports = _extract_exports("export function login() {}\n")
        self.assertEqual(
            _tuples(exports),
            [("login", "login")],
        )

    def test_export_const(self):
        exports = _extract_exports("export const x = 1;\n")
        self.assertEqual(
            _tuples(exports),
            [("x", "x")],
        )

    def test_export_arrow_function_const(self):
        exports = _extract_exports("export const login = () => {};\n")
        self.assertEqual(
            _tuples(exports),
            [("login", "login")],
        )

    def test_export_multiple_declarators(self):
        exports = _extract_exports("export const a = 1, b = 2;\n")
        self.assertEqual(
            _tuples(exports),
            [("a", "a"), ("b", "b")],
        )

    def test_export_default_anonymous_function(self):
        exports = _extract_exports("export default function() {}\n")
        self.assertEqual(
            _tuples(exports),
            [("default", None)],
        )

    def test_export_default_named_function(self):
        exports = _extract_exports("export default function login() {}\n")
        self.assertEqual(
            _tuples(exports),
            [("default", "login")],
        )

    def test_export_default_class(self):
        exports = _extract_exports("export default class AuthService {}\n")
        self.assertEqual(
            _tuples(exports),
            [("default", "AuthService")],
        )

    def test_export_default_identifier(self):
        exports = _extract_exports("const login = 1;\nexport default login;\n")
        self.assertEqual(
            _tuples(exports),
            [("default", "login")],
        )

    def test_export_named_specifier(self):
        exports = _extract_exports("export { login };\n")
        self.assertEqual(
            _tuples(exports),
            [("login", "login")],
        )

    def test_export_aliased_specifier(self):
        exports = _extract_exports("export { login as authLogin };\n")
        self.assertEqual(
            _tuples(exports),
            [("authLogin", "login")],
        )

    def test_export_specifier_as_default(self):
        exports = _extract_exports("const login = 1;\nexport { login as default };\n")
        self.assertEqual(
            _tuples(exports),
            [("default", "login")],
        )

    def test_reexport_from_is_deferred(self):
        exports = _extract_exports('export { login } from "./auth";\n')
        self.assertEqual(exports, [])

    def test_star_reexport_is_deferred(self):
        exports = _extract_exports('export * from "./auth";\n')
        self.assertEqual(exports, [])

    def test_non_exported_statement_produces_no_export(self):
        exports = _extract_exports("const x = 1;\nfunction f() {}\n")
        self.assertEqual(exports, [])


if __name__ == "__main__":
    unittest.main()
