from analysis.build_graph import build_graph
from graph.code_graph import CodeGraph
from indexing.symbol_index import SymbolIndex

# def print_symbol_tree(symbols: list[Symbol]):
#     by_id = {s.symbol_id: s for s in symbols}
#
#     print("\n=== SYMBOL TREE ===\n")
#
#     for symbol in symbols:
#         parent = (
#             by_id[symbol.parent_symbol_id].name if symbol.parent_symbol_id else None
#         )
#
#         print(f"{symbol.kind.value:10}{symbol.name:20}parent={parent}")
#


def main():
    root_dir = input("Enter the path to your code folder: ").strip()

    result = build_graph(root_dir=root_dir)

    ask_questions(
        symbol_index=result.symbol_index,
        graph=result.graph,
    )


def ask_questions(
    *,
    symbol_index: SymbolIndex,
    graph: CodeGraph,
):
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
            callers = graph.callers_of(symbol.symbol_id)
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
