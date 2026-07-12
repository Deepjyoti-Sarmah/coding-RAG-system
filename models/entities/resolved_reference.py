from dataclasses import dataclass

from models.entities.reference import Reference
from models.entities.symbol import Symbol


@dataclass(slots=True)
class ResolvedReference:
    reference: Reference
    target_symbol: Symbol
