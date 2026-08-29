"""The semantic pass sequence, defined once.

Both the full build (`analysis.build_graph`) and the incremental rebuild
(`indexing.indexer`) run the same passes in the same order. They differ
only in which documents they feed to extraction, and in the reuse
merging the incremental path performs between the two phases — which is
why the sequence is split in two rather than exposed as a single call.
"""

from analysis.build_result import BuildResult
from analysis.indexing_context import IndexingContext
from analysis.passes.export_pass import run_export_pass
from analysis.passes.graph_pass import run_graph_pass
from analysis.passes.import_pass import run_import_pass
from analysis.passes.import_resolver_pass import run_import_resolver_pass
from analysis.passes.module_symbol_pass import run_module_symbol_pass
from analysis.passes.parse_pass import run_parse_pass
from analysis.passes.reference_pass import run_reference_pass
from analysis.passes.relationship_pass import run_relationship_pass
from analysis.passes.resolver_pass import run_reference_resolver_pass
from analysis.passes.symbol_pass import run_symbol_pass
from models.entities.documents import Document


def run_extraction_passes(
    *,
    context: IndexingContext,
    result: BuildResult,
    documents: list[Document] | None = None,
) -> None:
    """Parse sources and extract every AST-derived artifact.

    `documents` restricts parsing to a subset (the incremental path
    passes only the files it needs to rebuild); `None` parses everything
    in the context's document index.
    """
    run_parse_pass(context=context, result=result, documents=documents)

    for parsed in context.parsed_documents:
        run_symbol_pass(
            document=parsed.document,
            tree=parsed.tree,
            context=context,
            result=result,
        )

    run_import_pass(context=context, result=result)
    run_export_pass(context=context, result=result)
    run_module_symbol_pass(context=context, result=result)
    run_reference_pass(context=context, result=result)


def run_resolution_passes(
    *,
    context: IndexingContext,
    result: BuildResult,
) -> None:
    """Resolve extracted artifacts into relationships and a graph.

    Imports resolve before references because reference resolution reads
    `result.resolved_import_references` to follow names across files.
    """
    run_import_resolver_pass(context=context, result=result)
    run_reference_resolver_pass(context=context, result=result)
    run_relationship_pass(result=result)
    run_graph_pass(result=result)
