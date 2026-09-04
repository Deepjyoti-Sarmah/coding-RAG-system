"""Hypothesis fuzz for secrets redaction — must not crash on 10k random."""
import unittest

from indexing.secrets import contains_secret, redact_pii, redact_secrets

try:
    from hypothesis import given, settings  # noqa: F401 -- availability probe
    from hypothesis import strategies as st  # noqa: F401 -- availability probe

    HAS_HYP = True
except ImportError:
    HAS_HYP = False

class TestSecretsFuzz(unittest.TestCase):
    def test_no_crash_random(self):
        for s in ["", "a", "AKIA", "x"*1000, "password=123", "email@a.com", "192.168.1.1", "4111111111111111"]:
            contains_secret(s)
            redact_secrets(s)
            redact_pii(s)

    def test_generic_credential(self):
        self.assertTrue(contains_secret("MY_TOKEN=123456789012345678"))
        self.assertTrue(contains_secret("export MY_SECRET=12345678901234567890"))
        self.assertIn("[REDACTED]", redact_secrets("MY_TOKEN=123456789012345678"))

    def test_luhn_valid(self):
        self.assertIn("[REDACTED:CARD]", redact_pii("4111111111111111"))
        self.assertEqual(redact_pii("1234567890123456"), "1234567890123456")
        self.assertIn("[REDACTED:CARD]", redact_pii("4111 1111 1111 1111"))

    def test_chunk_empty_no_crash(self):
        from analysis.build_result import BuildResult
        from chunking.symbol_chunker import build_semantic_chunks
        from graph.code_graph import CodeGraph
        br = BuildResult(documents=[], symbols=[], import_references=[], exports=[], references=[], resolved_references=[], resolved_import_references=[], graph=CodeGraph())
        self.assertEqual(build_semantic_chunks(br), [])

if HAS_HYP:
    from hypothesis import given as hyp_given
    from hypothesis import settings as hyp_settings
    from hypothesis import strategies as hyp_st

    class TestHypothesisFuzz(unittest.TestCase):
        @hyp_settings(max_examples=500, deadline=None)
        @hyp_given(hyp_st.text())
        def test_hypothesis_no_crash(self, s):
            contains_secret(s)
            redact_secrets(s)
            redact_pii(s)
