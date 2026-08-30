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
_C_EXTENSIONS = (".h", ".c")
_CPP_EXTENSIONS = (".hpp", ".hh", ".hxx", ".cpp", ".cc", ".cxx")


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


def _resolve_c_include(module_path: str, importing_directory: str, extensions: tuple[str, ...]) -> list[str]:
    if not module_path or module_path.startswith("<"):
        return []
    joined = posixpath.normpath(posixpath.join(importing_directory, module_path))
    if posixpath.splitext(joined)[1]:
        return [joined]
    return [joined + extension for extension in extensions] + [module_path + extension for extension in extensions]


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


def _resolve_rust(module_path: str, importing_directory: str) -> list[str]:
    """`crate::a::b` resolves from the crate root (assumed to be `src/`);
    `self::a` and `super::a` resolve relative to the importing module's
    directory, climbing one level per leading `super`. External crates
    (anything not starting with `crate`, `self`, or `super`) do not
    resolve -- there is no crate registry here, only this repo's own
    source tree.

    A path segment can name either a module (its own file) or an item
    declared inside its parent module's file (`crate::auth::login` is
    usually `fn login` inside `auth.rs`, not `auth/login.rs`), and
    nothing here distinguishes the two. Candidates are returned for
    both readings, full path first: `seg.rs` / `seg/mod.rs` for every
    segment, and -- when there is more than one segment -- the same
    pair one segment short, for the "last segment is an item" case.
    """
    if not module_path:
        return []

    segments = module_path.split("::")

    if segments[0] == "crate":
        base = "src"
        segments = segments[1:]
    elif segments[0] == "self":
        base = importing_directory
        segments = segments[1:]
    elif segments[0] == "super":
        base = importing_directory
        while segments and segments[0] == "super":
            base = posixpath.dirname(base)
            segments = segments[1:]
    else:
        return []

    if not segments:
        return []

    candidates: list[str] = []

    for depth in (len(segments), len(segments) - 1):
        if depth <= 0:
            continue

        relative = (
            posixpath.join(base, *segments[:depth])
            if base
            else "/".join(segments[:depth])
        )

        candidates.append(relative + ".rs")
        candidates.append(posixpath.join(relative, "mod.rs"))

    return candidates


RESOLVERS: dict[str, Resolver] = {
    "typescript": _resolve_typescript,
    "tsx": _resolve_typescript,
    "javascript": _resolve_typescript,
    "jsx": _resolve_typescript,
    "python": _resolve_python,
    "go": _resolve_go,
    "java": _resolve_java,
    "rust": _resolve_rust,
    "c": lambda module_path, importing_directory: _resolve_c_include(module_path, importing_directory, _C_EXTENSIONS),
    "cpp": lambda module_path, importing_directory: _resolve_c_include(module_path, importing_directory, _CPP_EXTENSIONS + _C_EXTENSIONS),
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
