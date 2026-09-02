from models.entities.reference_kind import ReferenceKind
from models.entities.resolved_reference import ResolutionStatus, ResolvedReference
from models.entities.symbols import Symbol
from models.relationships.relationship_kind import RelationshipKind
from models.relationships.relationships import Relationship

_RELATIONSHIP_BY_REFERENCE = {
    ReferenceKind.CALL: RelationshipKind.CALLS,
    ReferenceKind.EXTENDS: RelationshipKind.EXTENDS,
    ReferenceKind.IMPLEMENTS: RelationshipKind.IMPLEMENTS,
    ReferenceKind.HAS_TYPE: RelationshipKind.HAS_TYPE,
    ReferenceKind.RETURNS: RelationshipKind.RETURNS,
}


def build_relationships(
    *,
    resolved_references: list[ResolvedReference],
    symbols: list[Symbol] | None = None,
) -> list[Relationship]:
    """Fold resolved references and symbol ownership into deduped edges.

    Duplicates are folded here rather than left for `CodeGraph` to drop, so
    that `BuildResult.relationships` carries correct counts before it reaches
    either the graph or the store.
    """

    relationships: dict[tuple[str, str, RelationshipKind], Relationship] = {}

    for resolved in resolved_references:
        relationship = build_relationship(
            resolved_reference=resolved,
        )

        if relationship is None:
            continue

        _accumulate(relationships, relationship)

    for relationship in build_declares_relationships(symbols=symbols or []):
        _accumulate(relationships, relationship)

    for relationship in build_definition_relationships(symbols=symbols or []):
        _accumulate(relationships, relationship)

    return list(relationships.values())


def _accumulate(
    relationships: dict[tuple[str, str, RelationshipKind], Relationship],
    relationship: Relationship,
) -> None:
    existing = relationships.get(relationship.key)

    if existing is None:
        relationships[relationship.key] = relationship
        return

    existing.count += relationship.count


def build_declares_relationships(*, symbols: list[Symbol]) -> list[Relationship]:
    """Materialise parent/child ownership as DECLARES edges.

    Only emitted when the parent is part of the same symbol set: the
    incremental path builds one batch at a time, and an edge pointing at a
    symbol outside the batch would dangle.
    """
    symbol_ids = {symbol.symbol_id for symbol in symbols}

    return [
        Relationship(
            source_symbol_id=symbol.parent_symbol_id,
            target_symbol_id=symbol.symbol_id,
            kind=RelationshipKind.DECLARES,
        )
        for symbol in symbols
        if symbol.parent_symbol_id is not None
        and symbol.parent_symbol_id in symbol_ids
    ]


def build_definition_relationships(*, symbols: list[Symbol]) -> list[Relationship]:
    """Link C/C++ function bodies to matching header declarations.

    The stable-key suffix deliberately excludes the source path, while still
    retaining language, ownership, kind, and callable discriminator.
    """
    declarations = {
        symbol.stable_key.split("|", 1)[1]: symbol
        for symbol in symbols
        if symbol.stable_key.split("|", 1)[0].endswith((".h", ".hpp", ".hh", ".hxx"))
        and "{" not in symbol.content
    }
    links: list[Relationship] = []
    for symbol in symbols:
        if not symbol.stable_key.split("|", 1)[0].endswith((".c", ".cpp", ".cc", ".cxx")):
            continue
        if "{" not in symbol.content:
            continue
        suffix = symbol.stable_key.split("|", 1)[1]
        declaration = declarations.get(suffix)
        if declaration is not None:
            links.append(Relationship(symbol.symbol_id, declaration.symbol_id, RelationshipKind.DEFINITION_OF))
    return links


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
