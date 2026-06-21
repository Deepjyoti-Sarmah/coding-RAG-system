from pathlib import Path

from config import EXCLUDE_DIRS, INCLUDE_EXTENSIONS, MAX_FILE_SIZE_BYTES


def is_inside_excluded_dir(file_path: Path) -> bool:
    return any(part in EXCLUDE_DIRS for part in file_path.parts)


def should_skip_file(file_path: Path) -> bool:
    if file_path.suffix.lower() not in INCLUDE_EXTENSIONS:
        return True

    if file_path.stat().st_size > MAX_FILE_SIZE_BYTES:
        return True

    return False


def load_code_files(root_dir: str) -> list[dict]:
    root_path = Path(root_dir)
    documents = []

    for file_path in root_path.rglob("*"):
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

        documents.append(
            {
                "path": str(file_path),
                "relative_path": str(file_path.relative_to(root_path)),
                "extension": file_path.suffix.lower(),
                "content": content,
            }
        )

    return documents
