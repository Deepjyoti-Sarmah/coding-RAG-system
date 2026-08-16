from dataclasses import dataclass

from models.relationships.relationship_kind import RelationshipKind


@dataclass(slots=True)
class Relationship:
    source_symbol_id: str
    target_symbol_id: str

    kind: RelationshipKind

    @property
    def key(self) -> tuple[str, str, RelationshipKind]:
        return (self.source_symbol_id, self.target_symbol_id, self.kind)
