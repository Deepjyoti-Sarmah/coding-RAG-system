import unittest

from embeddings.fake_provider import FakeEmbeddingProvider
from evaluation.benchmark import BENCHMARK_QUESTIONS, CALLEES, CALLERS, DEFINITION, IMPORTERS
from evaluation.runner import run_evaluation


class TestEvaluationRunnerWithoutProvider(unittest.TestCase):
    """FTS + exact + graph only - no embedding worker, no model loaded."""

    @classmethod
    def setUpClass(cls):
        cls.report = run_evaluation(provider=None)

    def test_every_question_answered(self):
        self.assertEqual(
            {q.question_id for q in self.report.questions},
            {q.id for q in BENCHMARK_QUESTIONS},
        )

    def test_deterministic_ground_truth_is_fully_correct_on_the_fixture(self):
        self.assertEqual(self.report.definition_accuracy, 1.0)
        self.assertEqual(self.report.relationship_accuracy, 1.0)
        self.assertEqual(self.report.import_resolution_accuracy, 1.0)

    def test_structural_questions_have_a_deterministic_correct_flag(self):
        by_kind = {q.kind: q for q in self.report.questions}

        for kind in (DEFINITION, CALLERS, CALLEES, IMPORTERS):
            self.assertIsNotNone(by_kind[kind].correct)

    def test_semantic_questions_have_no_deterministic_ground_truth(self):
        semantic = [q for q in self.report.questions if q.category == "semantic"]

        self.assertTrue(semantic)
        for question in semantic:
            self.assertIsNone(question.correct)

    def test_context_respects_reported_baseline_relationship(self):
        self.assertGreater(self.report.baseline_tokens, 0)
        self.assertGreaterEqual(self.report.context_tokens, 0)

    def test_embedding_cache_hit_rate_is_zero_without_a_worker_run(self):
        self.assertEqual(self.report.embedding_cache_hit_rate, 0.0)

    def test_indexing_latency_is_measured_and_non_negative(self):
        self.assertGreaterEqual(self.report.initial_indexing_seconds, 0.0)
        self.assertGreaterEqual(self.report.incremental_indexing_seconds, 0.0)

    def test_recall_and_mrr_are_bounded(self):
        self.assertGreaterEqual(self.report.mean_recall_at_k, 0.0)
        self.assertLessEqual(self.report.mean_recall_at_k, 1.0)
        self.assertGreaterEqual(self.report.mean_reciprocal_rank, 0.0)
        self.assertLessEqual(self.report.mean_reciprocal_rank, 1.0)


class TestEvaluationRunnerWithProvider(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_evaluation(provider=FakeEmbeddingProvider(dimension=8))

    def test_structural_recall_and_mrr_are_perfect_on_the_fixture(self):
        by_id = {q.question_id: q for q in self.report.questions}

        for question_id in ("def-createAuth", "callers-login", "callees-login"):
            self.assertEqual(by_id[question_id].recall_at_k, 1.0)
            self.assertEqual(by_id[question_id].reciprocal_rank, 1.0)

    def test_deterministic_ground_truth_is_unaffected_by_vector_search(self):
        self.assertEqual(self.report.definition_accuracy, 1.0)
        self.assertEqual(self.report.relationship_accuracy, 1.0)
        self.assertEqual(self.report.import_resolution_accuracy, 1.0)

    def test_embedding_cache_hit_rate_is_high_after_a_single_symbol_edit(self):
        # Only the edited symbol's chunk should need re-embedding; every
        # other chunk in the fixture should be an "already DONE" hit.
        self.assertGreater(self.report.embedding_cache_hit_rate, 0.5)
        self.assertLess(self.report.embedding_cache_hit_rate, 1.0)

    def test_fixture_repo_is_left_unmodified(self):
        from pathlib import Path

        from evaluation.benchmark import BENCHMARK_REPO

        content = (Path(BENCHMARK_REPO) / "token.ts").read_text(encoding="utf-8")
        self.assertIn("token.length > 0", content)
        self.assertNotIn("token.length > 1", content)


if __name__ == "__main__":
    unittest.main()
