import unittest

from analysis.reference_extractor import extract_references
from analysis.symbol_extractor import extract_symbols
from models.entities.documents import Document
from parsing.registry import PARSER


def _make_document(content: str) -> Document:
    return Document(
        document_id="doc-1",
        absolute_path="/tmp/loc.ts",
        relative_path="loc.ts",
        file_name="loc.ts",
        extension=".ts",
        language="typescript",
        size_bytes=len(content),
        line_count=len(content.splitlines()),
        content=content,
    )


class TestSymbolLocationAccess(unittest.TestCase):
    def test_symbol_locations_match_source(self):
        content = "const x = 1;\nfunction foo() {}\n"
        doc = _make_document(content)
        tree = PARSER["typescript"].parse(doc)

        extracted = extract_symbols(tree=tree, document=doc)
        by_name = {e.symbol.name: e.symbol for e in extracted}

        self.assertIn("x", by_name)
        self.assertIn("foo", by_name)

        x = by_name["x"]
        self.assertEqual(x.location.start_line, 1)
        self.assertEqual(x.location.end_line, 1)
        # variable_declarator node is "x = 1"
        self.assertEqual(x.location.start_byte, len("const "))
        self.assertEqual(x.location.end_byte, len("const x = 1"))

        foo = by_name["foo"]
        self.assertEqual(foo.location.start_line, 2)
        self.assertEqual(foo.location.end_line, 2)
        # function_declaration starts at the `function` keyword
        self.assertEqual(foo.location.start_byte, len("const x = 1;\n"))
        self.assertEqual(
            foo.location.end_byte,
            len("const x = 1;\nfunction foo() {}"),
        )


class TestReferenceLocationAccess(unittest.TestCase):
    def test_reference_location_matches_source(self):
        content = "function foo() {\n  bar();\n}\n"
        doc = _make_document(content)
        tree = PARSER["typescript"].parse(doc)

        extracted = extract_symbols(tree=tree, document=doc)
        foo = next(e for e in extracted if e.symbol.name == "foo")

        references = extract_references(
            owner_symbol=foo.symbol,
            owner_node=foo.node,
        )

        self.assertEqual(len(references), 1)
        bar = references[0]
        self.assertEqual(bar.name, "bar")
        self.assertEqual(bar.location.start_line, 2)
        self.assertEqual(bar.location.end_line, 2)
        self.assertEqual(bar.location.start_byte, len("function foo() {\n  "))
        self.assertEqual(bar.location.end_byte, len("function foo() {\n  bar"))


if __name__ == "__main__":
    unittest.main()