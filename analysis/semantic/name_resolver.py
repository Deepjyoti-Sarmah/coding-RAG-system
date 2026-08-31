from analysis.semantic.cpp_overload import candidate_compatible, is_cpp_symbol
from analysis.semantic.import_symbol_resolver import resolve_exported_symbol
from indexing.export_index import ExportIndex
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
    export_index: ExportIndex | None = None,
) -> ResolvedReference:
    owner = symbol_index.lookup_by_id(reference.owner_symbol_id)
    if reference.kind.value == "call" and owner is not None and is_cpp_symbol(owner):
        cpp_result = resolve_cpp_call(reference, symbol_index, resolved_import_references)
        if cpp_result is not None:
            return build_resolved_reference(reference, cpp_result)
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

    if export_index is not None:
        wildcard_result = resolve_via_wildcard_import(
            name=reference.name,
            reference=reference,
            resolved_import_references=resolved_import_references,
            export_index=export_index,
            symbol_index=symbol_index,
        )

        if wildcard_result is not None:
            return build_resolved_reference(reference, wildcard_result)

    return ResolvedReference(
        reference=reference,
        status=ResolutionStatus.UNRESOLVED,
    )


def resolve_cpp_call(reference, symbol_index, resolved_import_references):
    candidates: dict[str, Symbol] = {}
    owner = symbol_index.lookup_by_id(reference.owner_symbol_id)
    current = owner
    while current is not None:
        for symbol in symbol_index.lookup_children(current.symbol_id):
            if symbol.name == reference.name and is_cpp_symbol(symbol):
                candidates[symbol.symbol_id] = symbol
        current = symbol_index.lookup_by_id(current.parent_symbol_id) if current.parent_symbol_id else None
    for resolved in resolved_import_references:
        imp = resolved.import_reference
        if imp.document_id != reference.document_id or imp.imported_name != "*":
            continue
        for symbol in symbol_index.lookup_by_name(reference.name):
            if symbol.document_id == resolved.target_document.document_id and is_cpp_symbol(symbol):
                candidates[symbol.symbol_id] = symbol
    compatible = [symbol for symbol in candidates.values() if candidate_compatible(symbol, reference)]
    # A header declaration and its source definition are one overload
    # candidate for call selection. Prefer the declaration as the canonical
    # target; DEFINITION_OF exposes the implementation separately.
    grouped: dict[str, list[Symbol]] = {}
    for symbol in compatible:
        grouped.setdefault(symbol.stable_key.split("|", 1)[1], []).append(symbol)
    compatible = [
        next((candidate for candidate in group if "{" not in candidate.content), group[0])
        for group in grouped.values()
    ]
    if len(compatible) == 1:
        return (ResolutionStatus.RESOLVED, compatible[0])
    if compatible:
        return (ResolutionStatus.AMBIGUOUS, compatible[0])
    return (ResolutionStatus.UNRESOLVED, owner) if candidates else None


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


def resolve_via_wildcard_import(
    *,
    name: str,
    reference: Reference,
    resolved_import_references: list[ResolvedImportReference],
    export_index: ExportIndex,
    symbol_index: SymbolIndex,
) -> tuple[ResolutionStatus, Symbol] | None:
    """Plain-identifier fallback for whole-namespace/module imports
    (C#'s `using App.Auth;`, JS's `import * as ns`): these bind
    everything the target exports rather than one name, so simple
    identifiers used unqualified need every wildcard import's target
    document checked for a matching export, not just an exact
    `local_name` match like `resolve_via_import` does.
    """
    for resolved_import in resolved_import_references:
        import_reference = resolved_import.import_reference

        if import_reference.document_id != reference.document_id:
            continue

        if import_reference.imported_name != "*":
            continue

        target = resolve_exported_symbol(
            document_id=resolved_import.target_document.document_id,
            exported_name=name,
            export_index=export_index,
            symbol_index=symbol_index,
        )

        if target is not None:
            return (ResolutionStatus.RESOLVED, target)

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
