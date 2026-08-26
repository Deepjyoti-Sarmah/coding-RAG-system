from analysis.build_result import BuildResult


def run_graph_pass(*, result: BuildResult):
    result.graph.add_symbols(
        result.symbols,
    )

    result.graph.add_relationships(
        result.relationships,
    )

    result.graph.add_document_edges(
        resolved_imports=result.resolved_import_references,
        exports=result.exports,
        symbol_index=result.symbol_index,
    )
