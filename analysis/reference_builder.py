from uuid import uuid4

from tree_sitter import Node

from models.common.source_location import SourceLocation
from models.entities.reference_kind import ReferenceKind
from models.entities.references import Reference
from models.entities.symbols import Symbol


def build_reference(
    *,
    node: Node,
    owner_symbol: Symbol,
    kind: ReferenceKind,
    path: tuple[str, ...],
) -> Reference:
    call_argument_count = None
    call_argument_kinds: tuple[str, ...] = ()
    call = node.parent if node.parent is not None and node.parent.type == "call_expression" else None
    if call is not None:
        arguments = next((child for child in call.children if child.type == "argument_list"), None)
        if arguments is not None:
            values = [child for child in arguments.children if child.is_named]
            call_argument_count = len(values)
            call_argument_kinds = tuple(_literal_kind(value) for value in values)
    return Reference(
        reference_id=str(uuid4()),
        document_id=owner_symbol.document_id,
        owner_symbol_id=owner_symbol.symbol_id,
        name=path[-1],
        kind=kind,
        location=SourceLocation(
            start_line=node.start_point.row + 1,
            end_line=node.end_point.row + 1,
            start_byte=node.start_byte,
            end_byte=node.end_byte,
        ),
        path=path,
        call_argument_count=call_argument_count,
        call_argument_kinds=call_argument_kinds,
    )


def _literal_kind(node: Node) -> str:
    if node.type in {"number_literal", "integer_literal"}:
        text = node.text.decode("utf-8") if node.text else ""
        return "float" if any(c in text for c in ".eE") else "integer"
    if node.type in {"string_literal", "raw_string_literal"}:
        return "string"
    if node.type in {"char_literal", "character_literal"}:
        return "character"
    if node.type in {"true", "false"}:
        return "boolean"
    if node.type in {"null", "null_literal"}:
        return "null"
    if node.type in {"cast_expression", "type_cast_expression"}:
        return "cast"
    return "unknown"
