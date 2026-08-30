"""Builds `NamespaceIndex` for namespace-indexed languages (C#) and, for
each document, synthesizes an implicit whole-namespace import of its own
declared namespace.

C# requires no `using` to see other types in the same namespace, even
across files -- that's exactly the "any file may declare a type in a
named namespace" property `NamespaceIndex` exists for. Modelling it as
a synthetic import (`imported_name="*"`, matching an explicit
`using Ns;`) means same-namespace, cross-file resolution reuses the
wildcard-import machinery in `name_resolver.py` / `member_resolver.py`
rather than needing its own resolution path.
"""

from analysis.build_result import BuildResult
from analysis.import_builder import build_import_reference
from analysis.indexing_context import IndexingContext
from analysis.languages import profile_for
from models.common.source_location import SourceLocation
from parsing.node_text import node_text


def run_namespace_pass(
    *,
    context: IndexingContext,
    result: BuildResult,
):
    for parsed in context.parsed_documents:
        profile = profile_for(parsed.document.language)

        if profile is None or not profile.namespace_nodes:
            continue

        node = _find_first(parsed.tree.root_node, profile.namespace_nodes)

        if node is None:
            continue

        name_node = node.child_by_field_name(profile.namespace_name_field)

        if name_node is None:
            continue

        namespace = node_text(name_node)

        context.namespace_index.add(
            namespace=namespace,
            document_id=parsed.document.document_id,
        )

        result.import_references.append(
            build_import_reference(
                document=parsed.document,
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
        )


def _find_first(node, node_types: frozenset[str]):
    if node.type in node_types:
        return node

    for child in node.children:
        found = _find_first(child, node_types)

        if found is not None:
            return found

    return None
