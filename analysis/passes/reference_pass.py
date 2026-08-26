from analysis.build_result import BuildResult
from analysis.indexing_context import IndexingContext
from analysis.languages import LanguageProfile, profile_for
from analysis.reference_extractor import extract_references


def run_reference_pass(
    *,
    context: IndexingContext,
    result: BuildResult,
):
    profiles: dict[str, LanguageProfile | None] = {}

    for extracted in context.extracted_symbols:
        if extracted.language not in profiles:
            profiles[extracted.language] = profile_for(extracted.language)

        profile = profiles[extracted.language]

        if profile is None:
            continue

        references = extract_references(
            owner_symbol=extracted.symbol,
            owner_node=extracted.node,
            profile=profile,
        )

        result.references.extend(references)
