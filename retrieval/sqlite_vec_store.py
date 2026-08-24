import numpy as np

from retrieval.vector_store import VectorSearchHit, VectorStore
from storage import db
from storage.repositories import vec_index_repository


class SqliteVecVectorStore(VectorStore):
    """Vector search served by the sqlite-vec extension over index.sqlite.

    Vectors never leave SQLite: queries run as KNN against a vec0 virtual
    table, so RAM stays flat no matter how large the indexed repo grows.
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def search(
        self,
        query_vector: np.ndarray,
        *,
        top_k: int = 5,
        relative_path: str | None = None,
    ) -> list[VectorSearchHit]:
        conn = db.connect(self._db_path)

        try:
            rows = vec_index_repository.search(
                conn,
                query_vector,
                top_k=top_k,
                relative_path=relative_path,
            )
        finally:
            conn.close()

        return [
            VectorSearchHit(
                chunk_key=row["chunk_key"],
                relative_path=row["relative_path"],
                score=1.0 - float(row["distance"]),
            )
            for row in rows
        ]


def sqlite_vec_available(db_path: str) -> bool:
    conn = db.connect(db_path or ":memory:")

    try:
        return db.load_vec_extension(conn)
    finally:
        conn.close()
