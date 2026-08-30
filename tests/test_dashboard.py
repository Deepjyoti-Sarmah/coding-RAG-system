import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from ckg.dashboard.server import create_server
from session_memory import SessionService


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name)
        self.server = create_server(str(self.project), port=0)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown(); self.thread.join(timeout=3); self.server.server_close(); self.tmp.cleanup()

    def get(self, path):
        with urllib.request.urlopen(self.base + path) as response:
            return response.status, json.loads(response.read()) if "json" in response.headers["Content-Type"] else response.read().decode()

    def test_health_empty_and_html(self):
        status, health = self.get("/api/health")
        self.assertEqual(status, 200); self.assertFalse(health["index_present"])
        status, page = self.get("/"); self.assertEqual(status, 200); self.assertIn("CKG Dashboard", page)

    def test_session_detail_search_and_safe_paths(self):
        service = SessionService(str(self.project)); session = service.start()
        service.decision("<script>alert(1)</script>", "local decision")
        service.code_area("auth.py", "authentication")
        service.retrieval("auth", ["auth.py:login"], 0, 0, 1)
        _, sessions = self.get("/api/sessions")
        self.assertEqual(sessions["sessions"][0]["id"], session["id"])
        _, detail = self.get("/api/sessions/" + session["id"])
        self.assertEqual(len(detail["decisions"]), 1)
        _, status = self.get("/api/status"); self.assertIsNone(status["savings_percentage"])
        with self.assertRaises(urllib.error.HTTPError): self.get("/api/sessions/../service.py")


if __name__ == "__main__": unittest.main()
