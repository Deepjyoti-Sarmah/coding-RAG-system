from dataclasses import dataclass


@dataclass(slots=True)
class FileState:
    relative_path: str
    file_hash: str
    size_bytes: int
    mtime_ns: int
    last_indexed_at: str
