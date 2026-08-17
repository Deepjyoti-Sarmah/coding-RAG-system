import tempfile
import unittest
from pathlib import Path

from models.file_state import FileState
from storage import db
from storage import schema
from storage.index_store import load_file_states
from storage.repositories import file_state_repository


class TestFileStateRepository(unittest.TestCase):
    def test_round_trip_preserves_all_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "index.sqlite")
            conn = db.connect(db_path)

            try:
                schema.create_schema(conn)

                states = [
                    FileState(
                        relative_path="a.ts",
                        file_hash="h1",
                        size_bytes=10,
                        mtime_ns=123,
                        last_indexed_at="t1",
                    ),
                    FileState(
                        relative_path="src/b.ts",
                        file_hash="h2",
                        size_bytes=20,
                        mtime_ns=456,
                        last_indexed_at="t2",
                    ),
                ]

                file_state_repository.insert_many(conn, states)
                loaded = file_state_repository.fetch_all(conn)
            finally:
                conn.close()

            by_path = {state.relative_path: state for state in loaded}

            self.assertEqual(
                set(by_path),
                {"a.ts", "src/b.ts"},
            )
            self.assertEqual(by_path["a.ts"].file_hash, "h1")
            self.assertEqual(by_path["a.ts"].size_bytes, 10)
            self.assertEqual(by_path["a.ts"].mtime_ns, 123)
            self.assertEqual(by_path["a.ts"].last_indexed_at, "t1")
            self.assertEqual(by_path["src/b.ts"].mtime_ns, 456)

    def test_insert_replaces_previous_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "index.sqlite")
            conn = db.connect(db_path)

            try:
                schema.create_schema(conn)

                file_state_repository.insert_many(
                    conn,
                    [
                        FileState(
                            relative_path="a.ts",
                            file_hash="old",
                            size_bytes=1,
                            mtime_ns=1,
                            last_indexed_at="t1",
                        )
                    ],
                )
                file_state_repository.insert_many(
                    conn,
                    [
                        FileState(
                            relative_path="a.ts",
                            file_hash="new",
                            size_bytes=2,
                            mtime_ns=2,
                            last_indexed_at="t2",
                        )
                    ],
                )

                loaded = file_state_repository.fetch_all(conn)
            finally:
                conn.close()

            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].file_hash, "new")

    def test_load_file_states_creates_schema_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "index.sqlite")
            self.assertEqual(load_file_states(db_path), [])


if __name__ == "__main__":
    unittest.main()