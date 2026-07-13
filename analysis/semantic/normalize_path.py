from pathlib import Path


def normalize_path(path: str) -> str:
    path = path.removeprefix("./")

    if "." not in Path(path).name:
        path += ".ts"

    return path
