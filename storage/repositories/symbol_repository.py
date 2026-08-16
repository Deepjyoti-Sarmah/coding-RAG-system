from models.entities.symbol_kind import SymbolKind
from models.entities.symbols import Symbol
from storage._rows import location_columns, source_location_from_row


def insert_many(conn, symbols: list[Symbol]) -> None:
    conn.executemany(
        """
        INSERT INTO symbols (
            symbol_id, document_id, name, kind, relative_path,
            start_line, end_line, start_byte, end_byte, content,
            parent_symbol_id, qualified_name, content_hash, signature_hash, stable_key
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                symbol.symbol_id,
                symbol.document_id,
                symbol.name,
                symbol.kind.value,
                symbol.relative_path,
                *location_columns(symbol.location),
                symbol.content,
                symbol.parent_symbol_id,
                symbol.qualified_name,
                symbol.content_hash,
                symbol.signature_hash,
                symbol.stable_key,
            )
            for symbol in symbols
        ],
    )


def fetch_all(conn) -> list[Symbol]:
    rows = conn.execute(
        """
        SELECT symbol_id, document_id, name, kind, relative_path,
               start_line, end_line, start_byte, end_byte, content,
               parent_symbol_id, qualified_name, content_hash, signature_hash, stable_key
        FROM symbols
        """
    ).fetchall()

    return [
        Symbol(
            symbol_id=row["symbol_id"],
            document_id=row["document_id"],
            name=row["name"],
            kind=SymbolKind(row["kind"]),
            relative_path=row["relative_path"],
            location=source_location_from_row(row),
            content=row["content"],
            parent_symbol_id=row["parent_symbol_id"],
            qualified_name=row["qualified_name"],
            content_hash=row["content_hash"],
            signature_hash=row["signature_hash"],
            stable_key=row["stable_key"],
        )
        for row in rows
    ]
