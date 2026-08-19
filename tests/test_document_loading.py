import tempfile
import unittest
from pathlib import Path

from ingestion.loader import load_code_files


class TestSingleDocumentLoad(unittest.TestCase):
    def test_single_file_loads_one_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            file_path = Path(tmp) / "auth.ts"
            file_path.write_text("export function login() {}\n", encoding="utf-8")

            documents = load_code_files(str(file_path))

            self.assertEqual(len(documents), 1)

    def test_single_document_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            file_path = Path(tmp) / "auth.ts"
            file_path.write_text("export function login() {}\n", encoding="utf-8")

            documents = load_code_files(str(file_path))
            document = documents[0]

            self.assertEqual(document.relative_path, "auth.ts")
            self.assertEqual(document.extension, ".ts")
            self.assertEqual(document.language, "typescript")
            self.assertEqual(document.content, "export function login() {}\n")


class TestDirectoryLoad(unittest.TestCase):
    def test_directory_loads_supported_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "auth.ts").write_text("export const a = 1;\n", encoding="utf-8")
            (root / "api.js").write_text("module.exports = {};\n", encoding="utf-8")

            documents = load_code_files(str(root))

            self.assertEqual(
                {d.relative_path for d in documents},
                {"auth.ts", "api.js"},
            )

    def test_skips_unsupported_extensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "auth.ts").write_text("export const a = 1;\n", encoding="utf-8")
            (root / "notes.md").write_text("# notes\n", encoding="utf-8")
            (root / "script.py").write_text("x = 1\n", encoding="utf-8")

            documents = load_code_files(str(root))

            self.assertEqual(
                {d.relative_path for d in documents},
                {"auth.ts"},
            )

    def test_skips_excluded_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "auth.ts").write_text("export const a = 1;\n", encoding="utf-8")
            excluded = root / "node_modules"
            excluded.mkdir()
            (excluded / "dep.ts").write_text(
                "export const dep = 1;\n",
                encoding="utf-8",
            )

            documents = load_code_files(str(root))

            self.assertEqual(
                {d.relative_path for d in documents},
                {"auth.ts"},
            )

    def test_honors_gitignore(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".gitignore").write_text("*.gen.ts\n", encoding="utf-8")
            (root / "auth.ts").write_text("export const a = 1;\n", encoding="utf-8")
            (root / "schema.gen.ts").write_text(
                "export const s = 1;\n", encoding="utf-8"
            )

            documents = load_code_files(str(root))

            self.assertEqual(
                {d.relative_path for d in documents},
                {"auth.ts"},
            )

    def test_honors_ckgignore(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".ckgignore").write_text("fixtures/\n", encoding="utf-8")
            (root / "auth.ts").write_text("export const a = 1;\n", encoding="utf-8")
            fixtures = root / "fixtures"
            fixtures.mkdir()
            (fixtures / "sample.ts").write_text(
                "export const s = 1;\n", encoding="utf-8"
            )

            documents = load_code_files(str(root))

            self.assertEqual(
                {d.relative_path for d in documents},
                {"auth.ts"},
            )


if __name__ == "__main__":
    unittest.main()