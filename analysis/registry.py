from collections.abc import Callable

from analysis.symbol_handlers.classes import handle_class
from analysis.symbol_handlers.function import handle_function
from analysis.symbol_handlers.go_function import (
    handle_go_function,
    handle_go_method,
    handle_go_type_spec,
)
from analysis.symbol_handlers.interface import handle_interface
from analysis.symbol_handlers.method import handle_method
from analysis.symbol_handlers.python_function import handle_python_function
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


def symbol_handlers_for(language: str) -> dict[str, SymbolHandler]:
    return SYMBOL_HANDLERS_BY_LANGUAGE.get(language, {})
