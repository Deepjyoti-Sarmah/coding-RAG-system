from tree_sitter import Node

from analysis.import_builder import build_import_reference
from models.common.source_location import SourceLocation
from models.entities.documents import Document
from models.entities.import_references import ImportReference


def handle_go_import(
    *,
    node: Node,
    document: Document,
) -> list[ImportReference] | None:
    """`import "x"` and block form; each `import_spec` becomes one entry.

    - module_path is the raw import path string, kept verbatim.
    - local_name is the alias when present (`alias \"p\"`), else the last
      path segment (`myrepo/token` -> `token`).
    - Blank imports (`_ \"x\"`) are recorded with local name `_`.
    """
    if node.type != "import_declaration":
        return None

    # Both forms nest specs under the declaration: directly for the
    # single form, via import_spec_list for the parenthesized block.
    sources = [
        spec_child
        for group in node.children
        if group.type in ("import_spec", "import_spec_list")
        for spec_child in (
            [group] if group.type == "import_spec" else group.children
        )
        if spec_child.type == "import_spec"
    ]

    references: list[ImportReference] = []

    for spec in sources:
        path_node = spec.child_by_field_name("path")

        if path_node is None:
            continue

        module_path = _string_value(path_node)

        if not module_path:
            continue

        alias_node = spec.child_by_field_name("name")
        local = (
            node_text_of(alias_node)
            if alias_node is not None
            else module_path.rsplit("/", 1)[-1]
        )

        references.append(
            build_import_reference(
                document=document,
                module_path=module_path,
                imported_name=local,
                local_name=local,
                location=SourceLocation(
                    start_line=spec.start_point.row + 1,
                    end_line=spec.end_point.row + 1,
                    start_byte=spec.start_byte,
                    end_byte=spec.end_byte,
                ),
            )
        )

    return references


def _string_value(node: Node) -> str:
    """Strip quotes from an interpreted_string_literal."""
    text = node_text_of(node).strip()

    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        return text[1:-1]

    return text


def node_text_of(node: Node) -> str:
    raw = node.text

    return raw.decode("utf-8") if raw is not None else ""
