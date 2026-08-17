import unittest

import numpy as np

from chunking.symbol_chunker import CHUNK_VERSION, SemanticChunk
from embeddings.fake_provider import FakeEmbeddingProvider
from indexing.embedding_store import embed_chunks


def _chunk(
    key: str,
    *,
    text: str = "def body",
    content_hash: str | None = None,
) -> SemanticChunk:
    return SemanticChunk(
        chunk_key=key,
        symbol_id=f"symbol-{key}",
        relative_path=f"{key}.ts",
        embedding_text=f"{key}: {text}",
        display_text=text,
        content_hash=content_hash or f"hash-{key}",
        chunk_version=CHUNK_VERSION,
    )


class _CountingProvider(FakeEmbeddingProvider):
    def __init__(self):
        super().__init__(dimension=8)
        self.batch_calls = 0

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        self.batch_calls += 1
        return super().embed_batch(texts)


class TestEmbedChunks(unittest.TestCase):
    def test_embeds_everything_when_cache_is_empty(self):
        chunks = [
            _chunk("a", content_hash="h1"),
            _chunk("b", content_hash="h2"),
            _chunk("c", content_hash="h3"),
        ]
        provider = _CountingProvider()

        embeddings, new_count = embed_chunks(chunks, provider, cache={})

        self.assertEqual(new_count, 3)
        self.assertEqual(set(embeddings), {"a", "b", "c"})
        self.assertEqual(provider.batch_calls, 1)
        for vector in embeddings.values():
            self.assertEqual(vector.shape, (8,))
            self.assertAlmostEqual(np.linalg.norm(vector), 1.0, places=6)

    def test_full_cache_is_noop(self):
        chunks = [
            _chunk("a", content_hash="h1"),
            _chunk("b", content_hash="h2"),
        ]
        cache = {
            "h1": np.full(8, 1.0, dtype=np.float32),
            "h2": np.full(8, 2.0, dtype=np.float32),
        }
        provider = _CountingProvider()

        embeddings, new_count = embed_chunks(chunks, provider, cache=cache)

        self.assertEqual(new_count, 0)
        self.assertEqual(provider.batch_calls, 0)
        np.testing.assert_array_equal(embeddings["a"], cache["h1"])
        np.testing.assert_array_equal(embeddings["b"], cache["h2"])

    def test_only_missing_embeddings_are_embedded(self):
        chunks = [
            _chunk("a", content_hash="h1"),
            _chunk("b", content_hash="h2"),
            _chunk("c", content_hash="h3"),
        ]
        cached = np.full(8, 5.0, dtype=np.float32)
        provider = _CountingProvider()

        embeddings, new_count = embed_chunks(
            chunks,
            provider,
            cache={"h2": cached},
        )

        self.assertEqual(new_count, 2)
        self.assertEqual(provider.batch_calls, 1)
        np.testing.assert_array_equal(embeddings["b"], cached)
        self.assertFalse(np.array_equal(embeddings["a"], cached))
        self.assertFalse(np.array_equal(embeddings["c"], cached))

    def test_empty_chunks(self):
        provider = _CountingProvider()

        embeddings, new_count = embed_chunks([], provider, cache={})

        self.assertEqual(embeddings, {})
        self.assertEqual(new_count, 0)
        self.assertEqual(provider.batch_calls, 0)


if __name__ == "__main__":
    unittest.main()