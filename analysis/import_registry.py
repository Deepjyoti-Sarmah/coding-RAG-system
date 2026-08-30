from collections.abc import Callable

from analysis.import_handlers.default import handle_default_import
from analysis.import_handlers.cs_imports import handle_cs_using
from analysis.import_handlers.c_include import handle_c_include
from analysis.import_handlers.go_imports import handle_go_import
from analysis.import_handlers.java_imports import handle_java_import
from analysis.import_handlers.named import handle_import_specifier
from analysis.import_handlers.namespace import handle_namespace_import
from analysis.import_handlers.python_imports import (
    handle_python_from_import,
    handle_python_import,
)
from analysis.import_handlers.rust_imports import handle_rust_use
from analysis.registry import TYPESCRIPT_FAMILY
from models.entities.import_references import ImportReference

# Handlers may return one reference or several (a Python
# `from x import a, b` line yields multiple); import_extractor normalizes.
ImportHandler = Callable[..., "ImportReference | list[ImportReference] | None"]

_TS_IMPORT_HANDLERS: dict[str, ImportHandler] = {
    "import_specifier": handle_import_specifier,
    "import_clause": handle_default_import,
    "namespace_import": handle_namespace_import,
}

IMPORT_HANDLERS_BY_LANGUAGE: dict[str, dict[str, ImportHandler]] = {
    language: dict(_TS_IMPORT_HANDLERS) for language in TYPESCRIPT_FAMILY
}

IMPORT_HANDLERS_BY_LANGUAGE["go"] = {
    "import_declaration": handle_go_import,
}

IMPORT_HANDLERS_BY_LANGUAGE["python"] = {
    "import_statement": handle_python_import,
    "import_from_statement": handle_python_from_import,
}

IMPORT_HANDLERS_BY_LANGUAGE["java"] = {
    "import_declaration": handle_java_import,
}

IMPORT_HANDLERS_BY_LANGUAGE["rust"] = {
    "use_declaration": handle_rust_use,
}

IMPORT_HANDLERS_BY_LANGUAGE["csharp"] = {
    "using_directive": handle_cs_using,
}

IMPORT_HANDLERS_BY_LANGUAGE["c"] = {"preproc_include": handle_c_include}
IMPORT_HANDLERS_BY_LANGUAGE["cpp"] = {"preproc_include": handle_c_include}


def import_handlers_for(language: str) -> dict[str, ImportHandler]:
    return IMPORT_HANDLERS_BY_LANGUAGE.get(language, {})
