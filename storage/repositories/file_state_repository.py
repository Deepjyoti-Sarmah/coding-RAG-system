from models.file_state import FileState


def insert_many(conn, file_states: list[FileState]) -> None:
    conn.executemany(
        """
        INSERT INTO file_state (
            relative_path, file_hash, size_bytes, mtime_ns, last_indexed_at
        ) VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(relative_path) DO UPDATE SET
            file_hash = excluded.file_hash,
            size_bytes = excluded.size_bytes,
            mtime_ns = excluded.mtime_ns,
            last_indexed_at = excluded.last_indexed_at
        """,
        [
            (
                state.relative_path,
                state.file_hash,
                state.size_bytes,
                state.mtime_ns,
                state.last_indexed_at,
            )
            for state in file_states
        ],
    )


def fetch_all(conn) -> list[FileState]:
    rows = conn.execute(
        """
        SELECT relative_path, file_hash, size_bytes, mtime_ns, last_indexed_at
        FROM file_state
        """
    ).fetchall()

    return [
        FileState(
            relative_path=row["relative_path"],
            file_hash=row["file_hash"],
            size_bytes=row["size_bytes"],
            mtime_ns=row["mtime_ns"],
            last_indexed_at=row["last_indexed_at"],
        )
        for row in rows
    ]
