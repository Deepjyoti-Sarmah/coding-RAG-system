from tree_sitter import Node

from analysis.relationship_extractor import extract_relationship
from analysis.symbol_extractor import extract_symbols
from graph.code_graph import CodeGraph
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

    graph = CodeGraph()
    graph.add_symbols([symbol for symbol, _ in all_symbols])
    graph.add_relationships(all_relationships)

    ask_questions(symbol_index, graph)


def ask_questions(symbol_index: SymbolIndex, graph: CodeGraph):
    print("Ask a question (or press enter to quit).")
    print("Try: Where is createAuth defined \n")

    while True:
        query = input("Ask> ").strip()
        if not query:
            break

        handle_query(query, symbol_index, graph)


def handle_query(query: str, symbol_index: SymbolIndex, graph: CodeGraph):
    words = query.split()
    symbol_name = words[-1]

    if query.lower().startswith("who calls"):
        matching_symbols = symbol_index.lookup(symbol_name)
        if not matching_symbols:
            print(f"No symbol named '{symbol_name}' found.\n")
            return

        for symbol in matching_symbols:
            callers = graph.callees_of(symbol.symbol_id)
            if not callers:
                print(f"Nothing calls {symbol.name}.\n")
                continue

            print(f"{symbol.name} is called by:")
            for caller in callers:
                print(f" - {caller.name} ({caller.relative_path})")
            print()

    elif query.lower().startswith("where is"):
        matching_symbols = symbol_index.lookup(symbol_name)

        if not matching_symbols:
            print(f"No symbol named '{symbol_name}' found.\n")
            return

        for symbol in matching_symbols:
            print(f"{symbol.name} ({symbol.kind.value}) is defined at:")
            print(f"{symbol.relative_path}:{symbol.start_line}\n")

    else:
        print(
            'Sorry, I can only answer "who calls X" or "where is X defined" right now.\n'
        )


if __name__ == "__main__":
    main()
