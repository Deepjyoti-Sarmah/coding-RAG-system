import tempfile
import unittest
from pathlib import Path

import numpy as np

from embeddings.fake_provider import FakeEmbeddingProvider
from embeddings.provider import EmbeddingProvider
from indexing.embedding_queue import (
    enqueue_embedding_jobs,
    queue_status,
    run_embedding_worker,
)
from indexing.indexer import reindex_index
from models.entities.embedding_job_status import EmbeddingJobStatus

AUTH = {
    "a.ts": "export function createAuth() { return 1; }\n",
    "b.ts": (
        'import { createAuth } from "./a";\n'
        "export function run() { createAuth(); }\n"
    ),
}


def _write(root: Path, files: dict[str, str]) -> None:
    for relative_path, content in files.items():
        (root / relative_path).write_text(content, encoding="utf-8")


class FailingProvider(EmbeddingProvider):
    @property
    def dimension(self) -> int:
        return 8

    def embed(self, text: str) -> np.ndarray:
        raise RuntimeError("embedding backend unavailable")

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        raise RuntimeError("embedding backend unavailable")

    def embed_query(self, query: str) -> np.ndarray:
        raise RuntimeError("embedding backend unavailable")


class TestEmbeddingQueue(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db_path = str(self.root / "index.sqlite")
        self.provider = FakeEmbeddingProvider(dimension=8)
        _write(self.root, AUTH)
        reindex_index(self.db_path, str(self.root))

    def tearDown(self):
        self.tmp.cleanup()

    def test_indexing_enqueues_every_chunk_as_pending(self):
        status = queue_status(self.db_path)

        self.assertGreater(status[EmbeddingJobStatus.PENDING.value], 0)
        self.assertNotIn(EmbeddingJobStatus.DONE.value, status)

    def test_worker_moves_pending_jobs_to_done(self):
        pending_count = queue_status(self.db_path)[EmbeddingJobStatus.PENDING.value]

        report = run_embedding_worker(self.db_path, self.provider)

        self.assertEqual(report.claimed, pending_count)
        self.assertEqual(report.done, pending_count)

        status = queue_status(self.db_path)
        self.assertEqual(status[EmbeddingJobStatus.DONE.value], pending_count)
        self.assertNotIn(EmbeddingJobStatus.PENDING.value, status)

    def test_unchanged_content_hash_is_not_reembedded(self):
        run_embedding_worker(self.db_path, self.provider)
        done_count = queue_status(self.db_path)[EmbeddingJobStatus.DONE.value]

        # Re-running the indexer over unchanged files re-enqueues the same
        # (chunk_key, content_hash) pairs, which must stay DONE rather than
        # being reset to PENDING.
        reindex_index(self.db_path, str(self.root))
        status = queue_status(self.db_path)
        self.assertEqual(status[EmbeddingJobStatus.DONE.value], done_count)
        self.assertNotIn(EmbeddingJobStatus.PENDING.value, status)

        report = run_embedding_worker(self.db_path, self.provider)
        self.assertEqual(report.claimed, 0)

    def test_failed_job_is_retried_on_next_run(self):
        failing_report = run_embedding_worker(self.db_path, FailingProvider())

        self.assertGreater(failing_report.failed, 0)
        status = queue_status(self.db_path)
        self.assertEqual(
            status[EmbeddingJobStatus.FAILED.value], failing_report.failed
        )
        self.assertNotIn(EmbeddingJobStatus.PENDING.value, status)

        retry_report = run_embedding_worker(self.db_path, self.provider)

        self.assertEqual(retry_report.claimed, failing_report.failed)
        self.assertEqual(retry_report.done, failing_report.failed)
        self.assertNotIn(
            EmbeddingJobStatus.FAILED.value, queue_status(self.db_path)
        )

    def test_limit_caps_jobs_claimed_per_run(self):
        report = run_embedding_worker(self.db_path, self.provider, limit=1)

        self.assertEqual(report.claimed, 1)
        self.assertEqual(
            queue_status(self.db_path)[EmbeddingJobStatus.PENDING.value], 1
        )

    def test_enqueue_embedding_jobs_returns_chunk_count(self):
        from storage.index_store import load_index

        chunk_count = len(load_index(self.db_path).chunks)
        enqueued = enqueue_embedding_jobs(self.db_path, load_index(self.db_path).chunks)

        self.assertEqual(enqueued, chunk_count)


if __name__ == "__main__":
    unittest.main()
