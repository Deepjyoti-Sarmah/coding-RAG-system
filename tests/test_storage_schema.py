import unittest

from storage import db, schema

EXPECTED_TABLES = {
    "documents",
    "symbols",
    "imports",
    "exports",
    "references",
    "resolved_references",
    "resolved_imports",
    "relationships",
    "chunks",
    "embeddings",
    "embedding_jobs",
    "file_state",
    "index_metadata",
    "chunks_fts",
}


def _table_names(conn) -> set[str]:
    rows = conn.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        """
    ).fetchall()
    return {row["name"] for row in rows}


class TestSchema(unittest.TestCase):
    def test_all_tables_created(self):
        conn = db.connect(":memory:")
        schema.create_schema(conn)

        self.assertTrue(EXPECTED_TABLES.issubset(_table_names(conn)))
        conn.close()

    def test_create_schema_is_idempotent(self):
        conn = db.connect(":memory:")
        schema.create_schema(conn)
        schema.create_schema(conn)

        self.assertTrue(EXPECTED_TABLES.issubset(_table_names(conn)))
        conn.close()

    def test_schema_version_set_on_create(self):
        conn = db.connect(":memory:")
        schema.create_schema(conn)

        self.assertEqual(schema.schema_version(conn), schema.SCHEMA_VERSION)
        conn.close()

    def test_schema_version_zero_before_create(self):
        conn = db.connect(":memory:")

        self.assertEqual(schema.schema_version(conn), 0)
        conn.close()

    def test_generation_zero_before_create(self):
        conn = db.connect(":memory:")

        self.assertEqual(schema.current_generation(conn), 0)
        conn.close()

    def test_bump_generation_increments_and_persists(self):
        conn = db.connect(":memory:")
        schema.create_schema(conn)

        self.assertEqual(schema.bump_generation(conn), 1)
        self.assertEqual(schema.bump_generation(conn), 2)
        self.assertEqual(schema.current_generation(conn), 2)
        conn.close()

    def test_relationships_unique_index(self):
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
            conn.execute(
                """
                INSERT INTO symbols (
                    symbol_id, document_id, name, kind, relative_path,
                    start_line, end_line, start_byte, end_byte, content,
                    parent_symbol_id, qualified_name, content_hash,
                    signature_hash, stable_key
                ) VALUES ('sym-1', 'doc-1', 'a', 'function', 'a.ts',
                          1, 1, 0, 10, 'body', NULL, 'a',
                          'chash', 'shash', 'key')
                """
            )
            conn.execute(
                """
                INSERT INTO symbols (
                    symbol_id, document_id, name, kind, relative_path,
                    start_line, end_line, start_byte, end_byte, content,
                    parent_symbol_id, qualified_name, content_hash,
                    signature_hash, stable_key
                ) VALUES ('sym-2', 'doc-1', 'b', 'function', 'a.ts',
                          1, 1, 0, 10, 'body', NULL, 'b',
                          'chash', 'shash', 'key')
                """
            )
            conn.execute(
                """
                INSERT INTO relationships (source_symbol_id, target_symbol_id, kind)
                VALUES ('sym-1', 'sym-2', 'calls')
                """
            )
            with self.assertRaises(Exception):
                conn.execute(
                    """
                    INSERT INTO relationships (source_symbol_id, target_symbol_id, kind)
                    VALUES ('sym-1', 'sym-2', 'calls')
                    """
                )

        conn.close()


if __name__ == "__main__":
    unittest.main()
