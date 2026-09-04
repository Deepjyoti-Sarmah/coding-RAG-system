import sys
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

from ckg.config import (
    EXCLUDE_DIRS,
    FALLBACK_EXTENSIONS,
    INCLUDE_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
)
from ingestion.ignore_rules import load_ignore_rules
from ingestion.language import detect_language
from models.entities.documents import Document


def is_inside_excluded_dir(file_path: Path) -> bool:
    return any(part in EXCLUDE_DIRS for part in file_path.parts)


def should_skip_file(file_path: Path) -> bool:
    ext = file_path.suffix.lower()
    # Strict + fallback are both indexable; only skip truly unknown
    if ext not in INCLUDE_EXTENSIONS and ext not in FALLBACK_EXTENSIONS:
        return True

    size_bytes = file_path.stat().st_size

    if size_bytes > MAX_FILE_SIZE_BYTES:
        # Silent otherwise: a user asking why a known symbol (e.g. a class
        # or route defined near the top of a large file) can't be found
        # gets no signal at all that the file was ever seen and dropped.
        print(
            f"Skipping {file_path}: {size_bytes} bytes exceeds "
            f"MAX_FILE_SIZE_BYTES ({MAX_FILE_SIZE_BYTES})",
            file=sys.stderr,
        )
        return True

    return False


def iter_repo_files(path: str | Path) -> Iterator[tuple[Path, str]]:
    """Yield (file_path, repo_relative_path) for every indexable file."""
    root_path = Path(path).resolve()

    is_single_file = root_path.is_file()
    ignore_rules = None if is_single_file else load_ignore_rules(root_path)

    files = [root_path] if is_single_file else root_path.rglob("*")

    for file_path in files:
        if not file_path.is_file():
            continue

        if is_inside_excluded_dir(file_path):
            continue

        if should_skip_file(file_path):
            continue

        relative_path = (
            file_path.name if is_single_file else str(file_path.relative_to(root_path))
        )

        if ignore_rules is not None and ignore_rules.is_ignored(relative_path):
            continue

        yield file_path, relative_path


def build_document(
    *,
    file_path: Path,
    relative_path: str,
    content: str,
    document_id: str,
) -> Document:
    return Document(
        document_id=document_id,
        absolute_path=str(file_path.resolve()),
        relative_path=relative_path,
        file_name=file_path.name,
        extension=file_path.suffix.lower(),
        language=detect_language(file_path.suffix.lower()),
        size_bytes=file_path.stat().st_size,
        line_count=len(content.splitlines()),
        content=content,
    )


def load_code_files(path: str, *, on_progress=None) -> list[Document]:
    from indexing.secrets import is_secret_filename, should_skip_file_content

    documents: list[Document] = []

    for idx, (file_path, relative_path) in enumerate(iter_repo_files(path), start=1):
        if is_secret_filename(relative_path):
            # pre-open deny-list: skip .env/.pem etc without reading
            print(f"Skipping {file_path}: secret filename", file=sys.stderr)
            continue
        try:
            content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            print(f"Skipping {file_path}: {e}")
            continue

        if should_skip_file_content(relative_path, content):
            print(f"Skipping {file_path}: contains secrets", file=sys.stderr)
            continue

        documents.append(
            build_document(
                file_path=file_path,
                relative_path=relative_path,
                content=content,
                document_id=str(uuid4()),
            )
        )

        if on_progress is not None and idx % 50 == 0:
            try:
                on_progress(f"Parsed {idx} files...")
            except Exception:
                pass

    return documents
