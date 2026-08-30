from collections.abc import Callable

from analysis.symbol_handlers.classes import handle_class
from analysis.symbol_handlers.c_callable import (
    handle_declaration as handle_c_declaration,
    handle_function as handle_c_function,
    handle_method as handle_c_method,
)
from analysis.symbol_handlers.c_types import handle_namespace, handle_type, handle_variable
from analysis.symbol_handlers.cs_class import handle_cs_class
from analysis.symbol_handlers.cs_interface import handle_cs_interface
from analysis.symbol_handlers.cs_method import handle_cs_method
from analysis.symbol_handlers.cs_property import handle_cs_field, handle_cs_property
from analysis.symbol_handlers.function import handle_function
from analysis.symbol_handlers.go_function import (
    handle_go_function,
    handle_go_method,
    handle_go_type_spec,
)
from analysis.symbol_handlers.interface import handle_interface
from analysis.symbol_handlers.java_enum import handle_java_enum
from analysis.symbol_handlers.java_field import handle_java_field
from analysis.symbol_handlers.java_interface import handle_java_interface
from analysis.symbol_handlers.java_method import handle_java_method
from analysis.symbol_handlers.java_record import handle_java_record
from analysis.symbol_handlers.java_class import handle_java_class
from analysis.symbol_handlers.method import handle_method
from analysis.symbol_handlers.python_function import handle_python_function
from analysis.symbol_handlers.rust_const import handle_rust_const
from analysis.symbol_handlers.rust_enum import handle_rust_enum
from analysis.symbol_handlers.rust_function import handle_rust_function
from analysis.symbol_handlers.rust_mod import handle_rust_mod
from analysis.symbol_handlers.rust_struct import handle_rust_struct
from analysis.symbol_handlers.rust_trait import handle_rust_trait
from analysis.symbol_handlers.rust_type import handle_rust_type
from analysis.symbol_handlers.type_alias import handle_type_alias
from analysis.symbol_handlers.variable import handle_variable_declarator
from models.entities.symbols import Symbol

SymbolHandler = Callable[..., "Symbol | None"]

# Languages sharing the tree-sitter-typescript grammars and, with it,
# one set of extraction handlers.
TYPESCRIPT_FAMILY = ("typescript", "tsx", "javascript", "jsx")

# Handlers are keyed by tree-sitter node type, which differs per grammar,
# so every language gets its own handler table.
_TS_NODE_HANDLERS: dict[str, SymbolHandler] = {
    "function_declaration": handle_function,
    "class_declaration": handle_class,
    "method_definition": handle_method,
    "variable_declarator": handle_variable_declarator,
    "interface_declaration": handle_interface,
    "type_alias_declaration": handle_type_alias,
}

SYMBOL_HANDLERS_BY_LANGUAGE: dict[str, dict[str, SymbolHandler]] = {
    language: dict(_TS_NODE_HANDLERS) for language in TYPESCRIPT_FAMILY
}

SYMBOL_HANDLERS_BY_LANGUAGE["go"] = {
    "function_declaration": handle_go_function,
    "method_declaration": handle_go_method,
    "type_spec": handle_go_type_spec,
}

SYMBOL_HANDLERS_BY_LANGUAGE["python"] = {
    "function_definition": handle_python_function,
    "class_definition": handle_class,
}

SYMBOL_HANDLERS_BY_LANGUAGE["java"] = {
    "class_declaration": handle_java_class,
    "interface_declaration": handle_java_interface,
    "enum_declaration": handle_java_enum,
    "record_declaration": handle_java_record,
    "method_declaration": handle_java_method,
    "constructor_declaration": handle_java_method,
    "field_declaration": handle_java_field,
}

# `impl_item` (`impl Trait for Type`) is deliberately absent: it is a
# standalone top-level node, not a declaration of a new type, so giving
# it a handler here would either mint a duplicate CLASS symbol
# colliding on stable_key with the struct/enum declaration, or (if
# registered but returning None) block the reference walker from
# descending into its methods. Its IMPLEMENTS relationship is produced
# by a dedicated pass (see `analysis.languages.LanguageProfile.impl_node`).
SYMBOL_HANDLERS_BY_LANGUAGE["csharp"] = {
    "class_declaration": handle_cs_class,
    "struct_declaration": handle_cs_class,
    "enum_declaration": handle_cs_class,
    "record_declaration": handle_cs_class,
    "interface_declaration": handle_cs_interface,
    "method_declaration": handle_cs_method,
    "constructor_declaration": handle_cs_method,
    "property_declaration": handle_cs_property,
    "field_declaration": handle_cs_field,
}

SYMBOL_HANDLERS_BY_LANGUAGE["rust"] = {
    "function_item": handle_rust_function,
    "function_signature_item": handle_rust_function,
    "struct_item": handle_rust_struct,
    "enum_item": handle_rust_enum,
    "trait_item": handle_rust_trait,
    "type_item": handle_rust_type,
    "const_item": handle_rust_const,
    "mod_item": handle_rust_mod,
}

SYMBOL_HANDLERS_BY_LANGUAGE["c"] = {
    "function_definition": handle_c_function,
    "declaration": handle_c_declaration,
    "struct_specifier": handle_type,
    "enum_specifier": handle_type,
    "union_specifier": handle_type,
    "type_definition": handle_type,
    "init_declarator": handle_variable,
}

SYMBOL_HANDLERS_BY_LANGUAGE["cpp"] = {
    "function_definition": handle_c_function,
    "declaration": handle_c_declaration,
    "class_specifier": handle_type,
    "struct_specifier": handle_type,
    "enum_specifier": handle_type,
    "namespace_definition": handle_namespace,
    "field_declaration": handle_c_method,
}


def symbol_handlers_for(language: str) -> dict[str, SymbolHandler]:
    return SYMBOL_HANDLERS_BY_LANGUAGE.get(language, {})
