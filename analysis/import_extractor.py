from tree_sitter import Node, Tree

from analysis.import_registry import IMPORT_HANDLERS
from models.entities.documents import Document
from models.entities.import_references import ImportReference


def extract_imports(
    *,
    tree: Tree,
    document: Document,
) -> list[ImportReference]:

    results: list[ImportReference] = []

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
    results: list[ImportReference],
):
    reference = visit(
        node=node,
        document=document,
    )

    if reference is not None:
        results.append(reference)

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
) -> ImportReference | None:

    handler = IMPORT_HANDLERS.get(node.type)

    if handler is None:
        return None

    return handler(
        node=node,
        document=document,
    )
