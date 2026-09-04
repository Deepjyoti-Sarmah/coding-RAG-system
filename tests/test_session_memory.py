import json
import shutil
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from session_memory import SessionService


class SessionMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name) / "project"
        shutil.copytree(Path("tests/fixtures/session_repo"), self.project)

    def tearDown(self):
        self.tmp.cleanup()

    def test_lifecycle_recall_persistence_and_export(self):
        service = SessionService(str(self.project))
        session = service.start()
        self.assertEqual(session["id"], service.start()["id"])
        decision = service.decision("Use local session memory", "resume work safely")
        service.code_area("python_app/auth.py", "token validation and login")
        service.retrieval("authentication", ["python_app/auth.py:login"], 40, 100, 2.5)
        self.assertTrue(service.recall("local session")[0]["id"] == decision["id"])
        timeline = service.timeline(session["id"])
        self.assertEqual(timeline, sorted(timeline, key=lambda x: (x["timestamp"], x["id"])))
        service.end(session["id"])
        reopened = SessionService(str(self.project))
        self.assertEqual(reopened.status(session["id"])["status"], "completed")
        self.assertIn("authentication", reopened.export(session["id"], "markdown"))
        self.assertEqual(json.loads(reopened.export(session["id"]))["session"]["id"], session["id"])

    def test_isolation_limits_and_prune(self):
        other = Path(self.tmp.name) / "other"
        other.mkdir()
        first = SessionService(str(self.project)); second = SessionService(str(other))
        first.decision("A" * 5000, "B" * 5000)
        second.decision("private other project")
        self.assertFalse(first.recall("private other"))
        with closing(sqlite3.connect(first.db_path)) as conn:
            row = conn.execute("select decision, reason from decisions").fetchone()
            self.assertLessEqual(len(row[0]), 2000); self.assertLessEqual(len(row[1]), 2000)
        self.assertEqual(first.prune(9999)["sessions"], 0)

    def test_invalid_session_is_rejected(self):
        with self.assertRaises(ValueError):
            SessionService(str(self.project)).decision("x", session_id="missing")


if __name__ == "__main__":
    unittest.main()
