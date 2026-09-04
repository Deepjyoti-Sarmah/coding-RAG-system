import tempfile
import unittest
from pathlib import Path

from analysis.build_graph import build_graph


class TestReExport(unittest.TestCase):
    def test_export_star_from(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.ts").write_text("export function foo() {}\n", encoding="utf-8")
            (root / "b.ts").write_text('export * from "./a";\n', encoding="utf-8")
            result = build_graph(str(root))
            docs_by_id = {d.document_id: d for d in result.documents}
            exps = [e for e in result.exports if docs_by_id[e.document_id].relative_path == "b.ts"]
            self.assertTrue(any(e.exported_name == "*" for e in exps))

    def test_export_named_from(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.ts").write_text("export function foo() {}\n", encoding="utf-8")
            (root / "b.ts").write_text('export { foo } from "./a";\n', encoding="utf-8")
            result = build_graph(str(root))
            docs_by_id = {d.document_id: d for d in result.documents}
            exps = [e for e in result.exports if docs_by_id[e.document_id].relative_path == "b.ts"]
            self.assertTrue(any(e.exported_name == "foo" for e in exps))

    def test_normal_export_still_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.ts").write_text("export function foo() {}\nexport const bar=1;\n", encoding="utf-8")
            result = build_graph(str(root))
            names = {e.exported_name for e in result.exports}
            self.assertIn("foo", names)
            self.assertIn("bar", names)


if __name__ == "__main__":
    unittest.main()
