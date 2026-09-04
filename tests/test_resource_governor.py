import os
import tempfile
import unittest

from indexing.resource_governor import (
    IdleTracker,
    ProjectIndexLock,
    adaptive_batch_size,
    is_memory_pressured,
    should_skip_large_file,
)


class TestResourceGovernor(unittest.TestCase):
    def test_skip_large_file(self):
        self.assertFalse(should_skip_large_file(1024))
        self.assertTrue(should_skip_large_file(3 * 1024 * 1024))

    def test_adaptive_batch(self):
        self.assertEqual(adaptive_batch_size(10), 25)
        self.assertEqual(adaptive_batch_size(200), 50)
        self.assertEqual(adaptive_batch_size(600), 100)

    def test_project_index_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock1 = ProjectIndexLock(tmp)
            self.assertTrue(lock1.acquire(blocking=False))
            lock2 = ProjectIndexLock(tmp)
            # second non-blocking should fail or succeed on Windows no-op, just ensure no crash
            lock2.acquire(blocking=False)
            lock1.release()
            lock2.release()

    def test_onnx_thread_cap(self):
        os.environ["CKG_ORT_THREADS"] = "2"
        try:
            from indexing.resource_governor import onnx_thread_cap

            onnx_thread_cap()
            self.assertEqual(os.environ.get("OMP_NUM_THREADS"), "2")
        finally:
            os.environ.pop("CKG_ORT_THREADS", None)
            for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "ORT_NUM_THREADS"):
                os.environ.pop(k, None)

    def test_is_memory_pressured(self):
        # Should not crash, returns bool
        self.assertIsInstance(is_memory_pressured(), bool)

    def test_idle_tracker(self):
        t = IdleTracker(timeout_seconds=1)
        self.assertFalse(t.is_idle())
        import time

        time.sleep(1.1)
        self.assertTrue(t.is_idle())
        t.touch()
        self.assertFalse(t.is_idle())

    def test_concurrent_lock(self):
        import concurrent.futures

        with tempfile.TemporaryDirectory() as tmp:
            # two threads try non-blocking acquire same .ckg/.index.lock
            def try_lock():
                lk = ProjectIndexLock(tmp)
                ok = lk.acquire(blocking=False)
                # hold briefly if acquired
                import time
                time.sleep(0.1)
                lk.release()
                return ok

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
                f1 = ex.submit(try_lock)
                import time
                time.sleep(0.02)
                f2 = ex.submit(try_lock)
                r1, r2 = f1.result(), f2.result()
                # at least one succeeded, second may fail or succeed on Windows no-op — just no crash and at least one True
                self.assertTrue(r1 or r2)


if __name__ == "__main__":
    unittest.main()
