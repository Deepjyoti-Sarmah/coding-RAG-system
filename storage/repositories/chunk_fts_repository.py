from chunking.symbol_chunker import SemanticChunk
from models.common.tokens import STOPWORDS, TOKEN_PATTERN, split_identifier
from models.entities.fts_hit import FtsHit
from models.entities.symbols import Symbol


def build_fts_query(query: str) -> str:
    raw_terms = TOKEN_PATTERN.findall(query)
    if not raw_terms:
        return ""
    # Drop stopwords case-insensitive, fallback to unfiltered if all are stopwords
    filtered = [t for t in raw_terms if t.lower() not in STOPWORDS]
    terms_to_use = filtered if filtered else raw_terms

    expanded = []
    seen = set()
    for term in terms_to_use:
        candidates = [term] + [
            word
            for word in split_identifier(term).split()
            if word != term and len(word) >= 2 and word.lower() not in STOPWORDS
        ]
        for word in candidates:
            if word.lower() in seen:
                continue
            seen.add(word.lower())
            expanded.append(word)

    quoted = [f'"{term}"' for term in expanded]
    return " OR ".join(quoted)


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