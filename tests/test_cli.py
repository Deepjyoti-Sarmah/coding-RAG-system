import tempfile
import unittest
from pathlib import Path

from cli import (
    cmd_callees,
    cmd_callers,
    cmd_context,
    cmd_definition,
    cmd_imports,
    cmd_index,
    cmd_search,
    cmd_status,
    default_db_path,
    has_embeddings,
    main,
)
from embeddings.fake_provider import FakeEmbeddingProvider

AUTH = {
    "auth.ts": (
        "export function createAuth() { return 1; }\n"
        "export function login(name: string) { createAuth(); return name; }\n"
    ),
    "api.ts": (
        'import { login } from "./auth";\n'
        'export function run() { login("admin"); }\n'
    ),
}


def _write(root: Path, files: dict[str, str]) -> None:
    for relative_path, content in files.items():
        (root / relative_path).write_text(content, encoding="utf-8")


class TestCliCommands(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db_path = str(self.root / "index.sqlite")
        _write(self.root, AUTH)

    def tearDown(self):
        self.tmp.cleanup()

    def test_default_db_path_is_dot_ckg_under_root(self):
        self.assertEqual(
            default_db_path(str(self.root)),
            str(self.root / ".ckg" / "index.sqlite"),
        )

    def test_index_creates_db_and_reports_parsed_files(self):
        report = cmd_index(str(self.root), self.db_path)

        self.assertTrue(Path(self.db_path).exists())
        self.assertEqual(report.parsed_files, 2)

    def test_index_without_provider_leaves_embeddings_empty(self):
        cmd_index(str(self.root), self.db_path)

        self.assertFalse(has_embeddings(self.db_path))

    def test_index_with_provider_embeds_chunks(self):
        cmd_index(str(self.root), self.db_path, provider=FakeEmbeddingProvider(dimension=8))

        self.assertTrue(has_embeddings(self.db_path))

    def test_status_reports_generation_and_counts(self):
        cmd_index(str(self.root), self.db_path)

        status = cmd_status(self.db_path)

        self.assertEqual(status["generation"], 1)
        self.assertEqual(status["documents"], 2)
        self.assertGreater(status["symbols"], 0)
        self.assertGreater(status["chunks"], 0)
        self.assertEqual(status["embeddings"], 0)
        self.assertEqual(status["embedding_jobs"]["PENDING"], status["chunks"])

    def test_search_without_provider_uses_fts_and_exact(self):
        cmd_index(str(self.root), self.db_path)

        retrieval = cmd_search(self.db_path, "login")

        self.assertIn("login", {c.symbol_name for c in retrieval.candidates})

    def test_search_with_provider_uses_vector_source(self):
        provider = FakeEmbeddingProvider(dimension=8)
        cmd_index(str(self.root), self.db_path, provider=provider)

        retrieval = cmd_search(self.db_path, "authentication flow", provider=provider)

        sources = {source for c in retrieval.candidates for source in c.sources}
        self.assertIn("vector", sources)

    def test_definition_finds_symbol(self):
        cmd_index(str(self.root), self.db_path)

        retrieval = cmd_definition(self.db_path, "createAuth")

        self.assertEqual(retrieval.strategy, "exact_symbol")
        self.assertEqual({c.symbol_name for c in retrieval.candidates}, {"createAuth"})

    def test_callers_and_callees(self):
        cmd_index(str(self.root), self.db_path)

        callers = cmd_callers(self.db_path, "login")
        callees = cmd_callees(self.db_path, "login")

        self.assertEqual({c.symbol_name for c in callers.candidates}, {"run"})
        self.assertEqual({c.symbol_name for c in callees.candidates}, {"createAuth"})

    def test_imports_lists_resolved_and_local_names(self):
        cmd_index(str(self.root), self.db_path)

        imports = cmd_imports(self.db_path, "api.ts")

        self.assertEqual(len(imports), 1)
        import_reference, resolved = imports[0]
        self.assertEqual(import_reference.local_name, "login")
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.target_document.relative_path, "auth.ts")
        self.assertEqual(resolved.target_symbol.name, "login")

    def test_imports_on_unknown_file_is_empty(self):
        cmd_index(str(self.root), self.db_path)

        self.assertEqual(cmd_imports(self.db_path, "missing.ts"), [])

    def test_context_returns_pack_within_budget(self):
        cmd_index(str(self.root), self.db_path)

        pack = cmd_context(self.db_path, "login", token_budget=500)

        self.assertLessEqual(pack.total_tokens, 500)
        self.assertIn(
            "login",
            [entry.qualified_name for entry in pack.primary_definitions],
        )


class TestCliMain(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db_path = str(self.root / "index.sqlite")
        _write(self.root, AUTH)

    def tearDown(self):
        self.tmp.cleanup()

    def test_index_command_creates_db(self):
        exit_code = main(["--db", self.db_path, "index", str(self.root)])

        self.assertEqual(exit_code, 0)
        self.assertTrue(Path(self.db_path).exists())

    def test_status_before_index_reports_missing_and_nonzero_exit(self):
        exit_code = main(["--db", self.db_path, "status"])

        self.assertEqual(exit_code, 1)

    def test_status_after_index_succeeds(self):
        main(["--db", self.db_path, "index", str(self.root)])

        exit_code = main(["--db", self.db_path, "status"])

        self.assertEqual(exit_code, 0)

    def test_search_command_defaults_to_no_vector_without_embeddings(self):
        main(["--db", self.db_path, "index", str(self.root)])

        exit_code = main(["--db", self.db_path, "search", "login"])

        self.assertEqual(exit_code, 0)

    def test_eval_command_runs_without_touching_the_target_db(self):
        # eval runs entirely against its own copy of the fixed benchmark
        # repo; it takes no --db/path and must not require a prior index.
        exit_code = main(["eval"])

        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
