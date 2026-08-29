import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from retrieval.hybrid_retriever import _select_with_per_file_cap, HybridCandidate
from storage.repositories.chunk_fts_repository import (
    BM25_WEIGHT_CHUNK_ID,
    BM25_WEIGHT_CHUNK_TEXT,
    BM25_WEIGHT_QUALIFIED_NAME,
    BM25_WEIGHT_RELATIVE_PATH,
    BM25_WEIGHT_SYMBOL_NAME,
)


def _cand(path: str, key: str = "") -> HybridCandidate:
    return HybridCandidate(
        chunk_key=key or f"{path}|x|{path}",
        symbol_id="",
        symbol_name="",
        qualified_name="",
        relative_path=path,
        symbol_kind="",
        score=0.0,
        sources=(),
    )


class TestPerFileCap(unittest.TestCase):
    def test_admits_at_most_n_per_file(self):
        # 6 candidates: 4 from a.py, 2 from b.py, cap=3, top_k=5
        candidates = [
            _cand("a.py", "a1"),
            _cand("a.py", "a2"),
            _cand("a.py", "a3"),
            _cand("a.py", "a4"),
            _cand("b.py", "b1"),
            _cand("b.py", "b2"),
        ]
        selected = _select_with_per_file_cap(candidates, top_k=5, per_file_cap=3)
        # Should have at most 3 from a.py
        a_count = sum(1 for c in selected if c.relative_path == "a.py")
        self.assertLessEqual(a_count, 3)
        self.assertEqual(len(selected), 5)
        # First 3 from a.py should be admitted, 4th skipped until second pass
        self.assertEqual([c.chunk_key for c in selected], ["a1", "a2", "a3", "b1", "b2"])

    def test_fills_top_k_when_candidates_allow(self):
        # 10 candidates, 2 files, cap=3, top_k=10 should return all 10
        candidates = [_cand(f"file{i%2}.py", f"k{i}") for i in range(10)]
        selected = _select_with_per_file_cap(candidates, top_k=10, per_file_cap=3)
        self.assertEqual(len(selected), 10)
        # Each file at most 3 in first pass, but second pass fills remainder
        # So we should have 5 from each file
        counts = {}
        for c in selected:
            counts[c.relative_path] = counts.get(c.relative_path, 0) + 1
        self.assertEqual(counts["file0.py"], 5)
        self.assertEqual(counts["file1.py"], 5)

    def test_second_pass_admits_remainder_in_rank_order(self):
        # 5 candidates: 3 from a.py, 2 from b.py, cap=2, top_k=5
        # First pass: a1,a2,b1,b2 (a3 skipped), second pass: a3
        candidates = [
            _cand("a.py", "a1"),
            _cand("a.py", "a2"),
            _cand("a.py", "a3"),
            _cand("b.py", "b1"),
            _cand("b.py", "b2"),
        ]
        selected = _select_with_per_file_cap(candidates, top_k=5, per_file_cap=2)
        self.assertEqual([c.chunk_key for c in selected], ["a1", "a2", "b1", "b2", "a3"])

    def test_cap_zero_or_negative_returns_slice(self):
        candidates = [_cand("a.py", f"k{i}") for i in range(5)]
        self.assertEqual(len(_select_with_per_file_cap(candidates, top_k=3, per_file_cap=0)), 3)
        self.assertEqual(len(_select_with_per_file_cap(candidates, top_k=3, per_file_cap=-1)), 3)

    def test_top_k_respected_even_with_many_files(self):
        # 20 candidates, 5 files, cap=3, top_k=7
        candidates = [_cand(f"f{i%5}.py", f"k{i}") for i in range(20)]
        selected = _select_with_per_file_cap(candidates, top_k=7, per_file_cap=3)
        self.assertEqual(len(selected), 7)
        # First 7 should be diverse: each file at most 3, so first 7 are from 5 files
        self.assertLessEqual(max(sum(1 for c in selected if c.relative_path == f"f{i}.py") for i in range(5)), 3)


class TestWeightedBM25(unittest.TestCase):
    def test_weights_are_named_constants_and_ordered(self):
        # Ensure constants exist and are in schema order with expected values
        self.assertEqual(BM25_WEIGHT_CHUNK_ID, 0.0)
        self.assertEqual(BM25_WEIGHT_SYMBOL_NAME, 10.0)
        self.assertEqual(BM25_WEIGHT_QUALIFIED_NAME, 5.0)
        self.assertEqual(BM25_WEIGHT_RELATIVE_PATH, 8.0)
        self.assertEqual(BM25_WEIGHT_CHUNK_TEXT, 1.0)

    def test_weighted_query_is_well_formed_and_ordering_unchanged(self):
        # Verify that weighted bm25 still returns negative scores and ORDER BY score ASC holds
        import tempfile
        from pathlib import Path
        from analysis.build_graph import build_graph
        from storage.index_store import persist_index, search_lexical

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.py").write_text("def foo(): pass\n", encoding="utf-8")
            (root / "b.py").write_text("def bar(): pass\n", encoding="utf-8")
            db_path = str(root / "index.sqlite")
            result = build_graph(str(root))
            persist_index(db_path, result)

            # Search with weighted BM25 should still return results sorted by score ASC (more negative = better)
            hits = search_lexical(db_path, "foo")
            if hits:
                scores = [h.score for h in hits]
                self.assertEqual(scores, sorted(scores))
                # Weighted scores should be negative (bm25 returns negative)
                for s in scores:
                    self.assertLess(s, 0)

            # Also test with multiple terms
            hits2 = search_lexical(db_path, "foo bar")
            if hits2:
                scores2 = [h.score for h in hits2]
                self.assertEqual(scores2, sorted(scores2))

    def test_relative_path_weight_above_chunk_text(self):
        self.assertGreater(BM25_WEIGHT_RELATIVE_PATH, BM25_WEIGHT_CHUNK_TEXT)
        self.assertGreater(BM25_WEIGHT_SYMBOL_NAME, BM25_WEIGHT_CHUNK_TEXT)
        self.assertGreater(BM25_WEIGHT_QUALIFIED_NAME, BM25_WEIGHT_CHUNK_TEXT)


if __name__ == "__main__":
    unittest.main()
