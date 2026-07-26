import unittest
from uuid import uuid4

from parsing.registry import PARSER
from analysis.symbol_extractor import extract_symbols
from models.entities.documents import Document
from models.entities.symbol_kind import SymbolKind


def _make_document(content: str) -> Document:
    return Document(
        document_id=str(uuid4()),
        absolute_path="/tmp/test.ts",
        relative_path="test.ts",
        file_name="test.ts",
        extension=".ts",
        language="typescript",
        size_bytes=len(content),
        line_count=len(content.splitlines()),
        content=content,
    )


def _extract(content: str):
    doc = _make_document(content)
    parser = PARSER["typescript"]
    tree = parser.parse(doc)
    return extract_symbols(tree=tree, document=doc)


def _names_and_kinds(extracted):
    return sorted((e.symbol.name, e.symbol.kind) for e in extracted)


class TestVariableDeclarator(unittest.TestCase):
    def test_const_x_equals_1(self):
        extracted = _extract("const x = 1;")
        self.assertEqual(
            _names_and_kinds(extracted), [("x", SymbolKind.VARIABLE)]
        )

    def test_const_fn_arrow(self):
        extracted = _extract("const fn = () => {};")
        self.assertEqual(
            _names_and_kinds(extracted), [("fn", SymbolKind.FUNCTION)]
        )

    def test_export_const(self):
        extracted = _extract("export const x = 1;")
        self.assertEqual(
            _names_and_kinds(extracted), [("x", SymbolKind.VARIABLE)]
        )

    def test_destructuring_skipped(self):
        extracted = _extract("const { a } = obj;")
        self.assertEqual(_names_and_kinds(extracted), [])

    def test_nested_inside_function_not_extracted(self):
        extracted = _extract("function foo() {\n  const x = 1;\n}")
        self.assertEqual(
            _names_and_kinds(extracted), [("foo", SymbolKind.FUNCTION)]
        )

    def test_multiple_declarators(self):
        extracted = _extract("const a = 1, b = 2;")
        self.assertEqual(
            _names_and_kinds(extracted),
            [("a", SymbolKind.VARIABLE), ("b", SymbolKind.VARIABLE)],
        )

    def test_export_arrow(self):
        extracted = _extract("export const fn = () => {};")
        self.assertEqual(
            _names_and_kinds(extracted), [("fn", SymbolKind.FUNCTION)]
        )

    def test_let_and_var(self):
        extracted = _extract("let x = 1;\nvar y = 2;")
        self.assertEqual(
            _names_and_kinds(extracted),
            [("x", SymbolKind.VARIABLE), ("y", SymbolKind.VARIABLE)],
        )


if __name__ == "__main__":
    unittest.main()
