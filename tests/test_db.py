import sqlite3
import tempfile
import unittest
from pathlib import Path

from storage import db, schema


class TestDatabaseConnection(unittest.TestCase):
    def test_connect_sets_pragmas(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "index.sqlite")

            conn = db.connect(db_path)

            try:
                journal_mode = conn.execute(
                    "PRAGMA journal_mode"
                ).fetchone()[0]
                foreign_keys = conn.execute(
                    "PRAGMA foreign_keys"
                ).fetchone()[0]
                busy_timeout = conn.execute(
                    "PRAGMA busy_timeout"
                ).fetchone()[0]

                self.assertEqual(journal_mode, "wal")
                self.assertEqual(foreign_keys, 1)
                self.assertEqual(busy_timeout, db.BUSY_TIMEOUT_MS)
            finally:
                conn.close()

    def test_transaction_commits_on_success(self):
        conn = db.connect(":memory:")
        schema.create_schema(conn)

        with db.transaction(conn):
            conn.execute(
                "INSERT INTO index_metadata (key, value) VALUES ('probe', '1')"
            )

        row = conn.execute(
            "SELECT value FROM index_metadata WHERE key = 'probe'"
        ).fetchone()
        self.assertEqual(row["value"], "1")
        conn.close()

    def test_transaction_rolls_back_on_error(self):
        conn = db.connect(":memory:")
        schema.create_schema(conn)

        with self.assertRaises(RuntimeError):
            with db.transaction(conn):
                conn.execute(
                    "INSERT INTO index_metadata (key, value) VALUES ('probe', '1')"
                )
                raise RuntimeError("boom")

        count = conn.execute(
            "SELECT COUNT(*) FROM index_metadata WHERE key = 'probe'"
        ).fetchone()[0]
        self.assertEqual(count, 0)
        conn.close()

    def test_foreign_keys_enforced(self):
        conn = db.connect(":memory:")
        schema.create_schema(conn)

        with db.transaction(conn):
            conn.execute(
                """
                INSERT INTO documents (
                    document_id, absolute_path, relative_path, file_name,
                    extension, language, size_bytes, line_count, content, file_hash
                ) VALUES ('doc-1', '/a.ts', 'a.ts', 'a.ts', '.ts', 'typescript',
                          10, 1, 'content', 'hash')
                """
            )
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    """
                    INSERT INTO symbols (
                        symbol_id, document_id, name, kind, relative_path,
                        start_line, end_line, start_byte, end_byte, content,
                        parent_symbol_id, qualified_name, content_hash,
                        signature_hash, stable_key
                    ) VALUES ('sym-1', 'missing-doc', 'login', 'function', 'a.ts',
                              1, 1, 0, 10, 'body', NULL, 'login',
                              'chash', 'shash', 'key')
                    """
                )

        conn.close()


if __name__ == "__main__":
    unittest.main()
