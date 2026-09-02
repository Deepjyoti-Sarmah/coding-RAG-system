import unittest

from evaluation.metrics import (
    accuracy,
    mean,
    recall_at_k,
    reciprocal_rank,
    token_reduction,
)


class TestRecallAtK(unittest.TestCase):
    def test_empty_expected_is_trivially_perfect(self):
        self.assertEqual(recall_at_k(frozenset(), ["a", "b"], 5), 1.0)

    def test_all_expected_found_in_top_k(self):
        self.assertEqual(
            recall_at_k(frozenset({"a", "b"}), ["a", "b", "c"], 5), 1.0
        )

    def test_partial_match(self):
        self.assertEqual(
            recall_at_k(frozenset({"a", "b"}), ["a", "c", "d"], 5), 0.5
        )

    def test_k_limits_the_window(self):
        self.assertEqual(
            recall_at_k(frozenset({"a"}), ["b", "c", "a"], 2), 0.0
        )

    def test_no_match(self):
        self.assertEqual(recall_at_k(frozenset({"z"}), ["a", "b"], 5), 0.0)


class TestReciprocalRank(unittest.TestCase):
    def test_first_position_is_rank_one(self):
        self.assertEqual(reciprocal_rank(frozenset({"a"}), ["a", "b"]), 1.0)

    def test_second_position_is_half(self):
        self.assertEqual(reciprocal_rank(frozenset({"b"}), ["a", "b"]), 0.5)

    def test_no_match_is_zero(self):
        self.assertEqual(reciprocal_rank(frozenset({"z"}), ["a", "b"]), 0.0)

    def test_uses_first_matching_position(self):
        self.assertEqual(
            reciprocal_rank(frozenset({"a", "b"}), ["c", "b", "a"]), 0.5
        )


class TestMean(unittest.TestCase):
    def test_mean_of_values(self):
        self.assertEqual(mean([1.0, 2.0, 3.0]), 2.0)

    def test_empty_is_zero(self):
        self.assertEqual(mean([]), 0.0)


class TestTokenReduction(unittest.TestCase):
    def test_reduction_fraction(self):
        self.assertEqual(token_reduction(50, 200), 0.75)

    def test_no_reduction(self):
        self.assertEqual(token_reduction(200, 200), 0.0)

    def test_zero_baseline_is_zero(self):
        self.assertEqual(token_reduction(10, 0), 0.0)

    def test_negative_reduction_when_context_exceeds_baseline(self):
        # token_reduction can be negative — caller must not clip it
        self.assertAlmostEqual(token_reduction(300, 200), -0.5)
        self.assertAlmostEqual(token_reduction(250, 100), -1.5)

    def test_negative_baseline_is_zero(self):
        self.assertEqual(token_reduction(10, -5), 0.0)


class TestAccuracy(unittest.TestCase):
    def test_all_correct(self):
        self.assertEqual(accuracy([True, True]), 1.0)

    def test_partial(self):
        self.assertEqual(accuracy([True, False]), 0.5)

    def test_empty_is_trivially_perfect(self):
        self.assertEqual(accuracy([]), 1.0)


class TestRetrievalGate(unittest.TestCase):
    def test_gate_definition_recall(self):
        # Gate: FTS+graph without vectors must keep 0.83/0.78 fixture baseline ckg/cli.py:295
        from evaluation.runner import run_evaluation

        report = run_evaluation(provider=None, top_k=5)
        self.assertGreaterEqual(report.definition_accuracy, 0.83)
        self.assertGreaterEqual(report.mean_recall_at_k, 0.5)


if __name__ == "__main__":
    unittest.main()
