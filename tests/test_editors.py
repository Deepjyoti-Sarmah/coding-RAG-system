import tempfile
import unittest
from pathlib import Path
import json

from ckg.editors import EDITORS, atomic_write_text, detect_editors
from ckg.cli import cmd_init, _ensure_mcp_entry


class TestEditors(unittest.TestCase):
    def test_editors_has_8(self):
        self.assertGreaterEqual(len(EDITORS), 8)

    def test_atomic_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "a.json"
            atomic_write_text(p, '{"a":1}')
            self.assertEqual(p.read_text(), '{"a":1}')

    def test_detect_auto(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vscode").mkdir()
            self.assertIn("vscode", detect_editors(root))

    def test_ensure_mcp_entry_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / ".mcp.json"
            p.write_text(json.dumps({"mcpServers": {"ckg": {"command": "ckg-mcp"}}}))
            self.assertEqual(_ensure_mcp_entry(p, "mcpServers"), "already configured")

    def test_ensure_mcp_entry_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / ".mcp.json"
            p.write_text("not json")
            with self.assertRaises(ValueError):
                _ensure_mcp_entry(p, "mcpServers")

    def test_init_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vscode").mkdir()
            (root / ".cursor").mkdir()
            (root / "opencode.json").write_text("{}")
            results = cmd_init(str(root), agents=["all"])
            self.assertIn(str(root / ".mcp.json"), results)
            self.assertIn(str(root / ".vscode/mcp.json"), results)

    def test_init_auto(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = cmd_init(str(root), agents=["auto"])
            self.assertIn(str(root / ".mcp.json"), results)

    def test_init_pi(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = cmd_init(str(root), agents=["pi"])
            self.assertTrue((root / "AGENTS.md").exists())

    def test_toml_escape(self):
        from ckg.editors import toml_escape, project_storage_slug, ensure_block_content
        self.assertEqual(toml_escape('a\\b"c'), 'a\\\\b\\"c')
        self.assertIn("-", project_storage_slug("/tmp/foo\\bar"))
        content, already = ensure_block_content("")
        self.assertFalse(already)
        self.assertIn("ckg-block-version", content)
        content2, already2 = ensure_block_content(content)
        self.assertTrue(already2)
        # legacy upgrade
        old = "<!-- CKG MCP: ckg-mcp -->\nhello"
        new, _ = ensure_block_content(old)
        self.assertIn("ckg-block-version", new)
