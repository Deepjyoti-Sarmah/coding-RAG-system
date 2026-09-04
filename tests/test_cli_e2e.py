import tempfile
import unittest
from pathlib import Path

from ckg.cli import cmd_context, cmd_index, cmd_search, cmd_status, default_db_path


class TestCliE2E(unittest.TestCase):
    def test_golden_e2e(self):
        # golden: index evaluation_repo -> search + context + status
        repo = Path("tests/fixtures/evaluation_repo")
        if not repo.exists():
            self.skipTest("evaluation_repo not present")
        with tempfile.TemporaryDirectory() as tmp:
            import shutil
            # copy repo to tmp
            dst = Path(tmp) / "repo"
            shutil.copytree(repo, dst)
            db = default_db_path(str(dst))
            report = cmd_index(str(dst), db)
            self.assertGreater(report.parsed_files, 0)
            status = cmd_status(db)
            self.assertGreater(status["symbols"], 0)
            self.assertIn("chunks", status)
            # search
            ret = cmd_search(db, "login", top_k=3)
            self.assertGreater(len(ret.candidates), 0)
            # context budget
            pack = cmd_context(db, "how does login work?", token_budget=800, top_k=3)
            self.assertLessEqual(pack.total_tokens, 800)
            self.assertGreater(len(pack.primary_definitions) + len(pack.supporting_definitions), 0)
            # oneline status
            self.assertIn("generation", status)
