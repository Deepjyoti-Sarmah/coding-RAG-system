import hashlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from analysis.fingerprints import compute_content_hash
from ingestion.ignore_rules import IgnoreRules, load_ignore_rules
from ingestion.loader import is_inside_excluded_dir


class NodeKind(Enum):
    FILE = "file"
    DIRECTORY = "directory"


@dataclass(slots=True)
class MerkleNode:
    relative_path: str
    kind: NodeKind
    hash: str


@dataclass(slots=True)
class MerkleTree:
    nodes: dict[str, MerkleNode]

    def node_hash(self, relative_path: str) -> str:
        return self.nodes[relative_path].hash

    @property
    def root_hash(self) -> str:
        return self.nodes[""].hash


def compute_merkle_tree(root_dir: str) -> MerkleTree:
    """Compute a deterministic hierarchical hash of the repo file tree.

    A file contributes its content hash; a directory contributes the hash of
    its children (names + child hashes) sorted deterministically. Only content
    and normalized names are hashed, never mtime, size, or random IDs, so a
    change to one leaf changes only its ancestor hashes.
    """
    root_path = Path(root_dir).resolve()
    nodes: dict[str, MerkleNode] = {}

    if root_path.is_file():
        content_hash = _hash_file(root_path)
        nodes[""] = MerkleNode(
            relative_path="",
            kind=NodeKind.FILE,
            hash=content_hash,
        )
        return MerkleTree(nodes=nodes)

    _build_directory(
        path=root_path,
        relative_path="",
        nodes=nodes,
        ignore_rules=load_ignore_rules(root_path),
    )

    return MerkleTree(nodes=nodes)


def _build_directory(
    *,
    path: Path,
    relative_path: str,
    nodes: dict[str, MerkleNode],
    ignore_rules: IgnoreRules,
) -> str:
    children: list[tuple[str, str]] = []

    for entry in sorted(path.iterdir(), key=lambda p: p.name):
        if is_inside_excluded_dir(entry):
            continue

        child_relative_path = (
            entry.name if relative_path == "" else f"{relative_path}/{entry.name}"
        )

        if ignore_rules.is_ignored(child_relative_path, is_dir=entry.is_dir()):
            continue

        if entry.is_dir():
            child_hash = _build_directory(
                path=entry,
                relative_path=child_relative_path,
                nodes=nodes,
                ignore_rules=ignore_rules,
            )
            nodes[child_relative_path] = MerkleNode(
                relative_path=child_relative_path,
                kind=NodeKind.DIRECTORY,
                hash=child_hash,
            )
        elif entry.is_file():
            content_hash = _hash_file(entry)
            nodes[child_relative_path] = MerkleNode(
                relative_path=child_relative_path,
                kind=NodeKind.FILE,
                hash=content_hash,
            )
            child_hash = content_hash
        else:
            continue

        children.append((entry.name, child_hash))

    directory_hash = _hash_children(children)

    nodes[relative_path] = MerkleNode(
        relative_path=relative_path,
        kind=NodeKind.DIRECTORY,
        hash=directory_hash,
    )

    return directory_hash


def _hash_file(file_path: Path) -> str:
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Skipping {file_path}: {e}")
        return ""

    return compute_content_hash(content)


def _hash_children(children: list[tuple[str, str]]) -> str:
    ordered = sorted(children, key=lambda item: item[0])

    payload = "".join(f"{name}\0{child_hash}\0" for name, child_hash in ordered)

    return hashlib.sha256(payload.encode("utf-8")).hexdigest()