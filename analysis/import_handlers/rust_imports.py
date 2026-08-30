from tree_sitter import Node

from analysis.import_builder import build_import_reference
from models.common.source_location import SourceLocation
from models.entities.documents import Document
from models.entities.import_references import ImportReference


def handle_rust_use(
    *,
    node: Node,
    document: Document,
) -> ImportReference | None:
    """`use a::b::C;` and `use a::b::C as D;`.

    Grouped imports (`use a::{b, c};`) and wildcard imports
    (`use a::*;`) are not expanded in v1 -- each would need multiple
    ImportReferences from one node, which `import_extractor` supports,
    but the grammar's nested `use_list` shapes are unbounded in depth
    and left for a follow-up rather than guessed at here.
    """
    if node.type != "use_declaration":
        return None

    target = next(
        (
            child
            for child in node.children
            if child.type in ("scoped_identifier", "identifier", "use_as_clause")
        ),
        None,
    )

    if target is None:
        return None

    if target.type == "use_as_clause":
        path_node = target.child_by_field_name("path")
        alias_node = target.child_by_field_name("alias")

        if path_node is None or alias_node is None:
            return None

        module_path = _dotted_text(path_node)
        local = _dotted_text(alias_node)
    else:
        module_path = _dotted_text(target)
        local = module_path.rsplit("::", 1)[-1]

    if not module_path:
        return None

    return build_import_reference(
        document=document,
        module_path=module_path,
        imported_name=local,
        local_name=local,
        location=SourceLocation(
            start_line=node.start_point.row + 1,
            end_line=node.end_point.row + 1,
            start_byte=node.start_byte,
            end_byte=node.end_byte,
        ),
    )


def _dotted_text(node: Node) -> str:
    raw = node.text
    return raw.decode("utf-8") if raw is not None else ""
