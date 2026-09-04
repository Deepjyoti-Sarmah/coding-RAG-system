import unittest
from unittest import mock

from analysis.build_result import BuildResult
from analysis.indexing_context import IndexingContext
from analysis.passes.parse_pass import run_parse_pass
from models.entities.documents import Document


def _make_document(
    content: str,
    *,
    language: str,
    relative_path: str = "file.ts",
) -> Document:
    return Document(
        document_id="doc-1",
        absolute_path=f"/tmp/{relative_path}",
        relative_path=relative_path,
        file_name=relative_path,
        extension=".ts",
        language=language,
        size_bytes=len(content),
        line_count=len(content.splitlines()),
        content=content,
    )


class TestParsePass(unittest.TestCase):
    def test_supported_language_is_parsed(self):
        document = _make_document("export function login() {}\n", language="typescript")

        context = IndexingContext()
        result = BuildResult()
        context.document_index.add(document)

        run_parse_pass(context=context, result=result)

        self.assertEqual(len(context.parsed_documents), 1)
        self.assertFalse(context.parsed_documents[0].has_parse_errors)

    def test_unsupported_language_is_skipped_cleanly(self):
        document = _make_document("x = 1\n", language="ruby")

        context = IndexingContext()
        result = BuildResult()
        context.document_index.add(document)

        run_parse_pass(context=context, result=result)

        self.assertEqual(len(context.parsed_documents), 0)

    def test_parse_errors_are_represented_without_crashing(self):
        document = _make_document("function foo( {\n", language="typescript")

        context = IndexingContext()
        result = BuildResult()
        context.document_index.add(document)

        run_parse_pass(context=context, result=result)

        self.assertEqual(len(context.parsed_documents), 1)
        self.assertTrue(context.parsed_documents[0].has_parse_errors)

    def test_parse_once_per_document_across_extraction_passes(self):
        # P5-5: the parse pass runs once per document and every downstream
        # pass reuses parsed.tree — no pass may re-parse.
        from analysis.pipeline import run_extraction_passes
        from parsing.tree_sitter_parser import TreeSitterParser

        context = IndexingContext()
        result = BuildResult()
        for i in ("a", "b"):
            doc = _make_document(
                f"export function login_{i}() {{ logout_{i}(); }}\n"
                f"function logout_{i}() {{}}\n",
                language="typescript",
                relative_path=f"{i}.ts",
            )
            doc.document_id = f"doc-{i}"
            context.document_index.add(doc)

        real_parse = TreeSitterParser.parse
        calls = []

        def counting_parse(self, document):
            calls.append(document.relative_path)
            return real_parse(self, document)

        with mock.patch.object(TreeSitterParser, "parse", counting_parse):
            run_extraction_passes(context=context, result=result)

        self.assertEqual(len(context.parsed_documents), 2)
        self.assertEqual(sorted(calls), ["a.ts", "b.ts"])


if __name__ == "__main__":
    unittest.main()