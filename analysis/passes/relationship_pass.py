from analysis.build_result import BuildResult
from analysis.relationship_builder import build_relationships


def run_relationship_pass(
    *,
    result: BuildResult,
):
    result.relationships = build_relationships(
        resolved_references=result.resolved_references,
        symbols=result.symbols,
    )
