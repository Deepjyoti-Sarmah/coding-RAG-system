"""Re-export handler: export * from \"./x\" / export {a,b} from \"./x\".

Previous handlers returned None for any export_statement with a source,
deferring until cross-file resolution exists. This handler now emits
synthetic exports for re-exports so that downstream graph/document_edges
can model the forwarding.

For `export * from "./x"` we emit a single wildcard export with exported_name="*".
For `export {a, b as c} from "./x"` we emit one export per specifier.
Re-exports are marked via symbol_name=None (no local symbol) but retain
module_path via location for later resolution in import_resolver_pass.
"""
from tree_sitter import Node

from analysis.export_builder import build_export
from models.entities.documents import Document
from models.entities.exports import Export
from parsing.node_text import node_text


def handle_re_export(
    *,
    node: Node,
    document: Document,
) -> list[Export] | None:
    if node.type != "export_statement":
        return None
    source = node.child_by_field_name("source")
    if source is None:
        return None

    # export * from "./x"
    if any(c.type == "*" for c in node.children):
        return [
            build_export(
                document=document,
                exported_name="*",
                symbol_name=None,
                node=node,
            )
        ]

    # export { a, b as c } from "./x"
    exports: list[Export] = []
    for child in node.children:
        if child.type == "export_clause":
            for spec in child.children:
                if spec.type == "export_specifier":
                    ids = [c for c in spec.children if c.type == "identifier"]
                    if len(ids) == 1:
                        name = node_text(ids[0])
                        exports.append(build_export(document=document, exported_name=name, symbol_name=None, node=spec))
                    elif len(ids) == 2:
                        # a as b  -> exported_name=b, symbol_name=a (re-exported)
                        exports.append(build_export(document=document, exported_name=node_text(ids[1]), symbol_name=node_text(ids[0]), node=spec))
    if exports:
        return exports
    # Bare `export *` without clause already handled
    return None
