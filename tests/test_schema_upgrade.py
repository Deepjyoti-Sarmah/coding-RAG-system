"""Upgrading an older index rebuilds it rather than migrating it.

The index is derived state, so `create_schema` drops and recreates when it
finds an older `schema_version`. The hazard is `chunks_fts`: an FTS5 virtual
table keeps shadow tables (`chunks_fts_data`, `chunks_fts_idx`, ...) that show
up as ordinary tables and must never be dropped directly.
"""

import tempfile
import unittest
from pathlib import Path

from analysis.build_graph import build_graph
from storage.db import connect
from storage.index_store import load_index, persist_index
from storage.schema import (
    SCHEMA_VERSION,
    create_schema,
    schema_version,
    set_schema_version,
    table_names,
)

SOURCE = {
    "auth.ts": (
        "export function createAuth() { return 1; }\n"
        "export function login() { return createAuth(); }\n"
    )
}


class TestSchemaUpgrade(unittest.TestCase):
    def test_table_names_covers_every_declared_table(self):
        names = table_names()

        self.assertIn("documents", names)
        self.assertIn("relationships", names)
        self.assertIn("chunks_fts", names)
        self.assertNotIn("chunks_fts_data", names)

    def test_older_index_is_dropped_and_rebuilt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, content in SOURCE.items():
                (root / name).write_text(content, encoding="utf-8")

            db_path = str(root / "index.sqlite")
            persist_index(db_path, build_graph(str(root)))

            # An FTS5 table with rows in it is the case that breaks a naive
            # sqlite_master sweep, so assert we actually have one.
            conn = connect(db_path)
            try:
                populated = conn.execute(
                    "SELECT count(*) AS n FROM chunks_fts"
                ).fetchone()["n"]
                self.assertGreater(populated, 0)

                shadow = conn.execute(
                    "SELECT count(*) AS n FROM sqlite_master "
                    "WHERE name LIKE 'chunks_fts_%'"
                ).fetchone()["n"]
                self.assertGreater(shadow, 0)

                set_schema_version(conn, SCHEMA_VERSION - 1)
            finally:
                conn.close()

            # Reopening must wipe the stale index without erroring on shadows.
            conn = connect(db_path)
            try:
                create_schema(conn)

                self.assertEqual(schema_version(conn), SCHEMA_VERSION)

                # Every declared table, not just the obvious ones: `references`
                # is quoted in the DDL and was missed by an earlier version of
                # `table_names`, so it survived the drop with its rows intact.
                for name in table_names():
                    if name == "index_metadata":
                        continue

                    surviving = conn.execute(
                        f'SELECT count(*) AS n FROM "{name}"'
                    ).fetchone()["n"]
                    self.assertEqual(surviving, 0, f"{name} was not dropped")
            finally:
                conn.close()

            # And the emptied index is usable again.
            persist_index(db_path, build_graph(str(root)))
            reloaded = load_index(db_path)

        self.assertTrue(reloaded.symbols)

    def test_matching_version_leaves_the_index_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, content in SOURCE.items():
                (root / name).write_text(content, encoding="utf-8")

            db_path = str(root / "index.sqlite")
            persist_index(db_path, build_graph(str(root)))

            conn = connect(db_path)
            try:
                create_schema(conn)
                surviving = conn.execute(
                    "SELECT count(*) AS n FROM documents"
                ).fetchone()["n"]
            finally:
                conn.close()

        self.assertEqual(surviving, 1)


if __name__ == "__main__":
    unittest.main()
