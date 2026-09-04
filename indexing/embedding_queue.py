import sqlite3
from dataclasses import dataclass
from typing import Any

import numpy as np

from embeddings.provider import EmbeddingProvider
from indexing.embedding_store import embed_chunks
from storage import db, schema
from storage.index_store import load_embedding_cache
from storage.repositories import (
    chunk_repository,
    embedding_job_repository,
    embedding_repository,
    vec_index_repository,
)


@dataclass(slots=True)
class EmbeddingRunReport:
    claimed: int = 0
    done: int = 0
    reused: int = 0
    stale: int = 0
    failed: int = 0


def enqueue_embedding_jobs(db_path: str, chunks: list[Any]) -> int:
    conn = db.connect(db_path)

    try:
        schema.create_schema(conn)

        with db.transaction(conn):
            for chunk in chunks:
                embedding_job_repository.enqueue(
                    conn,
                    chunk.chunk_key,
                    chunk.content_hash,
                )

        return len(chunks)
    finally:
        conn.close()


def _ensure_model_consistency(conn, provider: EmbeddingProvider) -> None:
    """Invalidate stored embeddings if model identifier or dimension changed."""
    # Check dimension mismatch first (covers FakeProvider dim switch without model_id change)
    try:
        from storage.schema import get_embedding_dim, set_embedding_dim

        stored_dim = get_embedding_dim(conn)
        cur_dim = getattr(provider, "dimension", None)
        if stored_dim is not None and cur_dim is not None and stored_dim != cur_dim:
            try:
                vec_index_repository.clear(conn)
            except (sqlite3.Error, OSError):
                pass
            try:
                conn.execute("DELETE FROM embeddings")
                conn.execute("DELETE FROM embedding_jobs")
                chunks = chunk_repository.fetch_all(conn)
                for chunk in chunks:
                    embedding_job_repository.enqueue(conn, chunk.chunk_key, chunk.content_hash)
                set_embedding_dim(conn, cur_dim)
                conn.commit()
            except (sqlite3.Error, OSError):
                pass
            # need to re-read stored_model after dim clear
        elif cur_dim is not None and stored_dim is None:
            try:
                set_embedding_dim(conn, cur_dim)
            except (sqlite3.Error, OSError):
                pass
    except Exception:
        pass
    try:
        stored = conn.execute(
            "SELECT value FROM index_metadata WHERE key = ?", ("embedding_model",)
        ).fetchone()
        stored_model = stored["value"] if stored else None
    except (sqlite3.Error, OSError):  # -- metadata lookup must not crash
        stored_model = None
    current = getattr(provider, "model_id", None)
    if current is None:
        try:
            current = (
                f"{getattr(provider, 'model_name', 'unknown')}:{provider.dimension}"
            )
        except (
            AttributeError,
            ValueError,
            OSError,
        ):  # -- provider probe must not crash
            return
    if stored_model is not None and stored_model != current:
        # Different models must never mix — clear all derived state and re-enqueue
        try:
            vec_index_repository.clear(conn)
        except (sqlite3.Error, OSError):  # -- best-effort cleanup
            pass
        try:
            conn.execute("DELETE FROM embeddings")
            conn.execute("DELETE FROM embedding_jobs")
            # Re-enqueue jobs for all current chunks with new model
            try:
                chunks = chunk_repository.fetch_all(conn)
                for chunk in chunks:
                    embedding_job_repository.enqueue(
                        conn, chunk.chunk_key, chunk.content_hash
                    )
            except (sqlite3.Error, OSError):  # -- re-enqueue best-effort
                pass
            conn.execute(
                "INSERT INTO index_metadata (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                ("embedding_model", current),
            )
            conn.commit()
        except (sqlite3.Error, OSError):  # -- model switch must not crash
            pass
    elif stored_model is None and current is not None:
        try:
            conn.execute(
                "INSERT INTO index_metadata (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                ("embedding_model", current),
            )
        except (sqlite3.Error, OSError):  # -- metadata write best-effort
            pass


