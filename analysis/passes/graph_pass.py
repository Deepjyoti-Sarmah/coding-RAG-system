from models.build_result import BuildResult


def run_graph_pass(*, result: BuildResult):
    result.graph.add_symbols(
        result.symbols,
    )

    result.graph.add_relationships(
        result.relationships,
    )
