import unittest

from config import INCLUDE_EXTENSIONS
from ingestion.language import detect_language
from parsing.registry import PARSER


class TestLanguageParserSupport(unittest.TestCase):
    def test_every_include_extension_has_a_parser(self):
        for extension in INCLUDE_EXTENSIONS:
            language = detect_language(extension)
            self.assertIn(
                language,
                PARSER,
                f"extension {extension} maps to language '{language}' with no parser",
            )

    def test_unknown_extension_has_no_parser(self):
        for extension in (".md", ".py", ".go", ".txt"):
            language = detect_language(extension)
            self.assertEqual(language, "unknown")
            self.assertNotIn(language, PARSER)


if __name__ == "__main__":
    unittest.main()