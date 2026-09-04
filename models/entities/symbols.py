from dataclasses import dataclass

from models.common.source_location import SourceLocation
from models.entities.symbol_kind import SymbolKind


@dataclass(slots=True)
class Symbol:
    symbol_id: str
    document_id: str

    name: str
    kind: SymbolKind

    relative_path: str

    location: SourceLocation

    content: str

    parent_symbol_id: str | None = None

    qualified_name: str = ""

    content_hash: str = ""

    signature_hash: str = ""

    stable_key: str = ""

    # Decorator names in source order, e.g. ("staticmethod", "app.route") for
    # `@staticmethod` `@app.route(...)`. Additive: identity (qualified_name,
    # stable_key) never depends on this, so a decorator added or removed does
    # not change what a symbol resolves as.
    decorators: tuple[str, ...] = ()
