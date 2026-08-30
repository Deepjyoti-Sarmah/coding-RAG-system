"""Module specifier -> candidate repo-relative paths, per language.

Resolution policy is the only truly language-specific part of import
resolution; `import_resolver.py` just probes candidates against the
document index. Each language registers a resolver function here.
"""

import posixpath
from collections.abc import Callable

Resolver = Callable[[str, str], list[str]]

_TYPESCRIPT_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx")
_PYTHON_EXTENSIONS = (".py",)


def _resolve_typescript(module_path: str, importing_directory: str) -> list[str]:
    if not module_path.startswith(("./", "../")):
        return []

    joined = posixpath.normpath(
        posixpath.join(importing_directory, module_path)
    )

    if posixpath.splitext(joined)[1]:
        return [joined]

    return [joined + extension for extension in _TYPESCRIPT_EXTENSIONS]


def _resolve_python(module_path: str, importing_directory: str) -> list[str]:
    if not module_path:
        return []

    # Relative imports: leading dots climb one directory per dot after
    # the first (`.` = current package, `..` = parent).
    if module_path.startswith("."):
        levels = len(module_path) - len(module_path.lstrip("."))
        remainder = module_path[levels:]

        base = importing_directory
        for _ in range(levels - 1):
            base = posixpath.dirname(base)

        if not remainder:
            # Bare `from . import x` targets the package __init__.
            joined = posixpath.join(base, "__init__")
        else:
            joined = posixpath.normpath(
                posixpath.join(base, *remainder.split("."))
            )
    else:
        # Absolute imports resolve against the repo root (the assumed
        # import root); package paths map dots to slashes.
        joined = module_path.replace(".", "/")

    return [joined + extension for extension in _PYTHON_EXTENSIONS]


def _resolve_go(module_path: str, importing_directory: str) -> list[str]:
    """Import paths resolve against the repo root (the assumed module
    root): `myrepo/auth` -> `myrepo/auth.go`. No go.mod prefix stripping
    in v1; external modules simply do not resolve."""
    if not module_path:
        return []

    return [module_path + ".go"]


_JAVA_SOURCE_ROOTS = ("src/main/java/", "src/test/java/", "")


def _resolve_java(module_path: str, importing_directory: str) -> list[str]:
    """Import paths are fully-qualified class names: `com.foo.Bar` maps
    to `com/foo/Bar.java`. Wildcard imports (`com.foo.*`) do not resolve
    to a single file in v1.

    No knowledge of the *importing* file's source root is available
    here, so candidates are probed under the conventional Maven/Gradle
    roots and the repo root, in that order. Multi-module Gradle layouts
    (root/<module>/src/main/java/...) and jar-packaged dependencies are
    out of scope; only same-repo, single-module sources resolve.
    """
    if not module_path or module_path.endswith("*"):
        return []

    relative = module_path.replace(".", "/") + ".java"

    return [root + relative for root in _JAVA_SOURCE_ROOTS]


RESOLVERS: dict[str, Resolver] = {
    "typescript": _resolve_typescript,
    "tsx": _resolve_typescript,
    "javascript": _resolve_typescript,
    "jsx": _resolve_typescript,
    "python": _resolve_python,
    "go": _resolve_go,
    "java": _resolve_java,
}


def resolve_module_path(
    *,
    module_path: str,
    importing_directory: str,
    language: str = "typescript",
) -> list[str]:
    """Return candidate repo-relative paths in deterministic order."""
    resolver = RESOLVERS.get(language)

    if resolver is None:
        return []

    return resolver(module_path, importing_directory)
