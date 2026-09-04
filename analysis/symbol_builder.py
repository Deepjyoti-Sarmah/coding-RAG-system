from uuid import uuid4

from tree_sitter import Node

from analysis.fingerprints import (
    build_stable_key,
    compute_content_hash,
    compute_signature_hash,
)
from analysis.signature import extract_signature
from models.common.source_location import SourceLocation
from models.entities.documents import Document
from models.entities.symbol_kind import SymbolKind
from models.entities.symbols import Symbol
from parsing.node_text import node_text


def build_symbol(
    *,
    node: Node,
    name: str,
    kind: SymbolKind,
    document: Document,
    owner: Symbol | None = None,
    identity_discriminator: str = "",
    qualified_name_override: str | None = None,
    decorators: tuple[str, ...] = (),
) -> Symbol:

    content = node_text(node)

    qualified_name = qualified_name_override or (
        f"{owner.qualified_name}.{name}" if owner is not None else name
    )

    signature = extract_signature(node=node, kind=kind)

    return Symbol(
        symbol_id=str(uuid4()),
        document_id=document.document_id,
        name=name,
        kind=kind,
        relative_path=document.relative_path,
        location=SourceLocation(
            start_line=node.start_point.row + 1,
            end_line=node.end_point.row + 1,
            start_byte=node.start_byte,
            end_byte=node.end_byte,
        ),
        content=content,
        parent_symbol_id=(owner.symbol_id if owner else None),
        qualified_name=qualified_name,
        content_hash=compute_content_hash(content),
        signature_hash=compute_signature_hash(signature),
        stable_key=build_stable_key(
            relative_path=document.relative_path,
            language=document.language,
            qualified_name=qualified_name,
            kind=kind,
            identity_discriminator=identity_discriminator,
        ),
        decorators=decorators,
    )
