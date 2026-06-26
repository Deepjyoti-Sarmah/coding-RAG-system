from analysis.relationship_extractor import extract_relationship
from analysis.symbol_extractor import extract_symbols
from indexing import symbol_index
from ingestion.loader import load_code_files
from parsing.registy import PARSER


def main():
    root_dir = input("Enter the path to your code folder:").strip()

    documents = load_code_files(root_dir)
    print(f"\nLoaded {len(documents)} files. \n")

    all_symbols = []

    for document in documents:
        parser = PARSER.get(document.language)

        if parser is None:
            continue

        tree = parser.parse(document)

        symbols = extract_symbols(
            tree=tree,
            document=document,
        )

        all_symbols.extend(symbols)

        symbol_index = symbol_index.SymbolIndex()

        symbol_index.add_many(all_symbols)

        relationships = []

        for symbol in all_symbols:
            tree = ...

            relationships.extend(
                extract_relationship(
                    tree=tree,
                    symbol=symbol,
                    symbol_index=symbol_index,
                )
            )

        for symbol in symbols:
            print(symbol.kind, symbol.name, symbol.relative_path)

        # print(document.relative_path)
        # print(tree.root_node.type)
        print(f"{document.relative_path} -> {tree.root_node.type}")

        for child in tree.root_node.children:
            print(child)


if __name__ == "__main__":
    main()
