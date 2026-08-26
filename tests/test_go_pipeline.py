import tempfile
import unittest
from pathlib import Path

from analysis.build_graph import build_graph
from analysis.semantic.normalize_path import resolve_module_path
from indexing.indexer import reindex_index
from retrieval.index_queries import build_hybrid_retriever

FIXTURE_REPO = str(
    Path(__file__).resolve().parent / "fixtures" / "go_repo"
)


class TestGoModuleResolution(unittest.TestCase):
    def test_import_path_maps_to_go_file(self):
        self.assertEqual(
            resolve_module_path(
                module_path="myrepo/auth",
                importing_directory="cmd/server",
                language="go",
            ),
            ["myrepo/auth.go"],
        )

    def test_external_modules_resolve_to_nothing(self):
        self.assertEqual(
            resolve_module_path(
                module_path="github.com/x/y",
                importing_directory="",
                language="go",
            ),
            ["github.com/x/y.go"],
        )
        # Candidate exists but no such document -> stays unresolved at the
        # resolver level; resolution against a real index is covered below.

    def test_unknown_language_resolves_nothing(self):
        self.assertEqual(
            resolve_module_path(
                module_path="x",
                importing_directory="",
                language="ruby",
            ),
            [],
        )


class TestGoExtraction(unittest.TestCase):
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

    def test_functions_methods_and_types_are_typed(self):
        self.assertTrue(self._symbols("ValidateToken", "function"))
        self.assertTrue(self._symbols("createSession", "function"))
        self.assertTrue(self._symbols("Login", "method"))
        self.assertTrue(self._symbols("Authenticator", "class"))
        self.assertTrue(self._symbols("Store", "class"))

    def test_imports_record_raw_paths(self):
        modules = {
            (i.module_path, i.local_name)
            for i in self.result.import_references
        }
        self.assertIn(("auth", "auth"), modules)
        self.assertIn(("fmt", "fmt"), modules)

    def test_intra_repo_import_resolves(self):
        resolved_targets = {
            ri.target_document.relative_path
            for ri in self.result.resolved_import_references
            if ri.target_document is not None
        }
        self.assertEqual(resolved_targets, {"auth.go"})

    def test_capitalized_names_are_exports(self):
        exported = {e.exported_name for e in self.result.exports}

        self.assertEqual(
            exported,
            {
                "ValidateToken",
                "NewAuthenticator",
                "Authenticator",
                "Login",
                "Store",
                "HandleRequest",
            },
        )
        self.assertNotIn("createSession", exported)

    def test_call_relationships_inside_file(self):
        self.assertTrue(self._relationship("Login", "calls", "ValidateToken"))
        self.assertTrue(self._relationship("Login", "calls", "createSession"))

    def test_chunks_exist_for_go_symbols(self):
        chunk_paths = {c.relative_path for c in self.result.chunks}
        self.assertEqual(chunk_paths, {"auth.go", "main.go"})


class TestGoRetrieval(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        for name in ("auth.go", "main.go"):
            content = (Path(FIXTURE_REPO) / name).read_text(encoding="utf-8")
            (root / name).write_text(content, encoding="utf-8")

        self.root = root
        self.db_path = str(root / ".ckg" / "index.sqlite")
        (root / ".ckg").mkdir(parents=True, exist_ok=True)
        reindex_index(self.db_path, str(root))

    def tearDown(self):
        self.tmp.cleanup()

    def test_definition_lookup_finds_go_symbols(self):
        retriever = build_hybrid_retriever(self.db_path)

        retrieval = retriever.retrieve("where is ValidateToken defined")

        self.assertTrue(
            any(
                c.symbol_name == "ValidateToken"
                and c.relative_path == "auth.go"
                for c in retrieval.candidates
            )
        )

    def test_semantic_search_surfaces_go_symbols(self):
        retriever = build_hybrid_retriever(self.db_path)

        # Lexical channel only (no embeddings here): pick terms that
        # co-occur inside the Login chunk.
        retrieval = retriever.retrieve("login user")

        paths = {c.relative_path for c in retrieval.candidates}
        self.assertIn("auth.go", paths)

    def test_incremental_edit_keeps_edges(self):
        (self.root / "auth.go").write_text(
            (
                "package auth\n"
                "\n"
                "func createSession(user string) string {\n"
                "\treturn user + \"!\"\n"
                "}\n"
                "\n"
                "func ValidateToken(token string) bool {\n"
                "\treturn len(token) > 8\n"
                "}\n"
                "\n"
                "type Authenticator struct {\n"
                "\tsecret string\n"
                "}\n"
                "\n"
                "func NewAuthenticator(secret string) *Authenticator {\n"
                "\treturn &Authenticator{secret: secret}\n"
                "}\n"
                "\n"
                "func (a *Authenticator) Login(user, token string) string {\n"
                "\tif ValidateToken(token) {\n"
                "\t\treturn createSession(user)\n"
                "\t}\n"
                "\treturn \"\"\n"
                "}\n"
                "\n"
                "type Store interface {\n"
                "\tSave() error\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        report = reindex_index(self.db_path, str(self.root))

        self.assertEqual(report.parsed_files, 1)

        retriever = build_hybrid_retriever(self.db_path)
        retrieval = retriever.retrieve("who calls createSession")
        names = {c.symbol_name for c in retrieval.candidates}
        self.assertIn("Login", names)


if __name__ == "__main__":
    unittest.main()
