import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from indexing.indexer import reindex_index
from symbolgraph.cli import default_db_path


class TestFallbackChunking(unittest.TestCase):
    def test_html_module_chunk(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "a.html").write_text("<html>hello world unique123</html>")
            db = default_db_path(tmp)
            report = reindex_index(db, tmp)
            self.assertGreater(report.parsed_files, 0)
            # check chunks contain a.html
            import sqlite3
            with closing(sqlite3.connect(db)) as conn:
                rows = conn.execute("SELECT relative_path FROM chunks WHERE relative_path='a.html'").fetchall()
                self.assertGreater(len(rows), 0)

    def test_md_non_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "notes.md").write_text("# Title\nhello md content")
            db = default_db_path(tmp)
            reindex_index(db, tmp)
            import sqlite3
            with closing(sqlite3.connect(db)) as conn:
                rows = conn.execute("SELECT relative_path FROM chunks WHERE relative_path='notes.md'").fetchall()
                self.assertGreater(len(rows), 0)

    def test_empty_no_chunk(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "empty.md").write_text("")
            db = default_db_path(tmp)
            reindex_index(db, tmp)
            import sqlite3
            with closing(sqlite3.connect(db)) as conn:
                rows = conn.execute("SELECT relative_path FROM chunks WHERE relative_path='empty.md'").fetchall()
                self.assertEqual(len(rows), 0)
