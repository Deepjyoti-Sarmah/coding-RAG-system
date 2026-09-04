import tempfile
import unittest
from pathlib import Path

from ingestion.ignore_rules import load_ignore_rules


class TestIgnoreRules(unittest.TestCase):
    def test_no_ignore_files_ignores_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            rules = load_ignore_rules(tmp)

            self.assertFalse(rules.is_ignored("auth.ts"))

    def test_gitignore_pattern_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".gitignore").write_text("*.gen.ts\n", encoding="utf-8")

            rules = load_ignore_rules(root)

            self.assertTrue(rules.is_ignored("schema.gen.ts"))
            self.assertFalse(rules.is_ignored("schema.ts"))

    def test_gitignore_directory_pattern_matches_nested_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".gitignore").write_text("vendor/\n", encoding="utf-8")

            rules = load_ignore_rules(root)

            self.assertTrue(rules.is_ignored("vendor/lib.ts"))
            self.assertTrue(rules.is_ignored("src/vendor/lib.ts"))
            self.assertFalse(rules.is_ignored("src/main.ts"))

    def test_ckgignore_patterns_are_honored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".sgignore").write_text("fixtures/\n", encoding="utf-8")

            rules = load_ignore_rules(root)

            self.assertTrue(rules.is_ignored("fixtures/sample.ts"))

    def test_gitignore_and_ckgignore_combine(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".gitignore").write_text("*.gen.ts\n", encoding="utf-8")
            (root / ".sgignore").write_text("fixtures/\n", encoding="utf-8")

            rules = load_ignore_rules(root)

            self.assertTrue(rules.is_ignored("schema.gen.ts"))
            self.assertTrue(rules.is_ignored("fixtures/sample.ts"))

    def test_negation_pattern_unignores(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".gitignore").write_text(
                "*.gen.ts\n!keep.gen.ts\n", encoding="utf-8"
            )

            rules = load_ignore_rules(root)

            self.assertTrue(rules.is_ignored("schema.gen.ts"))
            self.assertFalse(rules.is_ignored("keep.gen.ts"))

    def test_is_dir_appends_trailing_slash_for_directory_only_patterns(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".gitignore").write_text("build/\n", encoding="utf-8")

            rules = load_ignore_rules(root)

            self.assertTrue(rules.is_ignored("build", is_dir=True))
            self.assertFalse(rules.is_ignored("build.ts", is_dir=False))


if __name__ == "__main__":
    unittest.main()
