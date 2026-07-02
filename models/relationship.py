from dataclasses import dataclass

from models.relationship_kind import RelationshipKind


@dataclass(slots=True)
class Relationship:
    source_symbol_id: str
    target_symbol_id: str

    source_name: str
    target_name: str

    kind: RelationshipKind
