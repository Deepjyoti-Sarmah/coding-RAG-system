from tree_sitter import Node

from analysis.import_builder import build_import_reference
from models.common.source_location import SourceLocation
from models.entities.documents import Document
from models.entities.import_references import ImportReference


def handle_cs_using(
    *,
    node: Node,
    document: Document,
) -> ImportReference | None:
    """`using App.Auth;` binds an entire namespace, not one name --
    C# has no per-type import syntax. Recorded the same way a wildcard
    import is elsewhere (`imported_name="*"`) so it resolves through
    the namespace-index + wildcard-import machinery.

    `using Alias = Ns.Type;` (type alias) and `using static Type;`
    (static-member import) name one specific type/member rather than a
    namespace and need a different resolution path; both are
    unsupported in v1.
    """
    if node.type != "using_directive":
        return None

    if any(child.type in ("=", "static") for child in node.children):
        return None

    target = next(
        (
            child
            for child in node.children
            if child.type in ("qualified_name", "identifier")
        ),
        None,
    )

    if target is None or target.text is None:
        return None

    namespace = target.text.decode("utf-8")

    return build_import_reference(
        document=document,
        module_path=namespace,
        imported_name="*",
        local_name="*",
        location=SourceLocation(
            start_line=node.start_point.row + 1,
            end_line=node.end_point.row + 1,
            start_byte=node.start_byte,
            end_byte=node.end_byte,
        ),
    )
