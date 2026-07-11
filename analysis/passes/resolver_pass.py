from models.build_result import BuildResult
from models.entities.resolve_reference import ResolvedReference
from models.indexing_context import IndexingContext


def run_resolver_pass(*, context: IndexingContext, result: BuildResult):
    for reference in result.references:
        targets = context.symbol_index.lookup(reference.name)

        if not targets:
            continue

        result.resolved_references.append(
            ResolvedReference(
                reference=reference,
                target_symbol=targets[0],
            )
        )
