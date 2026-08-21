from tree_sitter import Node

from analysis.export_builder import build_export
from models.entities.documents import Document
from models.entities.exports import Export

DECLARATION_NODE_TYPES = {
    "function_declaration",
    "class_declaration",
    "function_expression",
    "class_expression",
    "lexical_declaration",
    "identifier",
}


def handle_export_statement(
    *,
    node: Node,
    document: Document,
) -> list[Export] | None:

    if node.type != "export_statement":
        return None

    # export { a, b } — handled by the export_specifier handler
    if any(child.type == "export_clause" for child in node.children):
        return None

    # export { a } from "./x" / export * from "./x" — deferred until
    # cross-file re-export resolution exists
    if node.child_by_field_name("source") is not None:
        return None

    is_default = any(child.type == "default" for child in node.children)

    declaration = _declaration_child(node)

    if declaration is None:
        return None

    names = _declaration_names(declaration)

    if is_default:
        exports = [
            build_export(
                document=document,
                exported_name="default",
                symbol_name=name,
                node=node,
            )
            for name in names
        ]

        if not exports:
            return [
                build_export(
                    document=document,
                    exported_name="default",
                    symbol_name=None,
                    node=node,
                )
            ]

        return exports

    return [
        build_export(
            document=document,
            exported_name=name,
            symbol_name=name,
            node=node,
        )
        for name in names
    ]


def _declaration_child(node: Node) -> Node | None:
    for child in node.children:
        if child.type in DECLARATION_NODE_TYPES:
            return child

    return None


def _declaration_names(node: Node) -> list[str]:
    if node.type in ("function_declaration", "class_declaration"):
        return _name_from_field(node)

    if node.type in ("function_expression", "class_expression"):
        return _name_from_field(node)

    if node.type == "lexical_declaration":
        return _lexical_declaration_names(node)

    if node.type == "identifier":
        return [node.text.decode("utf-8")]

    return []


def _name_from_field(node: Node) -> list[str]:
    name = node.child_by_field_name("name")

    if name is None:
        return []

    return [name.text.decode("utf-8")]


def _lexical_declaration_names(node: Node) -> list[str]:
    names: list[str] = []

    for declarator in node.children:
        if declarator.type != "variable_declarator":
            continue

        name = declarator.child_by_field_name("name")

        if name is not None and name.type == "identifier":
            names.append(name.text.decode("utf-8"))

    return names
