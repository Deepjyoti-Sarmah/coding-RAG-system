from dataclasses import dataclass

from models.relationships.relationship_kind import RelationshipKind


@dataclass(slots=True)
class Relationship:
    source_symbol_id: str
    target_symbol_id: str

    kind: RelationshipKind

    # How many resolved references produced this edge. Identity is the
    # (source, target, kind) triple, so duplicates fold into one edge and
    # accumulate here rather than being discarded.
    count: int = 1

    @property
    def key(self) -> tuple[str, str, RelationshipKind]:
        return (self.source_symbol_id, self.target_symbol_id, self.kind)
