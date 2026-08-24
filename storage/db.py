import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

BUSY_TIMEOUT_MS = 5000


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    load_vec_extension(conn)
    return conn


def load_vec_extension(conn: sqlite3.Connection) -> bool:
    """Load sqlite-vec into this connection.

    Returns False when the extension is unavailable (not installed, or the
    Python build refuses loadable extensions) so callers can fall back to
    the in-memory numpy store.
    """
    try:
        import sqlite_vec
    except ImportError:
        return False

    try:
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
    except (AttributeError, RuntimeError):
        return False

    return True


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[None]:
    try:
        conn.execute("BEGIN")
        yield
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")
