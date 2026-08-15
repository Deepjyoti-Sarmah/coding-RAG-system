from indexing.export_index import ExportIndex
from indexing.symbol_index import SymbolIndex
from models.entities.resolved_import_reference import ResolvedImportReference
from models.entities.symbols import Symbol


def resolve_imported_symbol(
    *,
    resolved_import: ResolvedImportReference,
    export_index: ExportIndex,
    symbol_index: SymbolIndex,
) -> Symbol | None:

    imported_name = resolved_import.import_reference.imported_name

    # A namespace import binds the whole module, not a single symbol.
    if imported_name == "*":
        return None

    return resolve_exported_symbol(
        document_id=resolved_import.target_document.document_id,
        exported_name=imported_name,
        export_index=export_index,
        symbol_index=symbol_index,
    )


def resolve_exported_symbol(
    *,
    document_id: str,
    exported_name: str,
    export_index: ExportIndex,
    symbol_index: SymbolIndex,
) -> Symbol | None:

    exports = export_index.lookup(
        document_id=document_id,
        exported_name=exported_name,
    )

    # Missing export, or a duplicate export name — do not guess.
    if len(exports) != 1:
        return None

    symbol_name = exports[0].symbol_name

    # Anonymous default export has no module-scope symbol.
    if symbol_name is None:
        return None

    return _lookup_module_symbol(
        symbol_index=symbol_index,
        document_id=document_id,
        name=symbol_name,
    )


def _lookup_module_symbol(
    *,
    symbol_index: SymbolIndex,
    document_id: str,
    name: str,
) -> Symbol | None:

    matches = [
        symbol
        for symbol in symbol_index.lookup_by_name(name)
        if symbol.document_id == document_id and symbol.parent_symbol_id is None
    ]

    if len(matches) == 1:
        return matches[0]

    return None
