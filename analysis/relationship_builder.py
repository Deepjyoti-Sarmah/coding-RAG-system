from models.entities.reference_kind import ReferenceKind
from models.entities.resolved_reference import ResolutionStatus, ResolvedReference
from models.relationships.relationship_kind import RelationshipKind
from models.relationships.relationships import Relationship

_RELATIONSHIP_BY_REFERENCE = {
    ReferenceKind.CALL: RelationshipKind.CALLS,
    ReferenceKind.EXTENDS: RelationshipKind.EXTENDS,
    ReferenceKind.IMPLEMENTS: RelationshipKind.IMPLEMENTS,
}


def build_relationships(
    *,
    resolved_references: list[ResolvedReference],
) -> list[Relationship]:

    relationships: list[Relationship] = []

    for resolved in resolved_references:
        relationship = build_relationship(
            resolved_reference=resolved,
        )

        if relationship is None:
            continue

        relationships.append(relationship)

    return relationships


def build_relationship(
    *,
    resolved_reference: ResolvedReference,
) -> Relationship | None:

    reference = resolved_reference.reference

    kind = _RELATIONSHIP_BY_REFERENCE.get(reference.kind)

    if kind is None:
        return None

    if resolved_reference.status != ResolutionStatus.RESOLVED:
        return None

    target_symbol = resolved_reference.target_symbol

    if target_symbol is None:
        return None

    return Relationship(
        source_symbol_id=reference.owner_symbol_id,
        target_symbol_id=target_symbol.symbol_id,
        kind=kind,
    )
