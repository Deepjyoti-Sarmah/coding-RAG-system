import unittest
from unittest.mock import patch

from retrieval.tokenizer import count_tokens

FALLBACK_DIVISOR = 4


class TestTokenizerFallback(unittest.TestCase):
    def test_fallback_when_encoder_unavailable(self):
        # Simulate offline / missing cache -> _encoder raises
        with patch("retrieval.tokenizer._encoder", side_effect=Exception("offline")):
            with patch("retrieval.tokenizer._encoder_available", return_value=False):
                # retrieval.tokenizer.count_tokens should use chars//4 fallback
                # need to clear lru_cache for _encoder_available
                text = "a" * 100
                # directly call without encoder
                result = count_tokens(text)
                self.assertEqual(result, max(1, len(text) // FALLBACK_DIVISOR))

    def test_fallback_empty_is_zero(self):
        with patch("retrieval.tokenizer._encoder_available", return_value=False):
            self.assertEqual(count_tokens(""), 0)

    def test_fallback_single_char_is_one(self):
        with patch("retrieval.tokenizer._encoder_available", return_value=False):
            self.assertEqual(count_tokens("x"), 1)

    def test_real_encoder_produces_reasonable_tokens(self):
        # When encoder is available, tiktoken should give deterministic counts
        result = count_tokens("hello world")
        self.assertGreaterEqual(result, 1)
        self.assertLessEqual(result, 10)

    def test_long_text_fallback_scales(self):
        with patch("retrieval.tokenizer._encoder_available", return_value=False):
            self.assertEqual(count_tokens("a" * 4000), 1000)
            self.assertEqual(count_tokens("a" * 400), 100)
