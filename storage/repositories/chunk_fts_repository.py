from chunking.symbol_chunker import SemanticChunk
from models.entities.fts_hit import FtsHit
from models.entities.symbols import Symbol


def build_fts_query(query: str) -> str:
    terms = [f'"{term}"' for term in query.split() if term]

    if not terms:
        return ""

    return " AND ".join(terms)


def insert_many(conn, chunks: list[SemanticChunk], symbols_by_id: dict[str, Symbol]) -> None:
    rows = []

    for chunk in chunks:
        symbol = symbols_by_id.get(chunk.symbol_id)

        if symbol is None:
            continue

        rows.append(
            (
                chunk.chunk_key,
                symbol.name,
                symbol.qualified_name,
                chunk.relative_path,
                chunk.embedding_text,
            )
        )

    conn.executemany(
        """
        INSERT INTO chunks_fts (
            chunk_id, symbol_name, qualified_name, relative_path, chunk_text
        ) VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )


def search(conn, query: str, *, limit: int = 10) -> list[FtsHit]:
    fts_query = build_fts_query(query)

    if not fts_query:
        return []

    rows = conn.execute(
        """
        SELECT chunk_id, symbol_name, qualified_name, relative_path,
               bm25(chunks_fts) AS score
        FROM chunks_fts
        WHERE chunks_fts MATCH ?
        ORDER BY score
        LIMIT ?
        """,
        (fts_query, limit),
    ).fetchall()

    return [
        FtsHit(
            chunk_key=row["chunk_id"],
            symbol_name=row["symbol_name"],
            qualified_name=row["qualified_name"],
            relative_path=row["relative_path"],
            score=row["score"],
        )
        for row in rows
    ]