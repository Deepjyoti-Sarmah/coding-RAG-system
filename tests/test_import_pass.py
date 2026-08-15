import unittest

from analysis.passes.import_pass import run_import_pass
from analysis.passes.parse_pass import run_parse_pass
from models.build_result import BuildResult
from models.entities.documents import Document
from models.indexing_context import IndexingContext


def _make_document(content: str) -> Document:
    return Document(
        document_id="doc-1",
        absolute_path="/tmp/imports.ts",
        relative_path="imports.ts",
        file_name="imports.ts",
        extension=".ts",
        language="typescript",
        size_bytes=len(content),
        line_count=len(content.splitlines()),
        content=content,
    )


def _extract_imports(content: str):
    document = _make_document(content)

    context = IndexingContext()
    result = BuildResult()

    context.document_index.add(document)
    run_parse_pass(context=context, result=result)
    run_import_pass(context=context, result=result)

    return result.import_references


def _tuples(imports):
    return sorted(
        (i.module_path, i.imported_name, i.local_name) for i in imports
    )


class TestImportPass(unittest.TestCase):
    def test_named_import(self):
        imports = _extract_imports('import { login } from "./auth";\n')
        self.assertEqual(
            _tuples(imports),
            [("./auth", "login", "login")],
        )

    def test_multiple_named_imports(self):
        imports = _extract_imports(
            'import { login, logout } from "./auth";\n'
        )
        self.assertEqual(
            _tuples(imports),
            [
                ("./auth", "login", "login"),
                ("./auth", "logout", "logout"),
            ],
        )

    def test_aliased_named_import(self):
        imports = _extract_imports(
            'import { login as authLogin } from "./auth";\n'
        )
        self.assertEqual(
            _tuples(imports),
            [("./auth", "login", "authLogin")],
        )

    def test_default_import(self):
        imports = _extract_imports('import AuthService from "./auth";\n')
        self.assertEqual(
            _tuples(imports),
            [("./auth", "default", "AuthService")],
        )

    def test_namespace_import(self):
        imports = _extract_imports('import * as auth from "./auth";\n')
        self.assertEqual(
            _tuples(imports),
            [("./auth", "*", "auth")],
        )

    def test_mixed_import(self):
        imports = _extract_imports(
            'import Auth, { login, logout as signOut } from "./auth";\n'
        )
        self.assertEqual(
            _tuples(imports),
            [
                ("./auth", "default", "Auth"),
                ("./auth", "login", "login"),
                ("./auth", "logout", "signOut"),
            ],
        )


if __name__ == "__main__":
    unittest.main()