import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from evaluation.ab_metrics import score, summarize
from evaluation.ab_runner import FakeAgentRunner, SubprocessAgentRunner, _provision_ckg, _validate_condition, load_tasks, parse_result, run


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

    def test_result_protocol_validation_and_nullable_metrics(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "result.json"
            path.write_text(json.dumps({"status":"failure", "changed_files":[], "symbols_found":[], "input_tokens":None, "output_tokens":None, "total_tokens":None, "tool_calls":None}))
            self.assertIsNone(parse_result(path)["total_tokens"])
            path.write_text("not json")
            with self.assertRaises(ValueError): parse_result(path)
            path.write_text(json.dumps({"status":"success", "changed_files":[], "symbols_found":[], "input_tokens":-1}))
            with self.assertRaises(ValueError): parse_result(path)

    def test_missing_result_and_timeout_are_explicit(self):
        task = load_tasks("evaluation/tasks.json")[0]
        with tempfile.TemporaryDirectory() as d:
            result = SubprocessAgentRunner("true").run(task, "without_ckg", Path(d))
            self.assertIn("result file", result["failure_reason"])

    def test_ckg_provisioning_is_standard_and_external(self):
        with tempfile.TemporaryDirectory() as d:
            work = Path(d) / "repo"
            import shutil
            shutil.copytree("tests/fixtures/session_repo", work)
            index, config = _provision_ckg(work)
            self.assertTrue(index.exists())
            self.assertEqual(json.loads(config.read_text()), {"mcpServers": {"ckg": {"command": "ckg-mcp"}}})

    def test_pilot_selects_exactly_python_and_javascript(self):
        tasks = load_tasks("evaluation/tasks.json")
        selected = [next(x for x in tasks if x["language"] == language) for language in ("python", "javascript")]
        self.assertEqual(len(selected), 2)

    def test_provision_failure_is_infrastructure_failure_and_skips_agent(self):
        class Agent(FakeAgentRunner):
            called = False
            def run(self, *args): self.called = True; return super().run(*args)
        agent = Agent()
        with tempfile.TemporaryDirectory() as d, patch("evaluation.ab_runner._provision_ckg", side_effect=RuntimeError("bad index")):
            result = run(load_tasks("evaluation/tasks.json")[:1], agent, ("with_ckg",), Path(d))[0]
        self.assertFalse(agent.called); self.assertTrue(result["infrastructure_failure"]); self.assertFalse(result["success"]); self.assertFalse(result["ckg_retrieval"]["enabled"])

    def test_without_ckg_validation_and_malformed_config_fail(self):
        with tempfile.TemporaryDirectory() as d:
            work=Path(d); _validate_condition(work,"without_ckg")
            (work/".mcp.json").write_text("{")
            with self.assertRaises(ValueError): _validate_condition(work,"with_ckg")


if __name__ == "__main__": unittest.main()
