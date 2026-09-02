"""Resource governor — caps indexing to stay local-first friendly."""

import os
import time
from pathlib import Path

DEFAULT_MAX_FILE_BYTES = 2 * 1024 * 1024  # 2MB, matches CCE _MAX_FILE_BYTES
DEFAULT_BATCH_SIZE = 50
DEFAULT_PARSE_BATCH = 50


def onnx_thread_cap(n: int | None = None) -> None:
    """Cap ONNX/sentence-transformers threads. Respects CCE_ORT_THREADS env."""
    env_n = os.environ.get("CCE_ORT_THREADS")
    explicit = False
    if env_n is not None:
        try:
            n = int(env_n)
            explicit = True
        except ValueError:
            pass
    if n is None:
        import multiprocessing

        n = min(multiprocessing.cpu_count(), 4)
    if n is None:
        os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
        return
    for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "ORT_NUM_THREADS"):
        if explicit:
            os.environ[k] = str(n)
        else:
            os.environ.setdefault(k, str(n))
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


def should_skip_large_file(size_bytes: int, cap: int = DEFAULT_MAX_FILE_BYTES) -> bool:
    return size_bytes > cap


def adaptive_batch_size(total_files: int, base: int = DEFAULT_BATCH_SIZE) -> int:
    if total_files > 500:
        return base * 2
    if total_files > 100:
        return base
    return max(10, base // 2)


def is_memory_pressured(threshold: float = 25.0) -> bool:
    try:
        with open("/proc/pressure/memory", encoding="utf-8") as f:
            for line in f:
                if "some avg10=" in line:
                    val = float(line.split("some avg10=")[1].split()[0])
                    return val > threshold
    except (OSError, ValueError, IndexError):
        pass
    return False


class ProjectIndexLock:
    """Advisory file lock via fcntl.flock, no-op on Windows."""

    def __init__(self, project_path: str | Path):
        self.lock_path = Path(project_path).resolve() / ".ckg" / ".index.lock"
        self._fh = None

    def acquire(self, blocking: bool = False) -> bool:
        try:
            import fcntl

            self.lock_path.parent.mkdir(parents=True, exist_ok=True)
            self._fh = open(self.lock_path, "w", encoding="utf-8")
            flags = fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB)
            fcntl.flock(self._fh.fileno(), flags)
            return True
        except (ImportError, OSError):
            return True  # no-op on Windows or if flock unavailable

    def release(self) -> None:
        try:
            import fcntl

            if self._fh:
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
                self._fh.close()
                self._fh = None
        except Exception:
            pass

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *_):
        self.release()


class IdleTracker:
    def __init__(self, timeout_seconds: int = 1800):
        self.timeout = timeout_seconds
        self.last = time.monotonic()

    def touch(self) -> None:
        self.last = time.monotonic()

    def is_idle(self) -> bool:
        return (time.monotonic() - self.last) > self.timeout
