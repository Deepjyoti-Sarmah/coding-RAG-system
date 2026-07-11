# from analysis.reference_extractor import extract_references
# from analysis.relationship_extractor import extract_relationship
# from analysis.symbol_extractor import extract_symbols
# from indexing.symbol_index import SymbolIndex
# from ingestion.loader import load_code_files
# from models.build_result import BuildResult
# from models.extracted_symbol import ExtractedSymbol
# from parsing.registry import PARSER


# def build_graph(root_dir: str) -> BuildResult:
#     build_result = BuildResult()

#     build_result.documents = load_code_files(root_dir)

#     symbol_index = SymbolIndex()
#     extracted_symbols: list[ExtractedSymbol] = []

#     # Symbol pass

#     for document in build_result.documents:
#         parser = PARSER.get(document.language)

#         if parser is None:
#             continue

#         tree = parser.parse(document)

#         symbols = extract_symbols(
#             tree=tree,
#             document=document,
#         )

#         extracted_symbols.extend(symbols)

#         build_result.symbols.extend(extracted.symbol for extracted in symbols)

#         symbol_index.add_many([extracted.symbol for extracted in symbols])

#     # Reference Pass
#     for extracted in extracted_symbols:
#         references = extract_references(
#             owner_symbol=extracted.symbol,
#             owner_node=extracted.node,
#         )

#         build_result.references.extend(references)

#     # Relationship Pass

#     for extracted in extracted_symbols:
#         relationships = extract_relationship(
#             symbol=extracted.symbol,
#             symbol_node=extracted.node,
#             symbol_index=symbol_index,
#         )

#         build_result.relationships.extend(relationships)

#     # Build Graph
#     #
#     build_result.graph.add_symbols(build_result.symbols)

#     build_result.graph.add_relationships(build_result.relationships)

#     build_result.symbol_index = symbol_index

#     return build_result

from analysis.reference_extractor import extract_references
from analysis.relationship_extractor import extract_relationship
from analysis.symbol_extractor import extract_symbols
from indexing.symbol_index import SymbolIndex
from ingestion.loader import load_code_files
from models.build_result import BuildResult
from models.extracted_symbol import ExtractedSymbol
from parsing.registry import PARSER


def build_graph(root_dir: str) -> BuildResult:
    build_result = BuildResult()

    build_result.documents = load_code_files(root_dir)

    symbol_index = SymbolIndex()
    extracted_symbols: list[ExtractedSymbol] = []

    #
    # Symbol Pass
    #
    for document in build_result.documents:
        parser = PARSER.get(document.language)

        if parser is None:
            continue

        tree = parser.parse(document)

        symbols = extract_symbols(
            tree=tree,
            document=document,
        )

        extracted_symbols.extend(symbols)

        build_result.symbols.extend(extracted.symbol for extracted in symbols)

        symbol_index.add_many([extracted.symbol for extracted in symbols])

    #
    # Reference Pass
    #
    for extracted in extracted_symbols:
        references = extract_references(
            owner_symbol=extracted.symbol,
            owner_node=extracted.node,
        )

        build_result.references.extend(references)

    #
    # Relationship Pass
    #
    for extracted in extracted_symbols:
        relationships = extract_relationship(
            symbol=extracted.symbol,
            symbol_node=extracted.node,
            symbol_index=symbol_index,
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

    build_result.symbol_index = symbol_index

    return build_result
