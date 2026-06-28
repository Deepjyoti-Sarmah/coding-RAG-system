from tree_sitter import Node

from analysis.relationship_extractor import extract_relationship
from analysis.symbol_extractor import extract_symbols
from indexing.symbol_index import SymbolIndex
from ingestion.loader import load_code_files
from models.symbol import Symbol
from parsing.registy import PARSER


def main():
    root_dir = input("Enter the path to your code folder: ").strip()

    documents = load_code_files(root_dir)
    print(f"\nLoaded {len(documents)} files.\n")

    symbol_index = SymbolIndex()
    all_symbols: list[tuple[Symbol, Node]] = []

    for document in documents:
        parser = PARSER.get(document.language)
        if parser is None:
            continue

        tree = parser.parse(document)

        symbols = extract_symbols(tree=tree, document=document)
        all_symbols.extend(symbols)
        symbol_index.add_many([s for s, _ in symbols])

        print(f"{document.relative_path} -> {len(symbols)} symbols")

    print(f"\nIndexed {len(all_symbols)} symbols total.\n")

    all_relationships = []

    for symbol, node in all_symbols:
        relationships = extract_relationship(
            symbol=symbol,
            symbol_node=node,
            symbol_index=symbol_index,
        )
        all_relationships.extend(relationships)

    print(f"Extracted {len(all_relationships)} relationships.\n")

    for symbol, _ in all_symbols:
        print(symbol.kind.value, symbol.name, symbol.relative_path)


if __name__ == "__main__":
    main()
