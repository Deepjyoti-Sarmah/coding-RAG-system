from analysis.semantic.cpp_overload import candidate_compatible, is_cpp_symbol
from analysis.semantic.import_symbol_resolver import resolve_exported_symbol
from analysis.semantic.name_resolver import (
    build_resolved_reference,
    resolve_in_scope,
    resolve_name_in_scopes,
    resolve_via_import,
    resolve_via_wildcard_import,
)
from indexing.export_index import ExportIndex
from indexing.symbol_index import SymbolIndex
from models.entities.references import Reference
from models.entities.resolved_import_reference import ResolvedImportReference
from models.entities.resolved_reference import ResolutionStatus, ResolvedReference
from models.entities.symbol_kind import SymbolKind
from models.entities.symbols import Symbol


def resolve_member_reference(
    *,
    reference: Reference,
    symbol_index: SymbolIndex,
    export_index: ExportIndex,
    resolved_import_references: list[ResolvedImportReference],
) -> ResolvedReference:

    path = reference.path

    if len(path) < 2:
        return _unresolved(reference)

    base = path[0]
    member = path[-1]

    # Intermediate members cannot be verified without type information.
    if len(path) > 2:
        return _unresolved(reference)

    if base == "this":
        return _resolve_this_member(
            reference=reference,
            member=member,
            symbol_index=symbol_index,
        )

    namespace_import = _find_namespace_import(
        reference=reference,
        base=base,
        resolved_import_references=resolved_import_references,
    )

    if namespace_import is not None:
        target = resolve_exported_symbol(
            document_id=namespace_import.target_document.document_id,
            exported_name=member,
            export_index=export_index,
            symbol_index=symbol_index,
        )

        if target is None:
            return _unresolved(reference)

        return build_resolved_reference(
            reference,
            (ResolutionStatus.RESOLVED, target),
        )

    base_result = resolve_name_in_scopes(
        name=base,
        reference=reference,
        symbol_index=symbol_index,
    )

    if base_result is None:
        base_result = resolve_via_import(
            name=base,
            reference=reference,
            resolved_import_references=resolved_import_references,
        )

    if base_result is None:
        base_result = resolve_via_wildcard_import(
            name=base,
            reference=reference,
            resolved_import_references=resolved_import_references,
            export_index=export_index,
            symbol_index=symbol_index,
        )

    if base_result is not None:
        status, base_symbol = base_result

        if (
            status == ResolutionStatus.RESOLVED
            and base_symbol.kind == SymbolKind.CLASS
        ):
            children = [
                child for child in symbol_index.lookup_children(base_symbol.symbol_id)
                if child.name == member and child.document_id == base_symbol.document_id
            ]
            if children and is_cpp_symbol(base_symbol):
                compatible = [child for child in children if candidate_compatible(child, reference)]
                groups: dict[str, list[Symbol]] = {}
                for child in compatible:
                    groups.setdefault(child.stable_key.split("|", 1)[1], []).append(child)
                compatible = [
                    next((candidate for candidate in group if "{" not in candidate.content), group[0])
                    for group in groups.values()
                ]
                if len(compatible) == 1:
                    return build_resolved_reference(
                        reference, (ResolutionStatus.RESOLVED, compatible[0])
                    )
                return _unresolved(reference)

            member_result = resolve_in_scope(
                name=member,
                parent_symbol_id=base_symbol.symbol_id,
                document_id=base_symbol.document_id,
                symbol_index=symbol_index,
            )

            if member_result is not None:
                return build_resolved_reference(reference, member_result)

    return _unresolved(reference)


def _resolve_this_member(
    *,
    reference: Reference,
    member: str,
    symbol_index: SymbolIndex,
) -> ResolvedReference:
    class_symbol = _find_class_scope(
        owner_id=reference.owner_symbol_id,
        symbol_index=symbol_index,
    )

    if class_symbol is None:
        return _unresolved(reference)

    result = resolve_in_scope(
        name=member,
        parent_symbol_id=class_symbol.symbol_id,
        document_id=reference.document_id,
        symbol_index=symbol_index,
    )

    if result is None:
        return _unresolved(reference)

    return build_resolved_reference(reference, result)


def _find_class_scope(
    *,
    owner_id: str,
    symbol_index: SymbolIndex,
) -> Symbol | None:
    current = symbol_index.lookup_by_id(owner_id)

    while current is not None:
        if current.kind == SymbolKind.CLASS:
            return current

        current = (
            symbol_index.lookup_by_id(current.parent_symbol_id)
            if current.parent_symbol_id is not None
            else None
        )

    return None


def _find_namespace_import(
    *,
    reference: Reference,
    base: str,
    resolved_import_references: list[ResolvedImportReference],
) -> ResolvedImportReference | None:
    matches = [
        resolved_import
        for resolved_import in resolved_import_references
        if resolved_import.import_reference.document_id == reference.document_id
        and resolved_import.import_reference.local_name == base
        and resolved_import.import_reference.imported_name == "*"
    ]

    if len(matches) == 1:
        return matches[0]

    return None


def _unresolved(reference: Reference) -> ResolvedReference:
    return ResolvedReference(
        reference=reference,
        status=ResolutionStatus.UNRESOLVED,
    )
