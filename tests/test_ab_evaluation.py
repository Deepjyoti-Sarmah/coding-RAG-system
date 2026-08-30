import json
import tempfile
import unittest
from pathlib import Path

from evaluation.ab_metrics import score, summarize
from evaluation.ab_runner import FakeAgentRunner, load_tasks, run


class AbEvaluationTests(unittest.TestCase):
    def test_manifest_has_exactly_twenty_tasks(self):
        tasks = load_tasks("evaluation/tasks.json")
        self.assertEqual(len(tasks), 20)
        self.assertEqual(len({x["id"] for x in tasks}), 20)

    def test_fake_runner_scores_and_resumes(self):
        tasks = load_tasks("evaluation/tasks.json")[:2]
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            results = run(tasks, FakeAgentRunner(), ("with_ckg", "without_ckg"), out)
            self.assertEqual(len(results), 4)
            self.assertTrue(any(x["success"] for x in results))
            self.assertTrue((out / "summary.json").exists())
            resumed = run(tasks, FakeAgentRunner(), ("with_ckg", "without_ckg"), out)
            self.assertEqual(len(resumed), 4)

    def test_dry_run_does_not_invoke_runner(self):
        class Fail(FakeAgentRunner):
            def run(self, *args): raise AssertionError("invoked")
        with tempfile.TemporaryDirectory() as d:
            run(load_tasks("evaluation/tasks.json")[:1], Fail(), ("with_ckg",), Path(d), True)

    def test_scoring_requires_files_and_symbols(self):
        task = load_tasks("evaluation/tasks.json")[0]
        result = score(task, {"exit_code": 0, "files_changed": [], "symbols_found": []})
        self.assertFalse(result["success"])

    def test_metrics_do_not_fabricate_missing_tokens(self):
        summary = summarize([{"task_id":"x","language":"python","condition":"with_ckg","success":True,"elapsed_seconds":1,"total_tokens":None,"tool_calls":None}])
        self.assertIsNone(summary["all"]["tokens"]["mean"])


if __name__ == "__main__": unittest.main()
