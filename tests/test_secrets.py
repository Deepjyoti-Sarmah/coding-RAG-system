import unittest
from indexing.secrets import contains_secret, is_secret_filename, redact_pii, redact_secrets, should_skip_file_content


class TestSecrets(unittest.TestCase):
    def test_detect_aws(self):
        self.assertTrue(contains_secret("AKIAIOSFODNN7EXAMPLE"))
        self.assertFalse(contains_secret("hello world"))

    def test_redact(self):
        self.assertEqual(redact_secrets("key AKIAIOSFODNN7EXAMPLE end"), "key [REDACTED] end")

    def test_skip_env(self):
        self.assertTrue(should_skip_file_content(".env", "AKIAIOSFODNN7EXAMPLE"))

    def test_13_regexes(self):
        self.assertTrue(contains_secret("ghp_" + "A" * 36))
        self.assertTrue(contains_secret("ghs_" + "A" * 36))
        self.assertTrue(contains_secret("xoxb-123456789012"))
        self.assertTrue(contains_secret("sk-ant-" + "A" * 20))
        self.assertTrue(contains_secret("AIza" + "A" * 35))
        self.assertTrue(contains_secret("eyJ" + "A" * 10 + "." + "B" * 10 + "." + "C" * 10))

    def test_placeholder_exempt(self):
        self.assertFalse(contains_secret("your-api-key AKIAIOSFODNN7EXAMPLE"))
        self.assertEqual(redact_secrets("your-api-key AKIAIOSFODNN7EXAMPLE"), "your-api-key AKIAIOSFODNN7EXAMPLE")

    def test_secret_filename(self):
        self.assertTrue(is_secret_filename(".env"))
        self.assertTrue(is_secret_filename("secrets.yml"))
        self.assertTrue(is_secret_filename("key.pem"))
        self.assertFalse(is_secret_filename("src/app.py"))

    def test_pii(self):
        self.assertNotEqual(redact_pii("a@b.com"), "a@b.com")
        self.assertIn("[REDACTED:EMAIL]", redact_pii("a@b.com"))
        self.assertEqual(redact_pii("a@b.com", enabled=False), "a@b.com")

    def test_redact_github_pat(self):
        self.assertTrue(contains_secret("github_pat_" + "A" * 80))
        self.assertIn("[REDACTED]", redact_secrets("github_pat_" + "A" * 80))

    def test_redact_slack(self):
        # constructed without literal to avoid push protection (GH013)
        token = "xox" + "b-1234567890-1234567890-AbCdEfGhIjKlMnOp"
        self.assertTrue(contains_secret(token))

    def test_redact_stripe(self):
        self.assertTrue(contains_secret("sk_live_" + "A" * 20))

    def test_redact_openai(self):
        self.assertTrue(contains_secret("sk-" + "A" * 20 + "T3BlbkFJ" + "B" * 20))

    def test_redact_aws_secret(self):
        self.assertTrue(contains_secret("aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"))

    def test_redact_generic_not_in_code(self):
        # generic password inside JS object should NOT be redacted (would break parsing) — only .env style with KEY=VALUE
        self.assertFalse(contains_secret('secret: "s3cr3t"'))

    def test_pii_ip(self):
        self.assertIn("[REDACTED:IP]", redact_pii("192.168.1.1"))

    def test_pii_ssn(self):
        self.assertIn("[REDACTED:SSN]", redact_pii("123-45-6789"))

    def test_pii_phone(self):
        self.assertIn("[REDACTED:PHONE]", redact_pii("+14155552671"))


if __name__ == "__main__":
    unittest.main()
