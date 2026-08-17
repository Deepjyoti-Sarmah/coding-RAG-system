from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

from config import (
    EXCLUDE_DIRS,
    INCLUDE_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
)
from ingestion.language import detect_language
from models.entities.documents import Document


def is_inside_excluded_dir(file_path: Path) -> bool:
    return any(part in EXCLUDE_DIRS for part in file_path.parts)


def should_skip_file(file_path: Path) -> bool:
    if file_path.suffix.lower() not in INCLUDE_EXTENSIONS:
        return True

    if file_path.stat().st_size > MAX_FILE_SIZE_BYTES:
        return True

    return False


def iter_repo_files(path: str | Path) -> Iterator[tuple[Path, str]]:
    """Yield (file_path, repo_relative_path) for every indexable file."""
    root_path = Path(path).resolve()

    is_single_file = root_path.is_file()

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


def load_code_files(path: str) -> list[Document]:
    documents: list[Document] = []

    for file_path, relative_path in iter_repo_files(path):
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"Skipping {file_path}: {e}")
            continue

        documents.append(
            build_document(
                file_path=file_path,
                relative_path=relative_path,
                content=content,
                document_id=str(uuid4()),
            )
        )

    return documents
