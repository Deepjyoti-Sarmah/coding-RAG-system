import tempfile
import unittest
from pathlib import Path

from analysis.build_graph import build_graph
from graph.code_graph import CodeGraph
from models.common.source_location import SourceLocation
from models.entities.symbols import Symbol
from models.entities.symbol_kind import SymbolKind
from models.relationships.relationships import Relationship
from models.relationships.relationship_kind import RelationshipKind


def _symbol(
    *,
    symbol_id: str,
    name: str,
    parent_symbol_id: str | None = None,
) -> Symbol:
    return Symbol(
        symbol_id=symbol_id,
        document_id="doc-1",
        name=name,
        kind=SymbolKind.FUNCTION,
        relative_path="f.ts",
        location=SourceLocation(
            start_line=1,
            end_line=1,
            start_byte=0,
            end_byte=1,
        ),
        content="",
        parent_symbol_id=parent_symbol_id,
    )


class TestGraphAPI(unittest.TestCase):
    def setUp(self):
        self.graph = CodeGraph()
        self.outer = _symbol(symbol_id="outer", name="outer")
        self.inner = _symbol(
            symbol_id="inner",
            name="inner",
            parent_symbol_id=self.outer.symbol_id,
        )
        self.graph.add_symbols([self.outer, self.inner])

    def test_symbols_returns_all_symbols(self):
        self.assertEqual(
            {s.symbol_id for s in self.graph.symbols()},
            {"outer", "inner"},
        )

    def test_children_of_returns_direct_children(self):
        self.assertEqual(
            [s.symbol_id for s in self.graph.children_of(self.outer.symbol_id)],
            ["inner"],
        )

    def test_children_of_unknown_id_is_empty(self):
        self.assertEqual(self.graph.children_of("missing"), [])

    def test_parents_of_returns_immediate_parent(self):
        self.assertEqual(
            [s.symbol_id for s in self.graph.parents_of(self.inner.symbol_id)],
            ["outer"],
        )

    def test_parents_of_module_scope_is_empty(self):
        self.assertEqual(self.graph.parents_of(self.outer.symbol_id), [])

    def test_parents_of_unknown_id_is_empty(self):
        self.assertEqual(self.graph.parents_of("missing"), [])

    def test_relationships_returns_immutable_copy(self):
        returned = self.graph.relationships()

        self.assertIsInstance(returned, tuple)
        self.assertEqual(returned, ())

    def test_relationships_reflects_added_relationships(self):
        self.graph.add_relationships(
            [
                Relationship(
                    source_symbol_id="outer",
                    target_symbol_id="inner",
                    kind=RelationshipKind.CALLS,
                )
            ]
        )

        self.assertEqual(len(self.graph.relationships()), 1)


class TestRelationshipDeduplication(unittest.TestCase):
    def test_repeated_calls_produce_one_edge(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.ts").write_text(
                "function login() {}\n"
                "function outer() {\n"
                "  login();\n"
                "  login();\n"
                "}\n",
                encoding="utf-8",
            )

            result = build_graph(str(root))

            outer = next(s for s in result.symbols if s.name == "outer")
            login = next(s for s in result.symbols if s.name == "login")

            calls = [
                r
                for r in result.graph.relationships()
                if r.kind == RelationshipKind.CALLS
                and r.source_symbol_id == outer.symbol_id
            ]

            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0].target_symbol_id, login.symbol_id)

    def test_callers_of_returns_unique_callers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.ts").write_text(
                "function login() {}\n"
                "function outer() {\n"
                "  login();\n"
                "  login();\n"
                "}\n",
                encoding="utf-8",
            )

            result = build_graph(str(root))

            login = next(s for s in result.symbols if s.name == "login")
            outer = next(s for s in result.symbols if s.name == "outer")

            callers = result.graph.callers_of(login.symbol_id)

            self.assertEqual([s.symbol_id for s in callers], [outer.symbol_id])

    def test_add_relationships_deduplicates_in_graph(self):
        graph = CodeGraph()
        graph.add_symbols(
            [_symbol(symbol_id="outer", name="outer")]
        )
        graph.add_relationships(
            [
                Relationship(
                    source_symbol_id="outer",
                    target_symbol_id="login",
                    kind=RelationshipKind.CALLS,
                ),
                Relationship(
                    source_symbol_id="outer",
                    target_symbol_id="login",
                    kind=RelationshipKind.CALLS,
                ),
            ]
        )

        self.assertEqual(len(graph.relationships()), 1)


if __name__ == "__main__":
    unittest.main()
