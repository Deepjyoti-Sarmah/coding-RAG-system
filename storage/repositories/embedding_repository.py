import numpy as np


def insert_many(conn, embeddings: dict[str, np.ndarray]) -> None:
    conn.executemany(
        "INSERT INTO embeddings (chunk_id, embedding) VALUES (?, ?)",
        [
            (chunk_id, _encode(vector))
            for chunk_id, vector in embeddings.items()
        ],
    )


def fetch_all(conn) -> dict[str, np.ndarray]:
    rows = conn.execute(
        "SELECT chunk_id, embedding FROM embeddings"
    ).fetchall()

    return {row["chunk_id"]: _decode(row["embedding"]) for row in rows}


def load_embedding_cache(conn) -> dict[str, np.ndarray]:
    rows = conn.execute(
        """
        SELECT c.content_hash, e.embedding
        FROM embeddings e
        JOIN chunks c ON c.chunk_id = e.chunk_id
        """
    ).fetchall()

    return {row["content_hash"]: _decode(row["embedding"]) for row in rows}


def _encode(vector: np.ndarray) -> bytes:
    return np.asarray(vector, dtype=np.float32).tobytes()


def _decode(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)