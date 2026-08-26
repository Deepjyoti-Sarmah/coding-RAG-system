"""Document-scoped import/export adjacency on the graph.

These edges replaced the repository-wide scans that `neighborhood` and
`hybrid_retriever` used to run once per seed symbol, so the assertions here
pin the traversal results those scans produced.
"""

import tempfile
import unittest
from pathlib import Path

from analysis.build_graph import build_graph
from storage.index_store import load_index, persist_index

FIXTURES = Path(__file__).resolve().parent / "fixtures"

TS_FIXTURE = {
    "auth.ts": (
        "export function createAuth() { return 1; }\n"
        "export function login(name: string) { return createAuth(); }\n"
    ),
    "api.ts": (
        'import { login } from "./auth";\n'
        'export function run() { login("admin"); }\n'
    ),
}


def _document_id(result, relative_path: str) -> str:
    return next(
        d.document_id for d in result.documents if d.relative_path == relative_path
    )


def _names(symbols) -> set[str]:
    return {symbol.name for symbol in symbols}


def _build_typescript():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for name, content in TS_FIXTURE.items():
            (root / name).write_text(content, encoding="utf-8")
        return build_graph(str(root))


class TestTypeScriptDocumentEdges(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = _build_typescript()

    def test_imports_of_document_lists_resolved_targets(self):
        api = _document_id(self.result, "api.ts")

        self.assertEqual(
            _names(self.result.graph.imports_of_document(api)), {"login"}
        )

    def test_exports_of_document_lists_local_exported_symbols(self):
        auth = _document_id(self.result, "auth.ts")

        self.assertEqual(
            _names(self.result.graph.exports_of_document(auth)),
            {"createAuth", "login"},
        )

    def test_importers_of_document_is_the_reverse_edge(self):
        auth = _document_id(self.result, "auth.ts")
        api = _document_id(self.result, "api.ts")

        self.assertEqual(self.result.graph.importers_of_document(auth), [api])
        self.assertEqual(self.result.graph.importers_of_document(api), [])

    def test_importers_of_symbol_is_precise(self):
        api = _document_id(self.result, "api.ts")
        login = next(s for s in self.result.symbols if s.name == "login")
        create_auth = next(s for s in self.result.symbols if s.name == "createAuth")

        self.assertEqual(self.result.graph.importers_of_symbol(login.symbol_id), [api])
        self.assertEqual(
            self.result.graph.importers_of_symbol(create_auth.symbol_id),
            [],
            "createAuth is exported but never imported",
        )

    def test_documents_are_findable_by_path_and_bare_name(self):
        auth = _document_id(self.result, "auth.ts")

        self.assertEqual(self.result.graph.document_ids_for_path("auth.ts"), [auth])
        self.assertEqual(self.result.graph.document_ids_for_path("nope.ts"), [])

    def test_edges_survive_a_round_trip_through_sqlite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, content in TS_FIXTURE.items():
                (root / name).write_text(content, encoding="utf-8")
            result = build_graph(str(root))

            db_path = str(root / "index.sqlite")
            persist_index(db_path, result)
            loaded = load_index(db_path)

        api = _document_id(loaded, "api.ts")
        auth = _document_id(loaded, "auth.ts")

        self.assertEqual(_names(loaded.graph.imports_of_document(api)), {"login"})
        self.assertEqual(loaded.graph.importers_of_document(auth), [api])


class TestPythonDocumentEdges(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build_graph(str(FIXTURES / "python_repo"))

    def test_importers_and_imports_resolve_across_modules(self):
        auth = _document_id(self.result, "auth.py")
        api = _document_id(self.result, "api.py")

        self.assertIn(api, self.result.graph.importers_of_document(auth))
        self.assertIn(
            "create_session", _names(self.result.graph.imports_of_document(api))
        )


class TestGoDocumentEdges(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build_graph(str(FIXTURES / "go_repo"))

    def test_importers_follow_go_package_paths(self):
        auth = _document_id(self.result, "auth.go")
        main = _document_id(self.result, "main.go")

        self.assertIn(main, self.result.graph.importers_of_document(auth))

    def test_unexported_go_symbols_are_not_exports(self):
        auth = _document_id(self.result, "auth.go")
        exported = _names(self.result.graph.exports_of_document(auth))

        self.assertIn("ValidateToken", exported)
        self.assertNotIn("createSession", exported)


if __name__ == "__main__":
    unittest.main()
