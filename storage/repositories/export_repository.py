from models.entities.exports import Export
from storage._rows import location_columns, source_location_from_row


def insert_many(conn, exports: list[Export]) -> None:
    conn.executemany(
        """
        INSERT OR REPLACE INTO exports (
            document_id, exported_name, symbol_name,
            start_line, end_line, start_byte, end_byte
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                export.document_id,
                export.exported_name,
                export.symbol_name,
                *location_columns(export.location),
            )
            for export in exports
        ],
    )


def fetch_all(conn) -> list[Export]:
    rows = conn.execute(
        """
        SELECT document_id, exported_name, symbol_name,
               start_line, end_line, start_byte, end_byte
        FROM exports
        """
    ).fetchall()

    return [
        Export(
            document_id=row["document_id"],
            exported_name=row["exported_name"],
            symbol_name=row["symbol_name"],
            location=source_location_from_row(row),
        )
        for row in rows
    ]
