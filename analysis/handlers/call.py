from tree_sitter import Node

from indexing.symbol_index import SymbolIndex
from models.relation_kind import RelationshipKind
from models.relationship import Relationship
from models.symbol import Symbol


def handle_call(
    node: Node,
    current_symbol: Symbol,
    symbol_index: SymbolIndex,
    relationships: list[Relationship],
):
    function_node = node.child_by_field_name("function")

    if function_node is None:
        return

    function_name = function_node.text.decode()

    targets = symbol_index.lookup(function_name)

    for target in targets:
        relationships.append(
            Relationship(
                source_symbol_id=current_symbol.symbol_id,
                target_symbol_id=target.symbol_id,
                source_name=current_symbol.name,
                target_name=target.name,
                kind=RelationshipKind.CALLS,
            )
        )