def run_embedding_worker(
    db_path: str,
    provider: EmbeddingProvider,
    *,
    limit: int | None = None,
    on_progress=None,
) -> EmbeddingRunReport:
    conn = db.connect(db_path)
    report = EmbeddingRunReport()

    try:
        schema.create_schema(conn)
        # Ensure model identifier stored and invalidate on change
        _ensure_model_consistency(conn, provider)
        # Also store/update for new runs
        try:
            mid = getattr(provider, "model_id", None)
            if mid:
                conn.execute(
                    "INSERT INTO index_metadata (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    ("embedding_model", mid),
                )
                conn.commit()
        except (sqlite3.Error, OSError, AttributeError, ValueError):  # -- metadata write best-effort
            pass

        # Backoff under memory pressure (P4-1-1)
        try:
            from indexing.resource_governor import is_memory_pressured

            if limit is not None and is_memory_pressured():
                limit = max(10, limit // 2)
        except Exception:
            pass

        jobs = embedding_job_repository.claim(conn, limit=limit)

        if not jobs:
            return report

        report.claimed = len(jobs)

        claimed_keys = {job.chunk_key for job in jobs}
        chunks_by_key = {
            chunk.chunk_key: chunk
            for chunk in chunk_repository.fetch_all(conn)
            if chunk.chunk_key in claimed_keys
        }

        embeddable: list[Any] = []
        stale: list[tuple[str, str]] = []
        orphaned: list[str] = []

        for job in jobs:
            chunk = chunks_by_key.get(job.chunk_key)

            if chunk is None:
                orphaned.append(job.chunk_key)
            elif chunk.content_hash != job.content_hash:
                stale.append((job.chunk_key, chunk.content_hash))
            else:
                embeddable.append(chunk)

        report.stale = len(stale) + len(orphaned)

        embeddings_by_key: dict[str, np.ndarray] = {}

        try:
            if embeddable:
                # emit periodic progress when embedding many chunks
                if on_progress is not None and len(embeddable) >= 50:
                    # process in batches to allow periodic progress emission
                    embeddings_by_key = {}
                    total_missing = 0
                    cache = load_embedding_cache(db_path)
                    for idx in range(0, len(embeddable), 50):
                        batch = embeddable[idx : idx + 50]
                        batch_embeddings, missing = embed_chunks(batch, provider, cache)
                        embeddings_by_key.update(batch_embeddings)
                        total_missing += missing
                        # update cache with newly computed embeddings for next batch reuse within same run
                        for k, v in batch_embeddings.items():
                            cache[k] = v
                        try:
                            on_progress(
                                f"Embedding {min(idx + 50, len(embeddable))}/{len(embeddable)} chunks..."
                            )
                        except Exception:
                            pass
                    report.done = len(embeddable)
                    report.reused = len(embeddable) - total_missing
                else:
                    embeddings_by_key, missing = embed_chunks(
                        embeddable,
                        provider,
                        load_embedding_cache(db_path),
                    )
                    report.done = len(embeddable)
                    report.reused = len(embeddable) - missing
        except Exception as exc:
            with db.transaction(conn):
                for chunk in embeddable:
                    embedding_job_repository.mark_failed(
                        conn, chunk.chunk_key, str(exc)
                    )

            report.failed = len(embeddable)
            return report

        with db.transaction(conn):
            if embeddings_by_key:
                embedding_repository.upsert(conn, embeddings_by_key)
                vec_index_repository.upsert(
                    conn,
                    [
                        (
                            chunk_key,
                            vector,
                            chunks_by_key[chunk_key].relative_path,
                        )
                        for chunk_key, vector in embeddings_by_key.items()
                    ],
                    model_id=getattr(provider, "model_id", None),
                )

            for chunk in embeddable:
                embedding_job_repository.mark_done(conn, chunk.chunk_key)

            for chunk_key, content_hash in stale:
                embedding_job_repository.reenqueue(conn, chunk_key, content_hash)

            for chunk_key in orphaned:
                conn.execute(
                    "DELETE FROM embedding_jobs WHERE chunk_key = ?",
                    (chunk_key,),
                )

        return report
    finally:
        conn.close()


def queue_status(db_path: str) -> dict[str, int]:
    conn = db.connect(db_path)

    try:
        schema.create_schema(conn)
        return embedding_job_repository.status_counts(conn)
    finally:
        conn.close()
