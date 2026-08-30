import unittest
from pathlib import Path

from analysis.build_graph import build_graph


FIXTURE_REPO = str(Path(__file__).resolve().parent / "fixtures" / "c_repo")


class TestCPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build_graph(FIXTURE_REPO)
        cls.by_id = {symbol.symbol_id: symbol for symbol in cls.result.symbols}

    def _relationship(self, source, kind, target):
        return any(
            edge.kind.value == kind
            and self.by_id[edge.source_symbol_id].name == source
            and self.by_id[edge.target_symbol_id].name == target
            for edge in self.result.graph.relationships()
        )

    def test_functions_and_header_declaration_are_symbols(self):
        authenticate = [s for s in self.result.symbols if s.name == "authenticate"]
        self.assertEqual(len(authenticate), 2)
        self.assertTrue(any(s.relative_path == "auth.h" for s in authenticate))
        self.assertTrue(any(s.relative_path == "auth.c" for s in authenticate))

    def test_quoted_includes_resolve_locally(self):
        imports = [i for i in self.result.resolved_import_references if i.import_reference.module_path == "auth.h"]
        self.assertEqual({i.target_document.relative_path for i in imports}, {"auth.h"})

    def test_calls_and_definitions_are_connected(self):
        self.assertTrue(self._relationship("authenticate", "calls", "validate"))
        self.assertTrue(self._relationship("authenticate", "definition_of", "authenticate"))


if __name__ == "__main__":
    unittest.main()
