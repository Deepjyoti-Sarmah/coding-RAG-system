"""Merkle / hierarchical hashing — deterministic root for incremental invalidation."""
import hashlib
from pathlib import PurePosixPath

from models.file_state import FileState


def compute_root(file_states: list[FileState]) -> str:
    """Deterministic repo root hash: sorted leaf SHA256(file_hash) + dir aggregation."""
    # leaf: relative_path\0file_hash
    leaves = sorted(f"{fs.relative_path}\0{fs.file_hash}" for fs in file_states)
    if not leaves:
        return hashlib.sha256(b"").hexdigest()
    # combine leaves
    h = hashlib.sha256()
    for leaf in leaves:
        h.update(hashlib.sha256(leaf.encode()).digest())
    # also fold dirs for hierarchical invalidation visibility
    dirs: dict[str, list[str]] = {}
    for fs in file_states:
        p = PurePosixPath(fs.relative_path)
        for parent in p.parents:
            if str(parent) in (".", ""):
                continue
            dirs.setdefault(str(parent), []).append(fs.file_hash)
    for d in sorted(dirs):
        h.update(hashlib.sha256(f"{d}\0{','.join(sorted(dirs[d]))}".encode()).digest())
    return h.hexdigest()
