from indexing.symbol_index import SymbolIndex
from models.entities.references import Reference
from models.entities.resolved_import_reference import ResolvedImportReference
from models.entities.resolved_reference import ResolutionStatus, ResolvedReference
from models.entities.symbols import Symbol


def resolve_symbol(
    *,
    reference: Reference,
    symbol_index: SymbolIndex,
    resolved_import_references: list[ResolvedImportReference],
) -> ResolvedReference:
    result = resolve_name_in_scopes(
        name=reference.name,
        reference=reference,
        symbol_index=symbol_index,
    )

    if result is not None:
        return build_resolved_reference(reference, result)

    import_result = resolve_via_import(
        name=reference.name,
        reference=reference,
        resolved_import_references=resolved_import_references,
    )

    if import_result is not None:
        return build_resolved_reference(reference, import_result)

    return ResolvedReference(
        reference=reference,
        status=ResolutionStatus.UNRESOLVED,
    )


def resolve_name_in_scopes(
    *,
    name: str,
    reference: Reference,
    symbol_index: SymbolIndex,
) -> tuple[ResolutionStatus, Symbol] | None:
    owner = symbol_index.lookup_by_id(reference.owner_symbol_id)

    current_scope = owner

    while current_scope is not None:
        result = resolve_in_scope(
            name=name,
            parent_symbol_id=current_scope.symbol_id,
            document_id=reference.document_id,
            symbol_index=symbol_index,
        )

        if result is not None:
            return result

        if current_scope.parent_symbol_id is None:
            break

        current_scope = symbol_index.lookup_by_id(current_scope.parent_symbol_id)

    return resolve_in_scope(
        name=name,
        parent_symbol_id=None,
        document_id=reference.document_id,
        symbol_index=symbol_index,
    )


def resolve_via_import(
    *,
    name: str,
    reference: Reference,
    resolved_import_references: list[ResolvedImportReference],
) -> tuple[ResolutionStatus, Symbol] | None:

    candidates: dict[str, Symbol] = {}

    for resolved_import in resolved_import_references:
        import_reference = resolved_import.import_reference

        if import_reference.document_id != reference.document_id:
            continue

        if import_reference.local_name != name:
            continue

        target_symbol = resolved_import.target_symbol

        if target_symbol is None:
            continue

        candidates[target_symbol.symbol_id] = target_symbol

    if len(candidates) == 1:
        return (ResolutionStatus.RESOLVED, next(iter(candidates.values())))

    if len(candidates) > 1:
        return (ResolutionStatus.AMBIGUOUS, next(iter(candidates.values())))

    return None


def resolve_in_scope(
    *,
    name: str,
    parent_symbol_id: str | None,
    document_id: str,
    symbol_index: SymbolIndex,
) -> tuple[ResolutionStatus, Symbol] | None:
    children = symbol_index.lookup_children(parent_symbol_id=parent_symbol_id)

    matches = [
        child
        for child in children
        if child.name == name and child.document_id == document_id
    ]

    if len(matches) == 1:
        return (ResolutionStatus.RESOLVED, matches[0])

    if len(matches) > 1:
        return (ResolutionStatus.AMBIGUOUS, matches[0])

    return None


def build_resolved_reference(
    reference: Reference,
    result: tuple[ResolutionStatus, Symbol],
) -> ResolvedReference:
    status, symbol = result

    if status != ResolutionStatus.RESOLVED:
        return ResolvedReference(
            reference=reference,
            status=status,
        )

    return ResolvedReference(
        reference=reference,
        status=status,
        target_symbol=symbol,
    )
