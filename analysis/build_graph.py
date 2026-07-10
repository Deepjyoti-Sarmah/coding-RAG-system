# main.py
#     │
#     ▼
# build_graph(root_dir)
#     │
#     ├── Load documents
#     ├── Parse documents
#     ├── Extract symbols
#     ├── Build symbol index
#     ├── Extract relationships
#     ├── Build graph
#     └── Return graph


from analysis.extracted_symbol import ExtractedSymbol
from analysis.relationship_extractor import extract_relationship
from analysis.symbol_extractor import extract_symbols
from graph.code_graph import CodeGraph
from indexing.symbol_index import SymbolIndex
from ingestion.loader import load_code_files
from models.build_result import BuildResult
from parsing.registry import PARSER


def build_graph(root_dir: str) -> BuildResult:

    documents = load_code_files(root_dir)

    symbol_index = SymbolIndex()
    all_symbols: list[ExtractedSymbol] = []

    for document in documents:
        parser = PARSER.get(document.language)
        if parser is None:
            continue

        tree = parser.parse(document)

        symbols = extract_symbols(tree=tree, document=document)
        all_symbols.extend(symbols)
        symbol_index.add_many([item.symbol for item in symbols])

    all_relationships = []

    for extracted in all_symbols:
        relationships = extract_relationship(
            symbol=extracted.symbol,
            symbol_node=extracted.node,
            symbol_index=symbol_index,
        )
        all_relationships.extend(relationships)

    graph = CodeGraph()
    graph.add_symbols([item.symbol for item in all_symbols])
    graph.add_relationships(all_relationships)

    return BuildResult(
        graph=graph,
        symbol_index=symbol_index,
    )
