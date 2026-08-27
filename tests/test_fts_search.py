import tempfile
import unittest
from pathlib import Path

from analysis.build_graph import build_graph
from storage.index_store import persist_index, search_lexical

FILES = {
    "auth.ts": (
        "export function createAuth() { return 1; }\n"
        "export function login(name: string) { return createAuth(); }\n"
    ),
    "api.ts": (
        'import { login } from "./auth";\n'
        'export function run() { login("admin"); }\n'
    ),
}


def _persist(root: Path, db_path: str) -> None:
    result = build_graph(str(root))
    persist_index(db_path, result)


def _write(root: Path, files: dict[str, str]) -> None:
    for relative_path, content in files.items():
        (root / relative_path).write_text(content, encoding="utf-8")


def _keys(hits) -> set[str]:
    return {hit.chunk_key for hit in hits}


class TestFtsSearch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db_path = str(self.root / "index.sqlite")
        _write(self.root, FILES)
        _persist(self.root, self.db_path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_search_finds_symbol_name(self):
        hits = search_lexical(self.db_path, "createAuth")

        self.assertIn(
            "auth.ts|typescript|createAuth|function",
            _keys(hits),
        )

    def test_search_finds_qualified_name(self):
        hits = search_lexical(self.db_path, "login")

        self.assertIn("auth.ts|typescript|login|function", _keys(hits))

    def test_search_finds_file_path(self):
        hits = search_lexical(self.db_path, "auth.ts")

        self.assertTrue(
            any(hit.relative_path == "auth.ts" for hit in hits)
        )

    def test_search_finds_chunk_source_text(self):
        hits = search_lexical(self.db_path, "admin")

        self.assertIn("api.ts|typescript|run|function", _keys(hits))

    def test_results_sorted_by_bm25_score(self):
        hits = search_lexical(self.db_path, "login createAuth", limit=10)

        scores = [hit.score for hit in hits]
        self.assertEqual(scores, sorted(scores))

    def test_empty_query_returns_nothing(self):
        self.assertEqual(search_lexical(self.db_path, ""), [])

    def test_no_match_returns_nothing(self):
        self.assertEqual(
            search_lexical(self.db_path, "totallyUnrelatedTerm"),
            [],
        )

    def test_re_persist_does_not_duplicate_fts_rows(self):
        _persist(self.root, self.db_path)

        hits = search_lexical(self.db_path, "createAuth", limit=50)

        self.assertEqual(len(_keys(hits)), len(hits))

    def test_search_respects_limit(self):
        hits = search_lexical(self.db_path, "auth", limit=1)

        self.assertLessEqual(len(hits), 1)

    def test_natural_language_query_finds_definition(self):
        hits = search_lexical(self.db_path, "where is login defined")

        self.assertIn("auth.ts|typescript|login|function", _keys(hits))


if __name__ == "__main__":
    unittest.main()