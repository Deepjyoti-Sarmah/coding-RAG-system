import tempfile
import unittest
from pathlib import Path

from analysis.build_graph import build_graph
from analysis.semantic.normalize_path import resolve_module_path
from indexing.indexer import reindex_index
from retrieval.index_queries import build_hybrid_retriever
from storage.index_store import load_index

FIXTURE_REPO = str(
    Path(__file__).resolve().parent / "fixtures" / "python_repo"
)


class TestPythonModuleResolution(unittest.TestCase):
    def test_absolute_import_maps_dots_to_slashes(self):
        self.assertEqual(
            resolve_module_path(
                module_path="utils.helpers",
                importing_directory="",
                language="python",
            ),
            ["utils/helpers.py"],
        )

    def test_relative_import_climbs_directories(self):
        self.assertEqual(
            resolve_module_path(
                module_path=".auth",
                importing_directory="pkg/sub",
                language="python",
            ),
            ["pkg/sub/auth.py"],
        )

    def test_parent_relative_import(self):
        self.assertEqual(
            resolve_module_path(
                module_path="..auth",
                importing_directory="pkg/sub",
                language="python",
            ),
            ["pkg/auth.py"],
        )

    def test_unknown_language_resolves_nothing(self):
        self.assertEqual(
            resolve_module_path(
                module_path="./x",
                importing_directory="src",
                language="ruby",
            ),
            [],
        )


class TestPythonExtraction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build_graph(FIXTURE_REPO)

    def _symbols(self, name: str, kind: str | None = None):
        return [
            symbol
            for symbol in self.result.symbols
            if symbol.name == name and (kind is None or symbol.kind.value == kind)
        ]

    def _relationship(self, source: str, kind: str, target: str) -> bool:
        symbols_by_id = {s.symbol_id: s for s in self.result.symbols}
        return any(
            r.kind.value == kind
            and symbols_by_id[r.source_symbol_id].name == source
            and symbols_by_id[r.target_symbol_id].name == target
            for r in self.result.graph.relationships()
        )

    def test_functions_classes_and_methods_are_typed(self):
        self.assertTrue(self._symbols("create_session", "function"))
        self.assertTrue(self._symbols("Authenticator", "class"))
        self.assertTrue(self._symbols("login", "method"))

    def test_imports_are_extracted_with_python_specifiers(self):
        modules = {
            (i.module_path, i.imported_name)
            for i in self.result.import_references
        }
        self.assertIn(("auth", "Authenticator"), modules)
        self.assertIn((".auth", "Authenticator"), modules)

    def test_top_level_definitions_are_exports(self):
        exported = {
            e.exported_name: e.document_id[-8:]
            for e in self.result.exports
        }

        self.assertIn("create_session", exported)
        self.assertIn("handle_request", exported)
        # Methods are not exports.
        self.assertNotIn("login", exported)

    def test_call_relationships_cross_files(self):
        # Direct constructor/function calls resolve cross-file; method
        # calls on local instances (`authenticator.login(...)`) need
        # instance tracking and stay unresolved in v1.
        self.assertTrue(
            self._relationship("handle_request", "calls", "Authenticator")
        )
        self.assertTrue(
            self._relationship("handle_request", "calls", "create_session")
        )

    def test_inheritance_through_superclasses_field(self):
        self.assertTrue(
            self._relationship("AdminAuthenticator", "extends", "Authenticator")
        )

    def test_chunks_exist_for_python_symbols(self):
        chunk_paths = {c.relative_path for c in self.result.chunks}

        self.assertEqual(chunk_paths, {"api.py", "admin.py", "auth.py"})


class TestPythonRetrieval(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        for name in ("auth.py", "api.py", "admin.py"):
            content = (Path(FIXTURE_REPO) / name).read_text(encoding="utf-8")
            (root / name).write_text(content, encoding="utf-8")

        self.root = root
        self.db_path = str(root / ".ckg" / "index.sqlite")
        (root / ".ckg").mkdir(parents=True, exist_ok=True)
        reindex_index(self.db_path, str(root))

    def tearDown(self):
        self.tmp.cleanup()

    def test_definition_lookup_routes_to_graph_answer(self):
        retriever = build_hybrid_retriever(self.db_path)

        retrieval = retriever.retrieve("where is Authenticator defined")

        self.assertEqual(retrieval.strategy, "exact_symbol")
        self.assertTrue(
            any(
                c.symbol_name == "Authenticator" and c.relative_path == "auth.py"
                for c in retrieval.candidates
            )
        )

    def test_semantic_search_finds_python_symbols(self):
        retriever = build_hybrid_retriever(self.db_path)

        retrieval = retriever.retrieve("token validation")

        paths = {c.relative_path for c in retrieval.candidates}
        self.assertIn("auth.py", paths)

    def test_incremental_edit_keeps_graph_consistent(self):
        (self.root / "auth.py").write_text(
            (
                "def create_session(user):\n"
                "    return {'user': user, 'created': True}\n"
                "\n"
                "\n"
                "def validate_token(token):\n"
                "    return len(token) > 8\n"
                "\n"
                "\n"
                "class Authenticator:\n"
                "    def __init__(self, secret):\n"
                "        self.secret = secret\n"
                "\n"
                "    def login(self, user, token):\n"
                "        if validate_token(token):\n"
                "            return create_session(user)\n"
                "        return None\n"
            ),
            encoding="utf-8",
        )
        reindex_index(self.db_path, str(self.root))

        result = load_index(self.db_path)
        create_session = next(
            s
            for s in result.symbols
            if s.name == "create_session" and s.kind.value == "function"
        )
        self.assertIn("'created': True", create_session.content)

        # The cross-file call and inheritance edges survived the
        # incremental rebuild.
        symbols_by_id = {s.symbol_id: s for s in result.symbols}
        kinds = {
            (symbols_by_id[r.source_symbol_id].name, r.kind.value,
             symbols_by_id[r.target_symbol_id].name)
            for r in result.graph.relationships()
        }

        self.assertIn(("handle_request", "calls", "Authenticator"), kinds)
        self.assertIn(("AdminAuthenticator", "extends", "Authenticator"), kinds)


if __name__ == "__main__":
    unittest.main()
