from enum import Enum


class ReferenceKind(Enum):
    CALL = "call"
    IDENTIFIER = "identifier"
    MEMBER_ACCESS = "member_access"
    IMPORT = "import"
    TYPE = "type"
