import unittest
from pathlib import Path

from analysis.build_graph import build_graph


FIXTURE_REPO = str(Path(__file__).resolve().parent / "fixtures" / "cpp_repo")


class TestCppPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build_graph(FIXTURE_REPO)
        cls.by_id = {symbol.symbol_id: symbol for symbol in cls.result.symbols}

    def _symbols(self, name, kind=None):
        return [s for s in self.result.symbols if s.name == name and (kind is None or s.kind.value == kind)]

    def _relationship(self, source, kind, target):
        return any(
            edge.kind.value == kind
            and self.by_id[edge.source_symbol_id].name == source
            and self.by_id[edge.target_symbol_id].name == target
            for edge in self.result.graph.relationships()
        )

    def test_namespaces_classes_and_methods_are_extracted(self):
        self.assertTrue(self._symbols("app", "module"))
        self.assertTrue(self._symbols("Base", "class"))
        self.assertTrue(self._symbols("Auth", "class"))
        self.assertTrue(self._symbols("login", "method"))

    def test_overloads_have_distinct_stable_keys(self):
        overloads = self._symbols("add", "function")
        self.assertEqual(len(overloads), 4)
        self.assertEqual(len({s.stable_key for s in overloads}), 4)

    def test_include_and_declaration_definition_links(self):
        includes = [i for i in self.result.resolved_import_references if i.import_reference.module_path == "auth.hpp"]
        self.assertEqual({i.target_document.relative_path for i in includes}, {"auth.hpp"})
        self.assertTrue(self._relationship("add", "definition_of", "add"))

    def test_inheritance_and_calls_are_extracted(self):
        self.assertTrue(self._relationship("Auth", "extends", "Base"))
        self.assertTrue(self._relationship("Auth::login", "calls", "add_int"))


if __name__ == "__main__":
    unittest.main()
