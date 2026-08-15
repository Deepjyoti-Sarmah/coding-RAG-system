import unittest

from analysis.semantic.import_resolver import resolve_import
from analysis.semantic.normalize_path import resolve_module_path
from indexing.document_index import DocumentIndex
from models.common.source_location import SourceLocation
from models.entities.documents import Document
from models.entities.import_references import ImportReference


def _add_document(index: DocumentIndex, relative_path: str):
    index.add(
        Document(
            document_id=relative_path,
            absolute_path=f"/tmp/{relative_path}",
            relative_path=relative_path,
            file_name=relative_path.split("/")[-1],
            extension=".ts" if relative_path.endswith(".ts") else ".tsx",
            language="typescript",
            size_bytes=0,
            line_count=1,
            content="",
        )
    )


def _import_reference(module_path: str) -> ImportReference:
    return ImportReference(
        document_id="src/api.ts",
        module_path=module_path,
        imported_name="x",
        local_name="x",
        location=SourceLocation(
            start_line=1,
            end_line=1,
            start_byte=0,
            end_byte=1,
        ),
    )


class TestResolveModulePath(unittest.TestCase):
    def test_relative_module_only(self):
        self.assertEqual(
            resolve_module_path(
                module_path="lodash",
                importing_directory="src",
            ),
            [],
        )

    def test_candidates_order_ts_first(self):
        self.assertEqual(
            resolve_module_path(
                module_path="./util",
                importing_directory="src",
            ),
            [
                "src/util.ts",
                "src/util.tsx",
                "src/util.js",
                "src/util.jsx",
            ],
        )

    def test_extension_preserved(self):
        self.assertEqual(
            resolve_module_path(
                module_path="./util.tsx",
                importing_directory="src",
            ),
            ["src/util.tsx"],
        )

    def test_parent_directory(self):
        self.assertEqual(
            resolve_module_path(
                module_path="../auth",
                importing_directory="src",
            ),
            [
                "auth.ts",
                "auth.tsx",
                "auth.js",
                "auth.jsx",
            ],
        )


class TestResolveImport(unittest.TestCase):
    def setUp(self):
        self.index = DocumentIndex()
        for path in (
            "auth.ts",
            "src/api.ts",
            "src/nested/util.ts",
            "src/directory/index.ts",
            "src/file.jsx",
        ):
            _add_document(self.index, path)
        self.importing = self.index.lookup_by_relative_path("src/api.ts")

    def _resolve(self, module_path: str):
        return resolve_import(
            import_reference=_import_reference(module_path),
            importing_document=self.importing,
            document_index=self.index,
        )

    def test_sibling_file_without_extension(self):
        target = self._resolve("./nested/util")
        self.assertEqual(target.relative_path, "src/nested/util.ts")

    def test_sibling_file_with_extension(self):
        target = self._resolve("./nested/util.ts")
        self.assertEqual(target.relative_path, "src/nested/util.ts")

    def test_parent_directory(self):
        target = self._resolve("../auth")
        self.assertEqual(target.relative_path, "auth.ts")

    def test_jsx_extension(self):
        target = self._resolve("./file.jsx")
        self.assertEqual(target.relative_path, "src/file.jsx")

    def test_directory_index(self):
        target = self._resolve("./directory/index.ts")
        self.assertEqual(target.relative_path, "src/directory/index.ts")

    def test_missing_module_returns_none(self):
        self.assertIsNone(self._resolve("./missing"))

    def test_bare_specifier_returns_none(self):
        self.assertIsNone(self._resolve("lodash"))


if __name__ == "__main__":
    unittest.main()