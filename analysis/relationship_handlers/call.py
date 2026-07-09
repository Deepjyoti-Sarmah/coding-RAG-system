from tree_sitter import Node

from analysis.semantic.resolve_call_target import (
    resolve_call_target,
)
from indexing.symbol_index import SymbolIndex
from models.entities.symbol import Symbol
from models.relationships.relationship import Relationship
from models.relationships.relationship_kind import RelationshipKind


def handle_call(
    *,
    node: Node,
    current_symbol: Symbol,
    symbol_index: SymbolIndex,
    relationships: list[Relationship],
):
    function_node = node.child_by_field_name("function")

    if function_node is None:
        return

    # function_name = function_node.text.decode("utf-8")
    function_name = resolve_call_target(function_node)

    if function_name is None:
        return

    targets = symbol_index.lookup(function_name)

    for target in targets:
        # if target.symbol_id == current_symbol.symbol_id:
        #     continue

        relationships.append(
            Relationship(
                source_symbol_id=current_symbol.symbol_id,
                target_symbol_id=target.symbol_id,
                kind=RelationshipKind.CALLS,
            )
        )
