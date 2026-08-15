import unittest

from analysis.passes.parse_pass import run_parse_pass
from models.build_result import BuildResult
from models.entities.documents import Document
from models.indexing_context import IndexingContext


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
        document = _make_document("x = 1\n", language="python")

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


if __name__ == "__main__":
    unittest.main()