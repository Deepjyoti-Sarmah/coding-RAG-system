from collections.abc import Callable

from analysis.export_handlers.declaration import handle_export_statement
from analysis.export_handlers.go_exports import handle_go_exports
from analysis.export_handlers.java_exports import handle_java_exports
from analysis.export_handlers.python_exports import handle_python_top_level
from analysis.export_handlers.specifier import handle_export_specifier
from analysis.registry import TYPESCRIPT_FAMILY
from models.entities.exports import Export

ExportHandler = Callable[..., "list[Export] | None"]

_TS_EXPORT_HANDLERS: dict[str, ExportHandler] = {
    "export_statement": handle_export_statement,
    "export_specifier": handle_export_specifier,
}

EXPORT_HANDLERS_BY_LANGUAGE: dict[str, dict[str, ExportHandler]] = {
    language: dict(_TS_EXPORT_HANDLERS) for language in TYPESCRIPT_FAMILY
}

EXPORT_HANDLERS_BY_LANGUAGE["go"] = {
    "function_declaration": handle_go_exports,
    "method_declaration": handle_go_exports,
    "type_spec": handle_go_exports,
}

EXPORT_HANDLERS_BY_LANGUAGE["python"] = {
    "function_definition": handle_python_top_level,
    "class_definition": handle_python_top_level,
}

EXPORT_HANDLERS_BY_LANGUAGE["java"] = {
    "class_declaration": handle_java_exports,
    "interface_declaration": handle_java_exports,
    "enum_declaration": handle_java_exports,
    "record_declaration": handle_java_exports,
}


def export_handlers_for(language: str) -> dict[str, ExportHandler]:
    return EXPORT_HANDLERS_BY_LANGUAGE.get(language, {})
