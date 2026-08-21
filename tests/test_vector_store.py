import tempfile
import unittest
from pathlib import Path

import numpy as np

from chunking.symbol_chunker import CHUNK_VERSION, SemanticChunk
from embeddings.fake_provider import FakeEmbeddingProvider
from indexing.embedding_queue import run_embedding_worker
from indexing.indexer import reindex_index
from retrieval.index_queries import load_vector_store
from retrieval.numpy_vector_store import NumpyVectorStore
from storage.index_store import load_index


def _chunk(key: str, relative_path: str = "a.ts") -> SemanticChunk:
    return SemanticChunk(
        chunk_key=key,
        symbol_id=f"symbol-{key}",
        relative_path=relative_path,
        embedding_text=f"{key} body",
        display_text=f"{key} body",
        content_hash=f"hash-{key}",
        chunk_version=CHUNK_VERSION,
    )


def _entry(
    chunk: SemanticChunk,
    vector: list[float],
) -> tuple[SemanticChunk, np.ndarray]:
    return chunk, np.asarray(vector, dtype=np.float32)


class TestNumpyVectorStore(unittest.TestCase):
    def test_search_returns_top_k_by_cosine(self):
        store = NumpyVectorStore(
            [
                _entry(_chunk("a"), [1.0, 0.0, 0.0]),
                _entry(_chunk("b"), [0.0, 1.0, 0.0]),
                _entry(_chunk("c"), [0.707, 0.707, 0.0]),
            ]
        )

        hits = store.search(np.array([1.0, 0.0, 0.0], dtype=np.float32), top_k=2)

        self.assertEqual([hit.chunk_key for hit in hits], ["a", "c"])
        self.assertGreater(hits[0].score, hits[1].score)

    def test_path_filter_restricts_results(self):
        store = NumpyVectorStore(
            [
                _entry(_chunk("a", "a.ts"), [1.0, 0.0]),
                _entry(_chunk("b", "b.ts"), [1.0, 0.0]),
            ]
        )

        hits = store.search(
            np.array([1.0, 0.0], dtype=np.float32),
            relative_path="b.ts",
        )

        self.assertEqual([hit.chunk_key for hit in hits], ["b"])
        self.assertEqual(hits[0].relative_path, "b.ts")

    def test_empty_store_returns_nothing(self):
        store = NumpyVectorStore([])

        self.assertEqual(
            store.search(np.array([1.0, 0.0], dtype=np.float32)),
            [],
        )

    def test_top_k_larger_than_entries_is_safe(self):
        store = NumpyVectorStore([_entry(_chunk("a"), [1.0, 0.0])])

        hits = store.search(
            np.array([1.0, 0.0], dtype=np.float32),
            top_k=10,
        )

        self.assertEqual(len(hits), 1)

    def test_path_filter_without_match_returns_nothing(self):
        store = NumpyVectorStore([_entry(_chunk("a", "a.ts"), [1.0, 0.0])])

        hits = store.search(
            np.array([1.0, 0.0], dtype=np.float32),
            relative_path="missing.ts",
        )

        self.assertEqual(hits, [])


class TestVectorStorePersistence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db_path = str(self.root / "index.sqlite")
        self.provider = FakeEmbeddingProvider(dimension=8)
        (self.root / "a.ts").write_text(
            "export function createAuth() { return 1; }\n",
            encoding="utf-8",
        )
        (self.root / "b.ts").write_text(
            'import { createAuth } from "./a";\n'
            "export function run() { createAuth(); }\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_load_vector_store_returns_persisted_embeddings(self):
        reindex_index(self.db_path, str(self.root))
        run_embedding_worker(self.db_path, self.provider)

        result = load_index(self.db_path)
        target = next(
            chunk for chunk in result.chunks if chunk.relative_path == "a.ts"
        )
        store = load_vector_store(self.db_path)

        hits = store.search(
            self.provider.embed(target.embedding_text),
            top_k=10,
        )

        self.assertEqual(hits[0].chunk_key, target.chunk_key)
        self.assertAlmostEqual(hits[0].score, 1.0, places=6)

    def test_vector_store_reflects_reindex(self):
        reindex_index(self.db_path, str(self.root))
        run_embedding_worker(self.db_path, self.provider)
        (self.root / "a.ts").write_text(
            "export function createAuth() { return 2; }\n",
            encoding="utf-8",
        )
        reindex_index(self.db_path, str(self.root))
        run_embedding_worker(self.db_path, self.provider)

        result = load_index(self.db_path)
        target = next(
            chunk for chunk in result.chunks if chunk.relative_path == "a.ts"
        )
        store = load_vector_store(self.db_path)

        hits = store.search(
            self.provider.embed(target.embedding_text),
            top_k=10,
        )

        self.assertEqual(hits[0].chunk_key, target.chunk_key)


if __name__ == "__main__":
    unittest.main()