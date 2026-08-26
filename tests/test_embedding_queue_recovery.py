import tempfile
import time
import unittest
from pathlib import Path

from storage import db, schema
from storage.repositories import embedding_job_repository


class TestEmbeddingQueueRecovery(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp.name) / "test.sqlite")
        conn = db.connect(self.db_path)
        try:
            schema.create_schema(conn)
            # ensure clean
            conn.execute("DELETE FROM embedding_jobs")
            conn.commit()
        finally:
            conn.close()

    def tearDown(self):
        self.tmp.cleanup()

    def _insert_job(self, chunk_key, status, attempts, claimed_at=None):
        conn = db.connect(self.db_path)
        try:
            conn.execute(
                "INSERT INTO embedding_jobs (chunk_key, content_hash, status, attempts, error, claimed_at) VALUES (?, ?, ?, ?, NULL, ?)",
                (chunk_key, "hash-" + chunk_key, status, attempts, claimed_at),
            )
            conn.commit()
        finally:
            conn.close()

    def test_processing_old_claimed_at_is_reclaimed(self):
        old = int(time.time()) - 600  # 10 min ago, older than 5 min lease
        self._insert_job("old-proc", "PROCESSING", 1, old)
        conn = db.connect(self.db_path)
        try:
            jobs = embedding_job_repository.claim(conn, limit=10)
            conn.commit()
            keys = {j.chunk_key for j in jobs}
            self.assertIn("old-proc", keys)
        finally:
            conn.close()

    def test_processing_exhausted_not_reclaimed(self):
        """A chunk that keeps crashing the worker must stop being reclaimed.

        A process killed mid-job never reaches `mark_failed`, so the job stays
        PROCESSING and the lease hands it back. Without an attempts cap on that
        branch, a chunk that reliably crashes the worker loops forever - and
        since the drain runs detached, it would do so unattended.
        """
        old = int(time.time()) - 600
        self._insert_job(
            "crash-loop",
            "PROCESSING",
            embedding_job_repository.MAX_ATTEMPTS,
            old,
        )
        conn = db.connect(self.db_path)
        try:
            jobs = embedding_job_repository.claim(conn, limit=10)
            conn.commit()
            keys = {j.chunk_key for j in jobs}
            self.assertNotIn("crash-loop", keys)
        finally:
            conn.close()

    def test_processing_recent_claimed_at_not_reclaimed(self):
        recent = int(time.time()) - 60  # 1 min ago, within lease
        self._insert_job("recent-proc", "PROCESSING", 1, recent)
        conn = db.connect(self.db_path)
        try:
            jobs = embedding_job_repository.claim(conn, limit=10)
            conn.commit()
            keys = {j.chunk_key for j in jobs}
            self.assertNotIn("recent-proc", keys)
        finally:
            conn.close()

    def test_failed_exhausted_not_claimed(self):
        self._insert_job("exhausted", "FAILED", embedding_job_repository.MAX_ATTEMPTS, None)
        conn = db.connect(self.db_path)
        try:
            jobs = embedding_job_repository.claim(conn, limit=10)
            conn.commit()
            keys = {j.chunk_key for j in jobs}
            self.assertNotIn("exhausted", keys)
        finally:
            conn.close()

    def test_status_counts_reports_exhausted(self):
        self._insert_job("exh1", "FAILED", embedding_job_repository.MAX_ATTEMPTS, None)
        self._insert_job("pending1", "PENDING", 0, None)
        conn = db.connect(self.db_path)
        try:
            counts = embedding_job_repository.status_counts(conn)
            self.assertIn("exhausted", counts)
            self.assertEqual(counts["exhausted"], 1)
            self.assertIn("FAILED", counts)
        finally:
            conn.close()
