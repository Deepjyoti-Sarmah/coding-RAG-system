from dataclasses import dataclass

from models.entities.references import Reference
from models.entities.symbols import Symbol


@dataclass(slots=True)
class ResolvedReference:
    reference: Reference
    target_symbol: Symbol
