"""IMPLEMENTS references for languages whose trait/interface-conformance
syntax (Rust's `impl Trait for Type`) lives in a standalone top-level
node rather than nested inside either symbol's own node.

The generic reference walker (`reference_extractor.py`) only visits
inside an already-extracted symbol's node, so it never sees these. This
pass walks each parsed document's raw tree once for `profile.impl_node`
occurrences and emits the IMPLEMENTS reference directly, from the
already-extracted `impl_type_field` symbol to the `impl_trait_field`
name -- reusing the existing reference/relationship pipeline rather than
building relationships by hand.
"""

from analysis.build_result import BuildResult
from analysis.indexing_context import IndexingContext
from analysis.languages import profile_for
from analysis.reference_builder import build_reference
from models.entities.reference_kind import ReferenceKind
from models.entities.symbols import Symbol
from parsing.node_text import node_text


def run_impl_pass(
    *,
    context: IndexingContext,
    result: BuildResult,
):
    module_level_by_document: dict[str, dict[str, Symbol]] = {}

    for extracted in context.extracted_symbols:
        symbol = extracted.symbol

        if symbol.parent_symbol_id is not None:
            continue

        module_level_by_document.setdefault(symbol.document_id, {})[
            symbol.name
        ] = symbol

    for parsed in context.parsed_documents:
        profile = profile_for(parsed.document.language)

        if profile is None or profile.impl_node is None:
            continue

        by_name = module_level_by_document.get(parsed.document.document_id, {})

        for node in _find_nodes(parsed.tree.root_node, profile.impl_node):
            type_node = node.child_by_field_name(profile.impl_type_field)
            trait_node = node.child_by_field_name(profile.impl_trait_field)

            if type_node is None or trait_node is None:
                continue

            type_symbol = by_name.get(node_text(type_node))

            if type_symbol is None:
                continue

            result.references.append(
                build_reference(
                    node=trait_node,
                    owner_symbol=type_symbol,
                    kind=ReferenceKind.IMPLEMENTS,
                    path=(node_text(trait_node),),
                )
            )


def _find_nodes(node, node_type: str):
    if node.type == node_type:
        yield node

    for child in node.children:
        yield from _find_nodes(child, node_type)
