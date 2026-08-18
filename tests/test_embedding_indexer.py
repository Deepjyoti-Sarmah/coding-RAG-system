import tempfile
import unittest
from pathlib import Path

import numpy as np

from embeddings.fake_provider import FakeEmbeddingProvider
from indexing.embedding_queue import run_embedding_worker
from indexing.indexer import reindex_index
from storage.index_store import load_embedding_cache, load_index

AUTH = {
    "a.ts": "export function createAuth() { return 1; }\n",
    "b.ts": (
        'import { createAuth } from "./a";\n'
        "export function run() { createAuth(); }\n"
    ),
}


def _write(root: Path, files: dict[str, str]) -> None:
    for relative_path, content in files.items():
        (root / relative_path).write_text(content, encoding="utf-8")


class TestEmbeddingIndexer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db_path = str(self.root / "index.sqlite")
        self.provider = FakeEmbeddingProvider(dimension=8)

    def tearDown(self):
        self.tmp.cleanup()

    def test_first_run_embeds_every_chunk(self):
        _write(self.root, AUTH)
        reindex_index(self.db_path, str(self.root))

        chunk_count = len(load_index(self.db_path).chunks)
        report = run_embedding_worker(self.db_path, self.provider)

        self.assertGreater(chunk_count, 0)
        self.assertEqual(report.claimed, chunk_count)
        self.assertEqual(report.done, chunk_count)

    def test_noop_run_reuses_all_embeddings(self):
        _write(self.root, AUTH)
        reindex_index(self.db_path, str(self.root))
        run_embedding_worker(self.db_path, self.provider)
        before = load_embedding_cache(self.db_path)

        reindex_index(self.db_path, str(self.root))
        report = run_embedding_worker(self.db_path, self.provider)

        after = load_embedding_cache(self.db_path)
        self.assertEqual(report.claimed, 0)
        self.assertEqual(report.done, 0)
        self.assertEqual(set(before), set(after))
        for content_hash, vector in before.items():
            np.testing.assert_array_equal(vector, after[content_hash])

    def test_body_edit_reembeds_only_changed_chunk(self):
        _write(self.root, AUTH)
        reindex_index(self.db_path, str(self.root))
        run_embedding_worker(self.db_path, self.provider)

        before = load_embedding_cache(self.db_path)
        _write(
            self.root,
            {"a.ts": "export function createAuth() { return 2; }\n"},
        )
        reindex_index(self.db_path, str(self.root))
        report = run_embedding_worker(self.db_path, self.provider)
        after = load_embedding_cache(self.db_path)

        self.assertEqual(report.claimed, 1)
        self.assertEqual(report.done, 1)

        unchanged_hashes = {
            chunk.content_hash
            for chunk in load_index(self.db_path).chunks
            if chunk.relative_path == "b.ts"
        }
        for content_hash in unchanged_hashes:
            self.assertIn(content_hash, before)
            np.testing.assert_array_equal(before[content_hash], after[content_hash])

    def test_embeddings_round_trip_persistence(self):
        _write(self.root, AUTH)
        reindex_index(self.db_path, str(self.root))
        run_embedding_worker(self.db_path, self.provider)

        cache = load_embedding_cache(self.db_path)

        self.assertGreater(len(cache), 0)
        for vector in cache.values():
            self.assertEqual(vector.dtype, np.float32)
            self.assertEqual(vector.shape, (8,))
            self.assertAlmostEqual(np.linalg.norm(vector), 1.0, places=6)

    def test_without_worker_run_skips_embeddings(self):
        _write(self.root, AUTH)

        reindex_index(self.db_path, str(self.root))

        self.assertEqual(load_embedding_cache(self.db_path), {})


if __name__ == "__main__":
    unittest.main()
