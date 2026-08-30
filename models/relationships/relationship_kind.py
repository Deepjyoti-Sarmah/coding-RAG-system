from enum import Enum


class RelationshipKind(Enum):
    CALLS = "calls"
    EXTENDS = "extends"
    IMPLEMENTS = "implements"
    DECLARES = "declares"
    DEFINITION_OF = "definition_of"
