import tempfile
import unittest
from pathlib import Path

from analysis.build_graph import build_graph
from analysis.semantic.normalize_path import resolve_module_path
from indexing.indexer import reindex_index
from retrieval.index_queries import build_hybrid_retriever

FIXTURE_REPO = str(
    Path(__file__).resolve().parent / "fixtures" / "rust_repo"
)


class TestRustModuleResolution(unittest.TestCase):
    def test_crate_path_maps_to_module_and_item_candidates(self):
        self.assertEqual(
            resolve_module_path(
                module_path="crate::auth::login",
                importing_directory="src",
                language="rust",
            ),
            [
                "src/auth/login.rs",
                "src/auth/login/mod.rs",
                "src/auth.rs",
                "src/auth/mod.rs",
            ],
        )

    def test_external_crates_resolve_to_nothing(self):
        self.assertEqual(
            resolve_module_path(
                module_path="serde::Serialize",
                importing_directory="src",
                language="rust",
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


class TestRustExtraction(unittest.TestCase):
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

    def test_structs_traits_and_functions_are_typed(self):
        self.assertTrue(self._symbols("Authenticator", "class"))
        self.assertTrue(self._symbols("Store", "interface"))
        self.assertTrue(self._symbols("Role", "class"))
        self.assertTrue(self._symbols("login", "function"))
        self.assertTrue(self._symbols("validate_token", "function"))
        self.assertTrue(self._symbols("new", "method"))
        self.assertTrue(self._symbols("save", "method"))

    def test_imports_record_raw_paths(self):
        modules = {
            (i.module_path, i.local_name)
            for i in self.result.import_references
        }
        self.assertIn(("crate::auth::Authenticator", "Authenticator"), modules)
        self.assertIn(("crate::auth::login", "login"), modules)

    def test_intra_repo_import_resolves(self):
        resolved_targets = {
            ri.target_document.relative_path
            for ri in self.result.resolved_import_references
            if ri.target_document is not None
        }
        self.assertIn("src/auth.rs", resolved_targets)

    def test_pub_items_are_exports(self):
        exported = {e.exported_name for e in self.result.exports}

        self.assertIn("Authenticator", exported)
        self.assertIn("Store", exported)
        self.assertIn("login", exported)
        self.assertNotIn("create_session", exported)

    def test_impl_trait_for_type_is_implements(self):
        self.assertTrue(self._relationship("Authenticator", "implements", "Store"))

    def test_call_relationships_inside_file(self):
        self.assertTrue(self._relationship("login", "calls", "validate_token"))
        self.assertTrue(self._relationship("login", "calls", "create_session"))

    def test_call_relationship_across_files_via_import(self):
        self.assertTrue(self._relationship("handle_request", "calls", "login"))

    def test_chunks_exist_for_rust_symbols(self):
        chunk_paths = {c.relative_path for c in self.result.chunks}
        self.assertIn("src/auth.rs", chunk_paths)
        self.assertIn("src/main.rs", chunk_paths)


class TestRustRetrieval(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        for rel in ("src/auth.rs", "src/main.rs"):
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

    def test_definition_lookup_finds_rust_symbols(self):
        retriever = build_hybrid_retriever(self.db_path)

        retrieval = retriever.retrieve("where is validate_token defined")

        self.assertTrue(
            any(
                c.symbol_name == "validate_token" and c.relative_path == "src/auth.rs"
                for c in retrieval.candidates
            )
        )

    def test_semantic_search_surfaces_rust_symbols(self):
        retriever = build_hybrid_retriever(self.db_path)

        retrieval = retriever.retrieve("login user")

        paths = {c.relative_path for c in retrieval.candidates}
        self.assertIn("src/auth.rs", paths)

    def test_incremental_edit_keeps_edges(self):
        (self.root / "src/auth.rs").write_text(
            (
                "pub struct Authenticator {\n"
                "    secret: String,\n"
                "}\n"
                "\n"
                "pub trait Store {\n"
                "    fn save(&self);\n"
                "}\n"
                "\n"
                "impl Store for Authenticator {\n"
                "    fn save(&self) {}\n"
                "}\n"
                "\n"
                "fn create_session(user: &str) -> String {\n"
                "    format!(\"{}!\", user)\n"
                "}\n"
                "\n"
                "pub fn validate_token(token: &str) -> bool {\n"
                "    token.len() > 8\n"
                "}\n"
                "\n"
                "pub fn login(user: &str, token: &str) -> String {\n"
                "    if validate_token(token) {\n"
                "        create_session(user)\n"
                "    } else {\n"
                "        String::new()\n"
                "    }\n"
                "}\n"
                "\n"
                "pub enum Role {\n"
                "    Admin,\n"
                "    User,\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        report = reindex_index(self.db_path, str(self.root))

        self.assertEqual(report.parsed_files, 1)

        retriever = build_hybrid_retriever(self.db_path)
        retrieval = retriever.retrieve("who calls create_session")
        names = {c.symbol_name for c in retrieval.candidates}
        self.assertIn("login", names)


if __name__ == "__main__":
    unittest.main()
