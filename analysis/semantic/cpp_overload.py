from models.entities.references import Reference
from models.entities.symbol_kind import SymbolKind
from models.entities.symbols import Symbol


def candidate_compatible(symbol: Symbol, reference: Reference) -> bool:
    """Apply only syntactic C++ call evidence; unknown evidence is permissive."""
    marker = "|params:"
    if marker not in symbol.stable_key:
        return True
    params = symbol.stable_key.rsplit(marker, 1)[1]
    arity = 0 if not params else len(params.split(","))
    if reference.call_argument_count is not None and arity != reference.call_argument_count:
        return False
    for kind, parameter in zip(reference.call_argument_kinds, params.split(",") if params else []):
        parameter = parameter.lower()
        if kind == "integer" and any(x in parameter for x in ("float", "double")):
            return False
        if kind == "float" and not any(x in parameter for x in ("float", "double")):
            return False
        if kind == "string" and "char" not in parameter and "string" not in parameter:
            return False
        if kind == "character" and "char" not in parameter:
            return False
        if kind == "boolean" and "bool" not in parameter:
            return False
    return True


def is_cpp_symbol(symbol: Symbol) -> bool:
    return "|cpp|" in symbol.stable_key and symbol.kind in {SymbolKind.FUNCTION, SymbolKind.METHOD}
