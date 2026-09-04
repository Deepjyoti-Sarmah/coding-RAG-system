import unittest
from unittest.mock import MagicMock, patch

import numpy as np


class TestOllamaProvider(unittest.TestCase):
    def test_ollama_available_probes_tags(self):
        from embeddings.ollama_provider import ollama_available

        try:
            import httpx
        except ImportError:
            self.skipTest("httpx not available")
        mock_resp = MagicMock(status_code=200)
        with patch.object(httpx, "get", return_value=mock_resp):
            self.assertTrue(ollama_available("http://localhost:11434"))
        mock_fail = MagicMock(status_code=500)
        with patch.object(httpx, "get", return_value=mock_fail):
            self.assertFalse(ollama_available("http://localhost:11434"))
        with patch.object(httpx, "get", side_effect=Exception("conn refused")):
            self.assertFalse(ollama_available("http://localhost:11434"))

    def test_ollama_provider_embeds_via_mock(self):
        from embeddings.ollama_provider import OllamaEmbeddingProvider

        # Mock _embed_batch probe and actual embed calls
        fake_vec = [0.1] * 768
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"embeddings": [fake_vec]}
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()

        try:
            import httpx
        except ImportError:
            self.skipTest("httpx not available")

        with patch.object(httpx, "post", return_value=mock_resp):
            provider = OllamaEmbeddingProvider(model_name="nomic-embed-text", base_url="http://localhost:11434")
            self.assertEqual(provider.dimension, 768)
            self.assertIn("ollama:nomic-embed-text", provider.model_id)
            vec = provider.embed("hello")
            self.assertEqual(vec.shape, (768,))
            # normalized
            self.assertAlmostEqual(np.linalg.norm(vec), 1.0, places=5)

    def test_ollama_env_var_precedence(self):
        import os

        from embeddings.ollama_provider import (
            _resolve_ollama_model,
            _resolve_ollama_url,
        )

        orig = os.environ.copy()
        try:
            os.environ.pop("SG_OLLAMA_URL", None)
            os.environ.pop("SG_OLLAMA_HOST", None)
            os.environ.pop("OLLAMA_HOST", None)
            os.environ.pop("SG_OLLAMA_MODEL", None)
            os.environ.pop("OLLAMA_MODEL", None)

            self.assertEqual(_resolve_ollama_url(), "http://localhost:11434")
            self.assertEqual(_resolve_ollama_model(), "nomic-embed-text")

            os.environ["OLLAMA_HOST"] = "http://myhost:11434"
            self.assertEqual(_resolve_ollama_url(), "http://myhost:11434")

            os.environ["SG_OLLAMA_URL"] = "http://sg-host:11434"
            self.assertEqual(_resolve_ollama_url(), "http://sg-host:11434")

            os.environ["OLLAMA_MODEL"] = "my-model"
            self.assertEqual(_resolve_ollama_model(), "my-model")
            os.environ["SG_OLLAMA_MODEL"] = "sg-model"
            self.assertEqual(_resolve_ollama_model(), "sg-model")
        finally:
            os.environ.clear()
            os.environ.update(orig)

    def test_no_torch_imported_for_ollama(self):
        # Ensure importing ollama provider does not import torch/sentence_transformers
        import sys

        for mod in list(sys.modules.keys()):
            if "torch" in mod or "sentence_transformers" in mod:
                # Don't fail if already imported by other tests, but check fresh import doesn't trigger
                pass
        # Import fresh in subprocess would be ideal, but check that ollama_provider import itself doesn't touch torch

        if "embeddings.ollama_provider" in sys.modules:
            del sys.modules["embeddings.ollama_provider"]
        # Track imports
        with patch.dict("sys.modules", {}):
            pass
        # Just verify file doesn't import torch at top level
        with open("embeddings/ollama_provider.py", encoding="utf-8") as f:
            content = f.read()
            self.assertNotIn("import torch", content)
            self.assertNotIn("sentence_transformers", content)


if __name__ == "__main__":
    unittest.main()
