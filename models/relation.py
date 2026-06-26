from dataclasses import dataclass

from models.relation_kind import RelationKind


@dataclass(slots=True)
class Relation:
    relation_id: str
    source_symbol_id: str
    target_name: str
    kind: RelationKind
