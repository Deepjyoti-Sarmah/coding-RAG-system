from analysis.symbol_extractor import extract_symbols
from ingestion.loader import load_code_files
from models import symbol
from parsing.registy import PARSER


def main():
    root_dir = input("Enter the path to your code folder:").strip()

    documents = load_code_files(root_dir)
    print(f"\nLoaded {len(documents)} files. \n")

    for document in documents:
        parser = PARSER.get(document.language)

        if parser is None:
            continue

        tree = parser.parse(document)

        symbols = extract_symbols(
            tree=tree,
            document=document,
        )

        for symbol in symbols:
            print(symbol.kind, symbol.name, symbol.relative_path)

        # print(document.relative_path)
        # print(tree.root_node.type)
        print(f"{document.relative_path} -> {tree.root_node.type}")


if __name__ == "__main__":
    main()
