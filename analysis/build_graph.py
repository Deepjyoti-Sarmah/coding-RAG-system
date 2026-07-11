from analysis.reference_extractor import extract_references
from analysis.relationship_extractor import extract_relationship
from analysis.symbol_extractor import extract_symbols
from indexing.symbol_index import SymbolIndex
from ingestion.loader import load_code_files
from models.build_result import BuildResult
from models.extracted_symbol import ExtractedSymbol
from models.indexing_context import IndexingContext
from parsing.registry import PARSER


def build_graph(root_dir: str) -> BuildResult:
    build_result = BuildResult()
    context = IndexingContext()

    build_result.documents = load_code_files(root_dir)

    #
    # Symbol Pass
    #
    for document in build_result.documents:
        parser = PARSER.get(document.language)

        if parser is None:
            continue

        tree = parser.parse(document)

        extracted = extract_symbols(
            tree=tree,
            document=document,
        )

        context.extracted_symbols.extend(extracted)

        build_result.symbols.extend(item.symbol for item in extracted)

        context.symbol_index.add_many([item.symbol for item in extracted])

    #
    # Reference Pass
    #
    for extracted in context.extracted_symbols:
        references = extract_references(
            owner_symbol=extracted.symbol,
            owner_node=extracted.node,
        )

        build_result.references.extend(references)

    #
    # Relationship Pass
    #
    for extracted in context.extracted_symbols:
        relationships = extract_relationship(
            symbol=extracted.symbol,
            symbol_node=extracted.node,
            symbol_index=context.symbol_index,
        )

        build_result.relationships.extend(relationships)

    #
    # Build Graph
    #
    build_result.graph.add_symbols(
        build_result.symbols,
    )

    build_result.graph.add_relationships(
        build_result.relationships,
    )

    return build_result
