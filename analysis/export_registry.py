from collections.abc import Callable

from analysis.export_handlers.c_local import handle_c_export
from analysis.export_handlers.cs_exports import handle_cs_exports
from analysis.export_handlers.declaration import handle_export_statement
from analysis.export_handlers.go_exports import handle_go_exports
from analysis.export_handlers.java_exports import handle_java_exports
from analysis.export_handlers.python_exports import handle_python_top_level
from analysis.export_handlers.re_export import handle_re_export
from analysis.export_handlers.rust_exports import handle_rust_exports
from analysis.export_handlers.specifier import handle_export_specifier
from analysis.registry import TYPESCRIPT_FAMILY
from models.entities.exports import Export

ExportHandler = Callable[..., "list[Export] | None"]

def _ts_export_statement(*, node, document):
    # Try normal export first, then re-export (export * from / export {x} from)
    result = handle_export_statement(node=node, document=document)
    if result is not None:
        return result
    return handle_re_export(node=node, document=document)


_TS_EXPORT_HANDLERS: dict[str, ExportHandler] = {
    "export_statement": _ts_export_statement,
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

EXPORT_HANDLERS_BY_LANGUAGE["csharp"] = {
    "class_declaration": handle_cs_exports,
    "struct_declaration": handle_cs_exports,
    "enum_declaration": handle_cs_exports,
    "record_declaration": handle_cs_exports,
    "interface_declaration": handle_cs_exports,
}

EXPORT_HANDLERS_BY_LANGUAGE["rust"] = {
    "function_item": handle_rust_exports,
    "struct_item": handle_rust_exports,
    "enum_item": handle_rust_exports,
    "trait_item": handle_rust_exports,
    "type_item": handle_rust_exports,
    "const_item": handle_rust_exports,
    "mod_item": handle_rust_exports,
}

EXPORT_HANDLERS_BY_LANGUAGE["c"] = {
    "function_definition": handle_c_export,
    "declaration": handle_c_export,
    "struct_specifier": handle_c_export,
    "enum_specifier": handle_c_export,
    "union_specifier": handle_c_export,
    "type_definition": handle_c_export,
}
EXPORT_HANDLERS_BY_LANGUAGE["cpp"] = {
    "function_definition": handle_c_export,
    "declaration": handle_c_export,
    "class_specifier": handle_c_export,
    "struct_specifier": handle_c_export,
    "enum_specifier": handle_c_export,
    "namespace_definition": handle_c_export,
}


def export_handlers_for(language: str) -> dict[str, ExportHandler]:
    return EXPORT_HANDLERS_BY_LANGUAGE.get(language, {})
