from analysis.passes.export_pass import run_export_pass
from analysis.passes.graph_pass import run_graph_pass
from analysis.passes.import_pass import run_import_pass
from analysis.passes.import_resolver_pass import run_import_resolver_pass
from analysis.passes.parse_pass import run_parse_pass
from analysis.passes.reference_pass import run_reference_pass
from analysis.passes.relationship_pass import run_relationship_pass
from analysis.passes.resolver_pass import run_reference_resolver_pass
from analysis.passes.symbol_pass import run_symbol_pass
from ingestion.loader import load_code_files
from models.build_result import BuildResult
from models.indexing_context import IndexingContext


def build_graph(root_dir: str) -> BuildResult:
    build_result = BuildResult()
    context = IndexingContext()

    build_result.documents = load_code_files(root_dir)

    context.document_index.add_many(build_result.documents)

    #
    # Parse Pass
    #
    run_parse_pass(
        context=context,
        result=build_result,
    )

    #
    # Symbol Pass
    #
    for parsed in context.parsed_documents:
        run_symbol_pass(
            document=parsed.document,
            tree=parsed.tree,
            context=context,
            result=build_result,
        )

    #
    # Import Pass
    #
    run_import_pass(
        context=context,
        result=build_result,
    )

    #
    # Export Pass
    #
    run_export_pass(
        context=context,
        result=build_result,
    )

    #
    # Import Resolver Pass
    #
    run_import_resolver_pass(
        context=context,
        result=build_result,
    )

    #
    # Reference Pass
    #
    run_reference_pass(
        context=context,
        result=build_result,
    )

    #
    # Resolver Pass
    #
    run_reference_resolver_pass(
        context=context,
        result=build_result,
    )

    #
    # Relationship Pass
    #
    run_relationship_pass(
        result=build_result,
    )

    build_result.symbol_index = context.symbol_index

    #
    # Build Graph
    #
    run_graph_pass(result=build_result)

    return build_result
