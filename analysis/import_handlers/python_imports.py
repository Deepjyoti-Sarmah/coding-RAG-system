from tree_sitter import Node

from analysis.import_builder import build_import_reference
from models.common.source_location import SourceLocation
from models.entities.documents import Document
from models.entities.import_references import ImportReference
from parsing.node_text import node_text


def handle_python_import(
    *,
    node: Node,
    document: Document,
) -> list[ImportReference] | None:
    """`import a.b` / `import a.b as c`.

    Without an alias, Python binds the *root* name (`a`); v1 records the
    last dotted segment as both imported and local name, which keeps
    same-package resolution working at the cost of stdlib-style bindings.
    """
    if node.type != "import_statement":
        return None

    references: list[ImportReference] = []

    for child in node.children:
        if child.type == "dotted_name":
            module_path = _dotted_text(child)

            if not module_path:
                continue

            local = module_path.split(".")[-1]
            references.append(
                _build(node, document, module_path, local, local)
            )

        elif child.type == "aliased_import":
            dotted = child.child_by_field_name("name")
            alias = child.child_by_field_name("alias")

            if dotted is None or alias is None:
                continue

            module_path = _dotted_text(dotted)
            local = node_text(alias)
            imported = module_path.split(".")[-1]

            references.append(
                _build(node, document, module_path, imported, local)
            )

    return references


def handle_python_from_import(
    *,
    node: Node,
    document: Document,
) -> list[ImportReference] | None:
    """`from .auth import login as li, token`."""
    if node.type != "import_from_statement":
        return None

    module_node = node.child_by_field_name("module_name")

    if module_node is None:
        return None

    module_prefix = _module_specifier(module_node)

    if module_prefix is None:
        return None

    references: list[ImportReference] = []

    for child in node.children:
        # The module specifier is handled above; only imported names
        # live in the remaining children. Span comparison instead of
        # identity: tree-sitter nodes are recreated per access.
        if (
            child.type == module_node.type
            and child.start_byte == module_node.start_byte
        ):
            continue

        if child.type == "dotted_name":
            name = _dotted_text(child)
            references.append(_build(node, document, module_prefix, name, name))

        elif child.type == "aliased_import":
            dotted = child.child_by_field_name("name")
            alias = child.child_by_field_name("alias")

            if dotted is None:
                continue

            imported = _dotted_text(dotted)
            local = node_text(alias) if alias is not None else imported
            references.append(_build(node, document, module_prefix, imported, local))

        elif child.type == "wildcard_import":
            references.append(
                _build(node, document, module_prefix, "*", "*")
            )

    return references


def _module_specifier(node: Node) -> str | None:
    """Dotted path for absolute imports; `.pkg.auth` form for relative."""
    if node.type == "dotted_name":
        return _dotted_text(node)

    if node.type == "relative_import":
        dots = _count_leading_dots(node)
        dotted = next(
            (part for part in node.children if part.type == "dotted_name"),
            None,
        )
        suffix = _dotted_text(dotted) if dotted is not None else ""
        return "." * dots + suffix

    return None


def _count_leading_dots(node: Node) -> int:
    if node.type == ".":
        return 1

    return sum(_count_leading_dots(child) for child in node.children)


def _dotted_text(node: Node) -> str:
    parts: list[str] = []

    for child in node.children:
        if child.type != "identifier" or child.text is None:
            continue

        parts.append(node_text(child))

    return ".".join(parts)


def _build(
    node: Node,
    document: Document,
    module_path: str,
    imported_name: str,
    local_name: str,
) -> ImportReference:
    return build_import_reference(
        document=document,
        module_path=module_path,
        imported_name=imported_name,
        local_name=local_name,
        location=SourceLocation(
            start_line=node.start_point.row + 1,
            end_line=node.end_point.row + 1,
            start_byte=node.start_byte,
            end_byte=node.end_byte,
        ),
    )
