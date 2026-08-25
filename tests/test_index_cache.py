import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from retrieval import index_cache
from retrieval.index_cache import clear, load_index_cached
from storage.index_store import persist_index, current_generation


AUTH = {
    "a.ts": "export function createAuth() { return 1; }\n",
    "b.ts": (
        'import { createAuth } from "./a";\n'
        "export function run() { createAuth(); }\n"
    ),
}


class TestIndexCache(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for name, content in AUTH.items():
            (self.root / name).write_text(content, encoding="utf-8")
        self.db_path = str(self.root / "index.sqlite")
        from analysis.build_graph import build_graph

        result = build_graph(str(self.root))
        persist_index(self.db_path, result)
        clear()

    def tearDown(self):
        clear()
        self.tmp.cleanup()

    def test_second_load_reuses_same_object(self):
        first = load_index_cached(self.db_path)
        second = load_index_cached(self.db_path)

        self.assertIs(first, second)

    def test_generation_bump_invalidates_cache(self):
        first = load_index_cached(self.db_path)

        from indexing.indexer import reindex_index

        reindex_index(self.db_path, str(self.root))
        second = load_index_cached(self.db_path)

        self.assertIsNot(first, second)
        # The generation really did move.
        self.assertNotEqual(
            current_generation(self.db_path),
            0,
        )

    def test_external_persist_invalidates_cache(self):
        first = load_index_cached(self.db_path)

        # Simulate another process writing to the same database.
        from analysis.build_graph import build_graph

        persist_index(self.db_path, build_graph(str(self.root)))

        second = load_index_cached(self.db_path)

        self.assertIsNot(first, second)

    def test_full_load_happens_only_once_between_generations(self):
        with patch(
            "retrieval.index_cache.load_index",
            wraps=index_cache.load_index,
        ) as spy:
            load_index_cached(self.db_path)
            load_index_cached(self.db_path)
            load_index_cached(self.db_path)

        self.assertEqual(spy.call_count, 1)


if __name__ == "__main__":
    unittest.main()
