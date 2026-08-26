from tree_sitter import Node, Tree

from analysis.import_registry import ImportHandler, import_handlers_for
from models.entities.documents import Document
from models.entities.import_references import ImportReference


def extract_imports(
    *,
    tree: Tree,
    document: Document,
) -> list[ImportReference]:

    results: list[ImportReference] = []
    handlers = import_handlers_for(document.language)

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
    results: list[ImportReference],
    handlers: dict[str, ImportHandler],
):
    reference = visit(
        node=node,
        document=document,
        handlers=handlers,
    )

    results.extend(reference)

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
    handlers: dict[str, ImportHandler],
) -> list[ImportReference]:

    handler = handlers.get(node.type)

    if handler is None:
        return []

    result = handler(
        node=node,
        document=document,
    )

    if result is None:
        return []

    # Handlers may return one reference or several (a Python
    # `from x import a, b` line yields multiple).
    if isinstance(result, list):
        return result

    return [result]
