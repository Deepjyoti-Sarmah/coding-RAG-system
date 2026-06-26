from uuid import uuid4
from tree_sitter import Node

from models.document import Document
from models.symbol import Symbol
from models.symbol_kind import SymbolKind


def build_symbol(
    *,
    node: Node,
    name: str,
    kind: SymbolKind,
    document: Document,
) -> Symbol:

    return Symbol(
        symbol_id=str(uuid4()),
        document_id=document.document_id,
        name=name,
        kind=kind,
        relative_path=document.relative_path,
        start_line=node.start_point.row + 1,
        end_line=node.end_point.row + 1,
        content=node.text.decode("utf-8"),
    )
