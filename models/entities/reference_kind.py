from enum import Enum


class ReferenceKind(Enum):
    CALL = "call"
    IDENTIFIER = "identifier"
    MEMBER_ACCESS = "member_access"
    EXTENDS = "extends"
    IMPLEMENTS = "implements"
    HAS_TYPE = "has_type"
    RETURNS = "returns"
