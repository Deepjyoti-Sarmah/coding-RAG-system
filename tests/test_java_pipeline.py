import tempfile
import unittest
from pathlib import Path

from analysis.build_graph import build_graph
from analysis.semantic.normalize_path import resolve_module_path
from indexing.indexer import reindex_index
from retrieval.index_queries import build_hybrid_retriever

FIXTURE_REPO = str(
    Path(__file__).resolve().parent / "fixtures" / "java_repo"
)


class TestJavaModuleResolution(unittest.TestCase):
    def test_import_path_maps_to_java_file(self):
        self.assertEqual(
            resolve_module_path(
                module_path="auth.Authenticator",
                importing_directory="src/main/java/app",
                language="java",
            ),
            [
                "src/main/java/auth/Authenticator.java",
                "src/test/java/auth/Authenticator.java",
                "auth/Authenticator.java",
            ],
        )

    def test_wildcard_imports_resolve_to_nothing(self):
        self.assertEqual(
            resolve_module_path(
                module_path="auth.*",
                importing_directory="",
                language="java",
            ),
            [],
        )

    def test_unknown_language_resolves_nothing(self):
        self.assertEqual(
            resolve_module_path(
                module_path="x",
                importing_directory="",
                language="ruby",
            ),
            [],
        )


class TestJavaExtraction(unittest.TestCase):
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

    def test_classes_interfaces_and_methods_are_typed(self):
        self.assertTrue(self._symbols("Authenticator", "class"))
        self.assertTrue(self._symbols("PersistentAuthenticator", "class"))
        self.assertTrue(self._symbols("Store", "interface"))
        self.assertTrue(self._symbols("SessionFactory", "class"))
        self.assertTrue(self._symbols("login", "method"))
        self.assertTrue(self._symbols("validateToken", "method"))
        self.assertTrue(self._symbols("save", "method"))

    def test_imports_record_raw_paths(self):
        modules = {
            (i.module_path, i.local_name)
            for i in self.result.import_references
        }
        self.assertIn(("auth.Authenticator", "Authenticator"), modules)

    def test_intra_repo_import_resolves(self):
        resolved_targets = {
            ri.target_document.relative_path
            for ri in self.result.resolved_import_references
            if ri.target_document is not None
        }
        self.assertIn("src/main/java/auth/Authenticator.java", resolved_targets)

    def test_public_types_are_exports(self):
        exported = {e.exported_name for e in self.result.exports}

        self.assertIn("Authenticator", exported)
        self.assertIn("Main", exported)
        self.assertNotIn("SessionFactory", exported)
        self.assertNotIn("PersistentAuthenticator", exported)

    def test_extends_and_implements_relationships(self):
        self.assertTrue(
            self._relationship("PersistentAuthenticator", "extends", "Authenticator")
        )
        self.assertTrue(
            self._relationship("PersistentAuthenticator", "implements", "Store")
        )

    def test_call_relationships_inside_file(self):
        self.assertTrue(self._relationship("login", "calls", "validateToken"))
        self.assertTrue(self._relationship("login", "calls", "createSession"))

    def test_chunks_exist_for_java_symbols(self):
        chunk_paths = {c.relative_path for c in self.result.chunks}
        self.assertIn("src/main/java/auth/Authenticator.java", chunk_paths)
        self.assertIn("src/main/java/app/Main.java", chunk_paths)


class TestJavaRetrieval(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        for rel in (
            "src/main/java/auth/Authenticator.java",
            "src/main/java/app/Main.java",
        ):
            content = (Path(FIXTURE_REPO) / rel).read_text(encoding="utf-8")
            dest = root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")

        self.root = root
        self.db_path = str(root / ".ckg" / "index.sqlite")
        (root / ".ckg").mkdir(parents=True, exist_ok=True)
        reindex_index(self.db_path, str(root))

    def tearDown(self):
        self.tmp.cleanup()

    def test_definition_lookup_finds_java_symbols(self):
        retriever = build_hybrid_retriever(self.db_path)

        retrieval = retriever.retrieve("where is validateToken defined")

        self.assertTrue(
            any(
                c.symbol_name == "validateToken"
                and c.relative_path == "src/main/java/auth/Authenticator.java"
                for c in retrieval.candidates
            )
        )

    def test_semantic_search_surfaces_java_symbols(self):
        retriever = build_hybrid_retriever(self.db_path)

        retrieval = retriever.retrieve("login user")

        paths = {c.relative_path for c in retrieval.candidates}
        self.assertIn("src/main/java/auth/Authenticator.java", paths)

    def test_incremental_edit_keeps_edges(self):
        (self.root / "src/main/java/auth/Authenticator.java").write_text(
            (
                "package auth;\n"
                "\n"
                "interface Store {\n"
                "    void save();\n"
                "}\n"
                "\n"
                "class SessionFactory {\n"
                "    static String createSession(String user) {\n"
                "        return user + \"!\";\n"
                "    }\n"
                "}\n"
                "\n"
                "public class Authenticator {\n"
                "    private String secret;\n"
                "\n"
                "    public Authenticator(String secret) {\n"
                "        this.secret = secret;\n"
                "    }\n"
                "\n"
                "    public static boolean validateToken(String token) {\n"
                "        return token.length() > 8;\n"
                "    }\n"
                "\n"
                "    public String login(String user, String token) {\n"
                "        if (validateToken(token)) {\n"
                "            return SessionFactory.createSession(user);\n"
                "        }\n"
                "        return \"\";\n"
                "    }\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        report = reindex_index(self.db_path, str(self.root))

        self.assertEqual(report.parsed_files, 1)

        retriever = build_hybrid_retriever(self.db_path)
        retrieval = retriever.retrieve("who calls createSession")
        names = {c.symbol_name for c in retrieval.candidates}
        self.assertIn("login", names)


if __name__ == "__main__":
    unittest.main()
