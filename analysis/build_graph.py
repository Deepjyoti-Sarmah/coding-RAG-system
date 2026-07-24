from analysis.passes.graph_pass import run_graph_pass
from analysis.passes.reference_pass import run_reference_pass
from analysis.passes.relationship_pass import run_relationship_pass
from analysis.passes.resolver_pass import run_reference_resolver_pass
from analysis.passes.symbol_pass import run_symbol_pass
from ingestion.loader import load_code_files
from models.build_result import BuildResult
from models.indexing_context import IndexingContext
from parsing.registry import PARSER


def build_graph(root_dir: str) -> BuildResult:
    build_result = BuildResult()
    context = IndexingContext()

    build_result.documents = load_code_files(root_dir)

    context.document_index.add_many(build_result.documents)

    # TODO: Replace the current parse-inside-symbol-pass flow with a ParsedDocument
    # IR so all semantic passes can reuse one parse result per file.

    #
    # Symbol Pass
    #
    for document in build_result.documents:
        parser = PARSER.get(document.language)

        if parser is None:
            continue

        tree = parser.parse(document)

        run_symbol_pass(
            document=document,
            tree=tree,
            context=context,
            result=build_result,
        )

    # TODO: Run import extraction + import resolution before reference resolution so
    # imported names and aliases can participate in cross-file symbol resolution.

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
        context=context,
        result=build_result,
    )

    build_result.symbol_index = context.symbol_index

    #
    # Build Graph
    #
    run_graph_pass(result=build_result)

    return build_result
