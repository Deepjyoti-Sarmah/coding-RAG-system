from dataclasses import dataclass
from enum import Enum

from models.entities.references import Reference
from models.entities.symbols import Symbol


class ResolutionStatus(Enum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    AMBIGUOUS = "ambiguous"


@dataclass(slots=True)
class ResolvedReference:
    reference: Reference
    status: ResolutionStatus
    target_symbol: Symbol | None = None
