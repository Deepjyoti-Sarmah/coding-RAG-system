from dataclasses import dataclass
from enum import Enum


class SymbolKind(Enum):
    FUNCTION = "function"
    CLASS = "class"
    INTERFACE = "interface"
    TYPE_ALIAS = "type_alias"
    VARIABLE = "variable"
