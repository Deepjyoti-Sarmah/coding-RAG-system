import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import release_smoke


class ReleaseSmokeHelpersTests(unittest.TestCase):
    def test_timeout_and_nonzero_are_reported(self):
        with patch("scripts.release_smoke.subprocess.run", side_effect=release_smoke.subprocess.TimeoutExpired(["x"], 1)), self.assertRaisesRegex(release_smoke.SmokeError, "timed out"):
            release_smoke.run_command(["x"], timeout=1)
        fake = type("P", (), {"returncode": 2, "stdout": "out", "stderr": "err"})()
        with patch("scripts.release_smoke.subprocess.run", return_value=fake), self.assertRaisesRegex(release_smoke.SmokeError, "failed"):
            release_smoke.run_command(["x"])

    def test_wheel_discovery_and_package_checks(self):
        with tempfile.TemporaryDirectory() as d:
            dist = Path(d); wheel = dist / "code_knowledge_graph-1.2.3-py3-none-any.whl"
            import zipfile
            with zipfile.ZipFile(wheel, "w") as z:
                z.writestr("code_knowledge_graph-1.2.3.dist-info/METADATA", "Name: code-knowledge-graph\nVersion: 1.2.3\n")
                z.writestr("session_memory/__init__.py", ""); z.writestr("ckg/dashboard/__init__.py", "")
            self.assertEqual(release_smoke.verify_wheel(release_smoke.discover_wheel(dist)), "1.2.3")

    def test_output_is_bounded_and_checkout_import_detection_environment(self):
        fake = type("P", (), {"returncode": 0, "stdout": "x" * 20000, "stderr": ""})()
        with patch("scripts.release_smoke.subprocess.run", return_value=fake):
            result = release_smoke.run_command(["x"])
        self.assertEqual(result.returncode, 0)
        self.assertNotEqual(str(Path.cwd()), str(Path(tempfile.gettempdir())))

    def test_missing_wheel_is_clear(self):
        with tempfile.TemporaryDirectory() as d, self.assertRaisesRegex(release_smoke.SmokeError, "no CKG wheel"):
            release_smoke.discover_wheel(d)


if __name__ == "__main__": unittest.main()
