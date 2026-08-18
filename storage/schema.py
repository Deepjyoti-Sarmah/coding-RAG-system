import sqlite3

SCHEMA_VERSION = 2

TABLES = [
    """
    CREATE TABLE IF NOT EXISTS documents (
        document_id   TEXT PRIMARY KEY,
        absolute_path TEXT NOT NULL,
        relative_path TEXT NOT NULL,
        file_name     TEXT NOT NULL,
        extension     TEXT NOT NULL,
        language      TEXT NOT NULL,
        size_bytes    INTEGER NOT NULL,
        line_count    INTEGER NOT NULL,
        content       TEXT NOT NULL,
        file_hash     TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS symbols (
        symbol_id        TEXT PRIMARY KEY,
        document_id      TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
        name             TEXT NOT NULL,
        kind             TEXT NOT NULL,
        relative_path    TEXT NOT NULL,
        start_line       INTEGER NOT NULL,
        end_line         INTEGER NOT NULL,
        start_byte       INTEGER NOT NULL,
        end_byte         INTEGER NOT NULL,
        content          TEXT NOT NULL,
        parent_symbol_id TEXT REFERENCES symbols(symbol_id) ON DELETE CASCADE,
        qualified_name   TEXT NOT NULL,
        content_hash     TEXT NOT NULL,
        signature_hash   TEXT NOT NULL,
        stable_key       TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS imports (
        import_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id   TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
        module_path   TEXT NOT NULL,
        imported_name TEXT NOT NULL,
        local_name    TEXT NOT NULL,
        start_line    INTEGER NOT NULL,
        end_line      INTEGER NOT NULL,
        start_byte    INTEGER NOT NULL,
        end_byte      INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS exports (
        export_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id   TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
        exported_name TEXT NOT NULL,
        symbol_name   TEXT,
        start_line    INTEGER NOT NULL,
        end_line      INTEGER NOT NULL,
        start_byte    INTEGER NOT NULL,
        end_byte      INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS "references" (
        reference_id    TEXT PRIMARY KEY,
        document_id     TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
        name            TEXT NOT NULL,
        kind            TEXT NOT NULL,
        owner_symbol_id TEXT REFERENCES symbols(symbol_id) ON DELETE CASCADE,
        path_json       TEXT NOT NULL,
        start_line      INTEGER NOT NULL,
        end_line        INTEGER NOT NULL,
        start_byte      INTEGER NOT NULL,
        end_byte        INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS resolved_references (
        reference_id     TEXT PRIMARY KEY REFERENCES "references"(reference_id) ON DELETE CASCADE,
        status           TEXT NOT NULL,
        target_symbol_id TEXT REFERENCES symbols(symbol_id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS resolved_imports (
        import_id          INTEGER PRIMARY KEY REFERENCES imports(import_id) ON DELETE CASCADE,
        target_document_id TEXT REFERENCES documents(document_id) ON DELETE CASCADE,
        target_symbol_id   TEXT REFERENCES symbols(symbol_id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS relationships (
        relationship_id  INTEGER PRIMARY KEY AUTOINCREMENT,
        source_symbol_id TEXT NOT NULL REFERENCES symbols(symbol_id) ON DELETE CASCADE,
        target_symbol_id TEXT NOT NULL REFERENCES symbols(symbol_id) ON DELETE CASCADE,
        kind             TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS chunks (
        chunk_id       TEXT PRIMARY KEY,
        symbol_id      TEXT NOT NULL REFERENCES symbols(symbol_id) ON DELETE CASCADE,
        relative_path  TEXT NOT NULL,
        embedding_text TEXT NOT NULL,
        display_text   TEXT NOT NULL,
        content_hash   TEXT NOT NULL,
        chunk_version  TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS embeddings (
        chunk_id  TEXT PRIMARY KEY REFERENCES chunks(chunk_id) ON DELETE CASCADE,
        embedding BLOB NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS file_state (
        relative_path   TEXT PRIMARY KEY,
        file_hash       TEXT NOT NULL,
        size_bytes      INTEGER NOT NULL,
        mtime_ns        INTEGER NOT NULL,
        last_indexed_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS index_metadata (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """,
    """
    CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
        chunk_id UNINDEXED,
        symbol_name,
        qualified_name,
        relative_path,
        chunk_text,
        tokenize = 'porter unicode61'
    )
    """,
]

INDEXES = [
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_relative_path ON documents(relative_path)",
    "CREATE INDEX IF NOT EXISTS idx_symbols_document ON symbols(document_id)",
    "CREATE INDEX IF NOT EXISTS idx_symbols_stable_key ON symbols(stable_key)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_relationships_unique ON relationships(source_symbol_id, target_symbol_id, kind)",
]


def create_schema(conn) -> None:
    for statement in [*TABLES, *INDEXES]:
        conn.execute(statement)
    set_schema_version(conn, SCHEMA_VERSION)


def schema_version(conn) -> int:
    try:
        row = conn.execute(
            "SELECT value FROM index_metadata WHERE key = 'schema_version'"
        ).fetchone()
    except sqlite3.OperationalError:
        return 0

    return int(row["value"]) if row is not None else 0


def set_schema_version(conn, version: int) -> None:
    conn.execute(
        """
        INSERT INTO index_metadata (key, value) VALUES ('schema_version', ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (str(version),),
    )
