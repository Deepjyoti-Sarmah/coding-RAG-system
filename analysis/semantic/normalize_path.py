import posixpath

SUPPORTED_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx")


def is_relative_import(module_path: str) -> bool:
    return module_path.startswith(("./", "../"))


def resolve_module_path(
    *,
    module_path: str,
    importing_directory: str,
) -> list[str]:
    """Return candidate repo-relative paths in deterministic order.

    Only relative module paths (./ or ../) are supported. Bare module
    specifiers like "lodash" are out of scope for v1.
    """

    if not is_relative_import(module_path):
        return []

    joined = posixpath.normpath(
        posixpath.join(importing_directory, module_path)
    )

    if posixpath.splitext(joined)[1]:
        return [joined]

    return [joined + extension for extension in SUPPORTED_EXTENSIONS]
