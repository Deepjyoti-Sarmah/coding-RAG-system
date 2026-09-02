import tempfile
import unittest
from pathlib import Path

from indexing.git_hooks import install_hooks, uninstall_hooks


class TestGitHooks(unittest.TestCase):
    def test_install_creates_hooks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # init git repo
            import subprocess

            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            installed = install_hooks(root)
            self.assertEqual(len(installed), 3)
            for name in ("post-commit", "post-checkout", "post-merge"):
                self.assertTrue((root / ".git" / "hooks" / name).exists())
                self.assertIn("CKG keep-fresh", (root / ".git" / "hooks" / name).read_text())

    def test_uninstall_removes_hooks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            import subprocess

            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            install_hooks(root)
            removed = uninstall_hooks(root)
            self.assertEqual(len(removed), 3)
            for name in ("post-commit", "post-checkout", "post-merge"):
                self.assertFalse((root / ".git" / "hooks" / name).exists())

    def test_worktree_respected(self):
        # install should handle non-git dir gracefully
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            installed = install_hooks(root)
            self.assertEqual(installed, [])
