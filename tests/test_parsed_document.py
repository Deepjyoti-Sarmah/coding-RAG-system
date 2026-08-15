import tempfile
import unittest
from pathlib import Path

from analysis.passes.parse_pass import run_parse_pass
from ingestion.loader import load_code_files
from models.build_result import BuildResult
from models.indexing_context import IndexingContext


def _build_for_dir(root: Path) -> tuple[BuildResult, IndexingContext]:
    build_result = BuildResult()
    context = IndexingContext()

    build_result.documents = load_code_files(str(root))
    context.document_index.add_many(build_result.documents)
    run_parse_pass(context=context, result=build_result)

    return build_result, context


class TestParsedDocument(unittest.TestCase):
    def test_one_ts_file_produces_one_parsed_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "auth.ts").write_text(
                "export function login() {}\n",
                encoding="utf-8",
            )

            build_result, context = _build_for_dir(root)

            self.assertEqual(len(build_result.documents), 1)
            self.assertEqual(len(context.parsed_documents), 1)

    def test_tree_root_is_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "auth.ts").write_text(
                "export function login() {}\n",
                encoding="utf-8",
            )

            _, context = _build_for_dir(root)

            parsed = context.parsed_documents[0]
            self.assertEqual(parsed.tree.root_node.type, "program")
            self.assertFalse(parsed.has_parse_errors)

    def test_file_hash_is_deterministic(self):
        content = "export function login() {}\n"

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "auth.ts").write_text(content, encoding="utf-8")

            _, first = _build_for_dir(root)
            _, second = _build_for_dir(root)

            hash_one = first.parsed_documents[0].file_hash
            hash_two = second.parsed_documents[0].file_hash

            self.assertEqual(hash_one, hash_two)
            self.assertTrue(hash_one)

    def test_file_hash_differs_for_different_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.ts").write_text("export const a = 1;\n", encoding="utf-8")
            (root / "b.ts").write_text("export const b = 2;\n", encoding="utf-8")

            _, context = _build_for_dir(root)

            hashes = {p.file_hash for p in context.parsed_documents}
            self.assertEqual(len(hashes), 2)


if __name__ == "__main__":
    unittest.main()