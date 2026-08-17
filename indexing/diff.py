import posixpath
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from analysis.fingerprints import compute_content_hash
from analysis.semantic.normalize_path import resolve_module_path
from ingestion.loader import iter_repo_files
from models.entities.documents import Document
from models.entities.exports import Export
from models.entities.import_references import ImportReference
from models.entities.symbols import Symbol
from models.file_state import FileState


class FileChange(Enum):
    NEW = "new"
    CHANGED = "changed"
    UNCHANGED = "unchanged"
    DELETED = "deleted"


@dataclass(slots=True)
class ScannedFile:
    file_path: Path
    relative_path: str
    size_bytes: int
    mtime_ns: int
    content: str | None


@dataclass(slots=True)
class ScanResult:
    changes: dict[str, FileChange]
    current: dict[str, ScannedFile]


def scan_files(
    root_dir: str,
    previous_states: dict[str, FileState],
) -> ScanResult:
    """Classify every repo file against the previous index state.

    mtime + size is a cheap change hint; content hash is the correctness
    signal. Files whose mtime and size match the stored state are marked
    UNCHANGED without reading their content.
    """
    changes: dict[str, FileChange] = {}
    current: dict[str, ScannedFile] = {}
    seen: set[str] = set()

    for file_path, relative_path in iter_repo_files(root_dir):
        seen.add(relative_path)

        stat = file_path.stat()
        size_bytes = stat.st_size
        mtime_ns = stat.st_mtime_ns
        previous = previous_states.get(relative_path)

        if _fast_path_unchanged(previous, mtime_ns, size_bytes):
            current[relative_path] = ScannedFile(
                file_path=file_path,
                relative_path=relative_path,
                size_bytes=size_bytes,
                mtime_ns=mtime_ns,
                content=None,
            )
            changes[relative_path] = FileChange.UNCHANGED
            continue

        content = _read_content(file_path)

        if content is None:
            continue

        content_hash = compute_content_hash(content)

        if previous is not None and previous.file_hash == content_hash:
            changes[relative_path] = FileChange.UNCHANGED
        else:
            changes[relative_path] = (
                FileChange.NEW if previous is None else FileChange.CHANGED
            )

        current[relative_path] = ScannedFile(
            file_path=file_path,
            relative_path=relative_path,
            size_bytes=size_bytes,
            mtime_ns=mtime_ns,
            content=content,
        )

    for relative_path in previous_states:
        if relative_path not in seen:
            changes[relative_path] = FileChange.DELETED

    return ScanResult(changes=changes, current=current)


def importers_of(
    *,
    import_references: list[ImportReference],
    documents_by_id: dict[str, Document],
) -> dict[str, set[str]]:
    """Map a repo-relative module path to the document ids importing it."""
    importers: dict[str, set[str]] = defaultdict(set)

    for import_reference in import_references:
        importing_document = documents_by_id.get(import_reference.document_id)

        if importing_document is None:
            continue

        importing_directory = posixpath.dirname(importing_document.relative_path)

        for candidate in resolve_module_path(
            module_path=import_reference.module_path,
            importing_directory=importing_directory,
        ):
            importers[candidate].add(importing_document.document_id)

    return dict(importers)


def interface_fingerprint(
    *,
    exports: list[Export],
    symbols: list[Symbol],
) -> tuple[tuple[str, str], ...]:
    """Deterministic signature of a file's public exported interface.

    Each entry is (exported_name, signature_hash of the exported symbol).
    Re-exports and anonymous exports contribute their raw name only.
    """
    module_symbols = {
        (symbol.document_id, symbol.name): symbol
        for symbol in symbols
        if symbol.parent_symbol_id is None
    }

    fingerprints: list[tuple[str, str]] = []

    for export in sorted(exports, key=lambda e: e.exported_name):
        if export.symbol_name is None:
            fingerprints.append((export.exported_name, ""))
            continue

        symbol = module_symbols.get((export.document_id, export.symbol_name))

        fingerprints.append(
            (
                export.exported_name,
                symbol.signature_hash if symbol is not None else "",
            )
        )

    return tuple(fingerprints)


def _fast_path_unchanged(
    previous: FileState | None,
    mtime_ns: int,
    size_bytes: int,
) -> bool:
    if previous is None:
        return False

    return previous.mtime_ns == mtime_ns and previous.size_bytes == size_bytes


def _read_content(file_path: Path) -> str | None:
    try:
        return file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Skipping {file_path}: {e}")
        return None