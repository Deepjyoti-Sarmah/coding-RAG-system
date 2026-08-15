from tree_sitter import Node, Tree

from analysis.export_registry import EXPORT_HANDLERS
from models.entities.documents import Document
from models.entities.exports import Export


def extract_exports(
    *,
    tree: Tree,
    document: Document,
) -> list[Export]:

    results: list[Export] = []

    walk(
        node=tree.root_node,
        document=document,
        results=results,
    )

    return results


def walk(
    *,
    node: Node,
    document: Document,
    results: list[Export],
):
    exports = visit(
        node=node,
        document=document,
    )

    if exports:
        results.extend(exports)

    for child in node.children:
        walk(
            node=child,
            document=document,
            results=results,
        )


def visit(
    *,
    node: Node,
    document: Document,
) -> list[Export] | None:

    handler = EXPORT_HANDLERS.get(node.type)

    if handler is None:
        return None

    return handler(
        node=node,
        document=document,
    )
