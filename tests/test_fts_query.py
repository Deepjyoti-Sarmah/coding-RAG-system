import unittest

from storage.repositories.chunk_fts_repository import build_fts_query


class TestBuildFtsQuery(unittest.TestCase):
    def test_empty_string(self):
        self.assertEqual(build_fts_query(""), "")

    def test_punctuation_only(self):
        self.assertEqual(build_fts_query("???!!!"), "")

    def test_all_stopwords_falls_back_to_unfiltered(self):
        query = build_fts_query("where is the")
        self.assertEqual(query, '"where" OR "is" OR "the"')

    def test_stopwords_dropped_when_real_terms_exist(self):
        query = build_fts_query("where is login defined")
        terms = query.split(" OR ")
        self.assertNotIn('"where"', terms)
        self.assertNotIn('"is"', terms)
        self.assertIn('"login"', terms)
        self.assertIn('"defined"', terms)

    def test_terms_joined_with_or_and_quoted(self):
        query = build_fts_query("login defined")
        self.assertEqual(query, '"login" OR "defined"')

    def test_camel_case_expansion(self):
        query = build_fts_query("createAuth")
        terms = query.split(" OR ")
        self.assertIn('"createAuth"', terms)
        self.assertIn('"create"', terms)
        self.assertIn('"Auth"', terms)

    def test_snake_case_expansion(self):
        query = build_fts_query("create_auth")
        terms = query.split(" OR ")
        self.assertIn('"create_auth"', terms)
        self.assertIn('"create"', terms)
        self.assertIn('"auth"', terms)

    def test_split_fragments_that_are_stopwords_are_excluded(self):
        query = build_fts_query("isValid")
        terms = query.split(" OR ")
        self.assertIn('"isValid"', terms)
        self.assertNotIn('"is"', terms)
        self.assertIn('"Valid"', terms)

    def test_single_character_split_fragments_excluded(self):
        query = build_fts_query("aX")
        terms = query.split(" OR ")
        self.assertIn('"aX"', terms)
        self.assertEqual(len(terms), 1)


if __name__ == "__main__":
    unittest.main()
