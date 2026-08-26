from tree_sitter import Node, Tree

from analysis.export_registry import ExportHandler, export_handlers_for
from models.entities.documents import Document
from models.entities.exports import Export


def extract_exports(
    *,
    tree: Tree,
    document: Document,
) -> list[Export]:

    results: list[Export] = []
    handlers = export_handlers_for(document.language)

    walk(
        node=tree.root_node,
        document=document,
        results=results,
        handlers=handlers,
    )

    return results


def walk(
    *,
    node: Node,
    document: Document,
    results: list[Export],
    handlers: dict[str, ExportHandler],
):
    exports = visit(
        node=node,
        document=document,
        handlers=handlers,
    )

    if exports:
        results.extend(exports)

    for child in node.children:
        walk(
            node=child,
            document=document,
            results=results,
            handlers=handlers,
        )


def visit(
    *,
    node: Node,
    document: Document,
    handlers: dict[str, ExportHandler],
) -> list[Export] | None:

    handler = handlers.get(node.type)

    if handler is None:
        return None

    return handler(
        node=node,
        document=document,
    )
