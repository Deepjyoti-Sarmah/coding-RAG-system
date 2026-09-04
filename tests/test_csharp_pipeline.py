import unittest
from pathlib import Path

from analysis.build_graph import build_graph

FIXTURE_REPO = str(Path(__file__).resolve().parent / "fixtures" / "csharp_repo")


class TestCSharpPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build_graph(FIXTURE_REPO)
        cls.symbols_by_id = {symbol.symbol_id: symbol for symbol in cls.result.symbols}

    def _symbols(self, name: str, kind: str | None = None):
        return [
            symbol
            for symbol in self.result.symbols
            if symbol.name == name
            and (kind is None or symbol.kind.value == kind)
        ]

    def _relationship(self, source: str, kind: str, target: str) -> bool:
        return any(
            relationship.kind.value == kind
            and self.symbols_by_id[relationship.source_symbol_id].name == source
            and self.symbols_by_id[relationship.target_symbol_id].name == target
            for relationship in self.result.graph.relationships()
        )

    def test_symbols_have_csharp_kinds(self):
        self.assertTrue(self._symbols("Authenticator", "class"))
        self.assertTrue(self._symbols("IStore", "interface"))
        self.assertTrue(self._symbols("CreateSession", "method"))
        self.assertTrue(self._symbols("Name", "variable"))

    def test_namespace_import_resolves_every_declaring_document(self):
        app_auth = [
            reference
            for reference in self.result.resolved_import_references
            if reference.import_reference.module_path == "App.Auth"
        ]
        targets = {reference.target_document.relative_path for reference in app_auth}
        self.assertEqual(targets, {"Auth.cs", "Session.cs", "PartialOne.cs", "PartialTwo.cs"})

    def test_inheritance_and_cross_file_call_are_resolved(self):
        self.assertTrue(self._relationship("Authenticator", "implements", "IStore"))
        self.assertTrue(self._relationship("Login", "calls", "ValidateToken"))
        self.assertTrue(self._relationship("Login", "calls", "CreateSession"))

    def test_partial_declarations_keep_distinct_stable_keys(self):
        declarations = self._symbols("SharedClient", "class")
        self.assertEqual(len(declarations), 2)
        self.assertEqual(len({symbol.stable_key for symbol in declarations}), 2)


if __name__ == "__main__":
    unittest.main()
