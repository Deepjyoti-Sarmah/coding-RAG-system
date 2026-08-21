from models.entities.reference_kind import ReferenceKind
from models.entities.resolved_reference import ResolutionStatus, ResolvedReference
from models.relationships.relationship_kind import RelationshipKind
from models.relationships.relationships import Relationship


def build_relationships(
    *,
    resolved_references: list[ResolvedReference],
) -> list[Relationship]:

    relationships: list[Relationship] = []

    for resolved in resolved_references:
        relationship = build_call_relationship(
            resolved_reference=resolved,
        )

        if relationship is None:
            continue

        relationships.append(relationship)

    return relationships


def build_call_relationship(
    *,
    resolved_reference: ResolvedReference,
) -> Relationship | None:

    reference = resolved_reference.reference

    if reference.kind != ReferenceKind.CALL:
        return None

    if resolved_reference.status != ResolutionStatus.RESOLVED:
        return None

    return Relationship(
        source_symbol_id=reference.owner_symbol_id,
        target_symbol_id=resolved_reference.target_symbol.symbol_id,
        kind=RelationshipKind.CALLS,
    )
