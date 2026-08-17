import unittest

import numpy as np

from embeddings.fake_provider import FakeEmbeddingProvider


class TestFakeEmbeddingProvider(unittest.TestCase):
    def test_reports_dimension(self):
        provider = FakeEmbeddingProvider(dimension=8)
        self.assertEqual(provider.dimension, 8)

    def test_same_text_produces_same_vector(self):
        provider = FakeEmbeddingProvider(dimension=8)

        first = provider.embed("export function login() {}")
        second = provider.embed("export function login() {}")

        np.testing.assert_array_equal(first, second)

    def test_different_texts_produce_different_vectors(self):
        provider = FakeEmbeddingProvider(dimension=8)

        first = provider.embed("export function login() {}")
        second = provider.embed("export function logout() {}")

        self.assertFalse(np.array_equal(first, second))

    def test_embed_batch_shape_and_normalization(self):
        provider = FakeEmbeddingProvider(dimension=8)

        vectors = provider.embed_batch(
            ["alpha", "beta", "gamma"]
        )

        self.assertEqual(vectors.shape, (3, 8))
        self.assertEqual(vectors.dtype, np.float32)

        for vector in vectors:
            self.assertAlmostEqual(np.linalg.norm(vector), 1.0, places=6)

    def test_embed_is_normalized(self):
        provider = FakeEmbeddingProvider(dimension=8)

        vector = provider.embed("some text")

        self.assertAlmostEqual(np.linalg.norm(vector), 1.0, places=6)

    def test_embed_query_matches_embed(self):
        provider = FakeEmbeddingProvider(dimension=8)

        np.testing.assert_array_equal(
            provider.embed_query("login"),
            provider.embed("login"),
        )

    def test_empty_batch_shape(self):
        provider = FakeEmbeddingProvider(dimension=8)

        vectors = provider.embed_batch([])

        self.assertEqual(vectors.shape, (0, 8))


if __name__ == "__main__":
    unittest.main()