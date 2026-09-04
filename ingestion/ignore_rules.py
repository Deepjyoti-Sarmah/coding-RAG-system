from pathlib import Path
from typing import Any

import pathspec

IGNORE_FILE_NAMES = (".gitignore", ".sgignore")


class IgnoreRules:
    def __init__(self, spec: pathspec.PathSpec[Any]) -> None:  # type: ignore[type-arg]  # pyright: ignore[reportMissingTypeArgument]
        self._spec = spec

    def is_ignored(self, relative_path: str, *, is_dir: bool = False) -> bool:
        if is_dir and not relative_path.endswith("/"):
            relative_path = f"{relative_path}/"

        return self._spec.match_file(relative_path)


def load_ignore_rules(root_dir: str | Path) -> IgnoreRules:
    """Load .gitignore and .sgignore patterns from the repo root.

    Both files are honored together: .sgignore adds project-specific
    ignores on top of .gitignore rather than replacing it. Only root-level
    ignore files are read; nested per-directory ignore files are not
    supported yet.
    """
    root_path = Path(root_dir)

    if root_path.is_file():
        root_path = root_path.parent

    lines: list[str] = []

    for file_name in IGNORE_FILE_NAMES:
        ignore_file = root_path / file_name

        if ignore_file.is_file():
            lines.extend(ignore_file.read_text(encoding="utf-8").splitlines())

    return IgnoreRules(pathspec.PathSpec.from_lines("gitignore", lines))  # type: ignore[arg-type]
