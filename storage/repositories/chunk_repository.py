from chunking.symbol_chunker import CHUNK_VERSION, SemanticChunk


def insert_many(conn, chunks: list[SemanticChunk]) -> None:
    conn.executemany(
        """
        INSERT INTO chunks (
            chunk_id, symbol_id, relative_path, embedding_text,
            display_text, content_hash, chunk_version
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                chunk.chunk_key,
                chunk.symbol_id,
                chunk.relative_path,
                chunk.embedding_text,
                chunk.display_text,
                chunk.content_hash,
                chunk.chunk_version,
            )
            for chunk in chunks
        ],
    )


def fetch_all(conn) -> list[SemanticChunk]:
    rows = conn.execute(
        """
        SELECT chunk_id, symbol_id, relative_path, embedding_text,
               display_text, content_hash, chunk_version
        FROM chunks
        """
    ).fetchall()

    return [
        SemanticChunk(
            chunk_key=row["chunk_id"],
            symbol_id=row["symbol_id"],
            relative_path=row["relative_path"],
            embedding_text=row["embedding_text"],
            display_text=row["display_text"],
            content_hash=row["content_hash"],
            chunk_version=row["chunk_version"] or CHUNK_VERSION,
        )
        for row in rows
    ]
