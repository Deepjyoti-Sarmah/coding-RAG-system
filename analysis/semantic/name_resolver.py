from indexing.symbol_index import SymbolIndex
from models.entities.reference import Reference
from models.entities.symbol import Symbol


def resolve_symbol(
    *,
    reference: Reference,
    symbol_index: SymbolIndex,
) -> Symbol | None:
    owner = symbol_index.lookup_by_id(reference.owner_symbol_id)

    if owner is None:
        return None

    current_scope = owner

    while current_scope is not None:
        symbol = resolve_in_scope(
            name=reference.name,
            parent_symbol_id=current_scope.symbol_id,
            symbol_index=symbol_index,
        )

        if symbol is not None:
            return symbol

        if current_scope.parent_symbol_id is None:
            break

        current_scope = symbol_index.lookup_by_id(current_scope.parent_symbol_id)

    return resolve_in_scope(
        name=reference.name,
        parent_symbol_id=None,
        symbol_index=symbol_index,
    )


def resolve_in_scope(
    *,
    name: str,
    parent_symbol_id: str | None,
    symbol_index: SymbolIndex,
) -> Symbol | None:

    children = symbol_index.lookup_children(parent_symbol_id=parent_symbol_id)

    for child in children:
        if child.name == name:
            return child

    return None
