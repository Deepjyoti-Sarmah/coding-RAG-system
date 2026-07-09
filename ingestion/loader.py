from pathlib import Path
from uuid import uuid4

from config import (
    EXCLUDE_DIRS,
    INCLUDE_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
)
from ingestion.language import detect_language
from models.entities.document import Document


def is_inside_excluded_dir(file_path: Path) -> bool:
    return any(part in EXCLUDE_DIRS for part in file_path.parts)


def should_skip_file(file_path: Path) -> bool:
    if file_path.suffix.lower() not in INCLUDE_EXTENSIONS:
        return True

    if file_path.stat().st_size > MAX_FILE_SIZE_BYTES:
        return True

    return False


def load_code_files(path: str) -> list[Document]:
    root_path = Path(path).resolve()
    documents: list[Document] = []

    is_single_file = root_path.is_file()

    if is_single_file:
        files = [root_path]
    else:
        files = root_path.rglob("*")

    for file_path in files:
        if not file_path.is_file():
            continue

        if is_inside_excluded_dir(file_path):
            continue

        if should_skip_file(file_path):
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"Skipping {file_path}: {e}")
            continue

        relative_path = (
            file_path.name if is_single_file else str(file_path.relative_to(root_path))
        )

        documents.append(
            Document(
                document_id=str(uuid4()),
                absolute_path=str(file_path.resolve()),
                relative_path=relative_path,
                file_name=file_path.name,
                extension=file_path.suffix.lower(),
                language=detect_language(file_path.suffix.lower()),
                size_bytes=file_path.stat().st_size,
                line_count=len(content.splitlines()),
                content=content,
            )
        )

    return documents
