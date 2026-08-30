import sqlite3

import numpy as np

_VEC_TABLE = "chunk_vecs"
_DIM_KEY = "vector_dim"
_MODEL_KEY = "embedding_model"


def upsert(
    conn,
    items: list[tuple[str, np.ndarray, str]],
    model_id: str | None = None,
) -> None:
    """Sync (chunk_key, vector, relative_path) triples into the vec0 index."""
    if not items:
        return

    dimension = len(items[0][1])
    _ensure_table(conn, dimension, model_id)

    # vec0 has no UPSERT/ON CONFLICT support: replace is delete + insert.
    keys = [chunk_key for chunk_key, _, _ in items]
    placeholders = ",".join("?" * len(keys))
    conn.execute(
        f"DELETE FROM {_VEC_TABLE} WHERE chunk_key IN ({placeholders})",
        keys,
    )
    conn.executemany(
        f"""
        INSERT INTO {_VEC_TABLE} (chunk_key, embedding, relative_path)
        VALUES (?, ?, ?)
        """,
        [
            (chunk_key, _encode(vector), relative_path)
            for chunk_key, vector, relative_path in items
        ],
    )


def delete_keys(conn, keys: list[str]) -> None:
    if not keys or not table_exists(conn):
        return

    placeholders = ",".join("?" * len(keys))
    conn.execute(
        f"DELETE FROM {_VEC_TABLE} WHERE chunk_key IN ({placeholders})",
        keys,
    )


def prune_not_in(conn, current_keys: set[str]) -> None:
    if not table_exists(conn):
        return

    if not current_keys:
        clear(conn)
        return

    placeholders = ",".join("?" * len(current_keys))
    conn.execute(
        f"DELETE FROM {_VEC_TABLE} WHERE chunk_key NOT IN ({placeholders})",
        list(current_keys),
    )


def clear(conn) -> None:
    conn.execute(f"DROP TABLE IF EXISTS {_VEC_TABLE}")
    conn.execute(
        "DELETE FROM index_metadata WHERE key = ?",
        (_DIM_KEY,),
    )
    conn.execute(
        "DELETE FROM index_metadata WHERE key = ?",
        (_MODEL_KEY,),
    )


def table_exists(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (_VEC_TABLE,),
    ).fetchone()
    return row is not None


def search(
    conn,
    query_vector: np.ndarray,
    *,
    top_k: int = 5,
    relative_path: str | None = None,
) -> list[sqlite3.Row]:
    if not table_exists(conn):
        return []

    statement = f"""
        SELECT chunk_key, relative_path, distance
        FROM {_VEC_TABLE}
        WHERE embedding MATCH ?
          AND k = ?
    """
    parameters: list[object] = [_encode(query_vector), top_k]

    if relative_path is not None:
        statement += " AND relative_path = ?"
        parameters.append(relative_path)

    return conn.execute(statement, parameters).fetchall()


def _ensure_table(conn, dimension: int, model_id: str | None = None) -> None:
    stored_dim = _stored_dimension(conn)
    stored_model = _stored_model(conn) if model_id is not None else None

    if stored_dim == dimension and (model_id is None or stored_model == model_id) and table_exists(conn):
        return

    # Mismatch on dimension or model -> drop and clear derived embeddings
    need_drop = False
    if stored_dim is not None and stored_dim != dimension:
        need_drop = True
    if model_id is not None and stored_model is not None and stored_model != model_id:
        need_drop = True

    if need_drop:
        conn.execute(f"DROP TABLE IF EXISTS {_VEC_TABLE}")
        # Vectors from different models must never mix — even same dimension
        if model_id is not None and stored_model != model_id:
            try:
                conn.execute("DELETE FROM embeddings")
                conn.execute("DELETE FROM embedding_jobs")
            except sqlite3.OperationalError:
                pass

    conn.execute(
        f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS {_VEC_TABLE} USING vec0(
            chunk_key TEXT PRIMARY KEY,
            embedding FLOAT[{dimension}] distance_metric=cosine,
            relative_path TEXT
        )
        """
    )
    _set_dimension(conn, dimension)
    if model_id is not None:
        _set_model(conn, model_id)


def _stored_dimension(conn) -> int | None:
    try:
        row = conn.execute(
            "SELECT value FROM index_metadata WHERE key = ?",
            (_DIM_KEY,),
        ).fetchone()
    except sqlite3.OperationalError:
        return None

    return int(row["value"]) if row is not None else None


def _set_dimension(conn, dimension: int) -> None:
    conn.execute(
        """
        INSERT INTO index_metadata (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (_DIM_KEY, str(dimension)),
    )


def _stored_model(conn) -> str | None:
    try:
        row = conn.execute(
            "SELECT value FROM index_metadata WHERE key = ?",
            (_MODEL_KEY,),
        ).fetchone()
    except sqlite3.OperationalError:
        return None
    return row["value"] if row is not None else None


def _set_model(conn, model_id: str) -> None:
    conn.execute(
        """
        INSERT INTO index_metadata (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (_MODEL_KEY, model_id),
    )


def _encode(vector: np.ndarray) -> bytes:
    return np.asarray(vector, dtype="<f4").tobytes()
