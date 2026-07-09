from enum import Enum


class SymbolKind(Enum):
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    INTERFACE = "interface"
    TYPE_ALIAS = "type_alias"
    VARIABLE = "variable"
