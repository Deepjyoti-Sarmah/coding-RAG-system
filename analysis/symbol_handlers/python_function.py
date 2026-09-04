from tree_sitter import Node

from analysis.symbol_builder import build_symbol
from models.entities.documents import Document
from models.entities.symbol_kind import SymbolKind
from models.entities.symbols import Symbol


def handle_python_function(
    *,
    node: Node,
    document: Document,
    owner: Symbol | None,
) -> Symbol | None:
    """`function_definition` doubles as method when nested in a class."""
    name_node = node.child_by_field_name("name")

    if name_node is None:
        return None

    raw_name = name_node.text

    if raw_name is None:
        return None

    is_method = owner is not None and owner.kind == SymbolKind.CLASS

    return build_symbol(
        node=node,
        name=raw_name.decode("utf-8"),
        kind=SymbolKind.METHOD if is_method else SymbolKind.FUNCTION,
        document=document,
        owner=owner,
        decorators=_decorators_of(node),
    )


def _decorators_of(function_node: Node) -> tuple[str, ...]:
    """Decorator names in source order, e.g. `@app.route("/x")` -> "app.route".

    tree-sitter wraps a decorated function in a `decorated_definition` node,
    with `decorator` children preceding the `function_definition` sibling —
    the decorators are not children of the function node itself. Additive
    only: this never affects qualified_name or stable_key, so a decorator
    gained or lost does not change what the symbol resolves as.
    """
    parent = function_node.parent

    if parent is None or parent.type != "decorated_definition":
        return ()

    names: list[str] = []

    for child in parent.children:
        if child.type != "decorator":
            continue

        # A decorator's payload is everything after `@`: a bare name
        # (`@staticmethod`), a dotted attribute (`@app.route`), or a call
        # (`@app.route(...)`) whose callee is what we want. `.text` on the
        # dotted/attribute/call node gives the source slice directly rather
        # than reconstructing it node-by-node.
        payload = next((c for c in child.children if c.type != "@"), None)

        if payload is None:
            continue

        target = payload.child_by_field_name("function") if payload.type == "call" else payload
        raw = target.text if target is not None else None

        if raw is not None:
            names.append(raw.decode("utf-8"))

    return tuple(names)
