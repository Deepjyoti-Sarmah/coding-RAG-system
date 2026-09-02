from __future__ import annotations

import posixpath
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import replace
from typing import TYPE_CHECKING

from models.relationships.relationship_kind import RelationshipKind
from models.relationships.relationships import Relationship

if TYPE_CHECKING:
    from indexing.symbol_index import SymbolIndex
    from models.entities.documents import Document
    from models.entities.exports import Export
    from models.entities.resolved_import_reference import ResolvedImportReference
    from models.entities.symbols import Symbol


class CodeGraph:
    def __init__(self) -> None:
        self._symbols_by_id: dict[str, Symbol] = {}
        self._children_by_parent: dict[str | None, list[Symbol]] = defaultdict(list)
        self._relationships: list[Relationship] = []
        self._relationships_by_key: dict[tuple[str, str, object], Relationship] = {}
        self._outgoing: dict[str, list[Relationship]] = defaultdict(list)
        self._incoming: dict[str, list[Relationship]] = defaultdict(list)

        # Document-scoped adjacency. Imports and exports are file-level facts
        # with no owning symbol, so they cannot be symbol->symbol rows; they
        # live here instead, rebuilt from the already-persisted
        # resolved_imports/exports tables.
        self._imports_by_document: dict[str, list[Symbol]] = defaultdict(list)
        self._exports_by_document: dict[str, list[Symbol]] = defaultdict(list)
        self._importers_by_document: dict[str, list[str]] = defaultdict(list)
        self._importers_by_symbol: dict[str, list[str]] = defaultdict(list)
        self._document_ids_by_path: dict[str, list[str]] = defaultdict(list)

    def symbols(self) -> tuple[Symbol, ...]:
        return tuple(self._symbols_by_id.values())

    def relationships(self) -> tuple[Relationship, ...]:
        return tuple(self._relationships)

    def add_symbols(self, symbols: list[Symbol]):
        for symbol in symbols:
            self._symbols_by_id[symbol.symbol_id] = symbol
            self._children_by_parent[symbol.parent_symbol_id].append(symbol)

    def add_relationships(self, relationships: list[Relationship]):
        """Fold `relationships` in, accumulating `count` per (source, target, kind).

        The graph holds its own copy of every edge, so folding never mutates the
        caller's objects - `BuildResult.relationships` keeps the counts the
        builder gave it. The graph's copies are what `storage.index_store`
        persists, which makes the graph the authority on edge counts.
        """
        for relationship in relationships:
            existing = self._relationships_by_key.get(relationship.key)

            if existing is not None:
                existing.count += relationship.count
                continue

            owned = replace(relationship)

            self._relationships_by_key[owned.key] = owned
            self._relationships.append(owned)
            self._outgoing[owned.source_symbol_id].append(owned)
            self._incoming[owned.target_symbol_id].append(owned)

    def add_document_edges(
        self,
        *,
        resolved_imports: list[ResolvedImportReference] | None = None,
        exports: list[Export] | None = None,
        symbol_index: SymbolIndex | None = None,
    ) -> None:
        """Index file-level import/export facts for O(1) lookup by document.

        Callers previously scanned the whole repository's resolved imports
        once per seed symbol; this builds the maps once instead.
        """
        for resolved in resolved_imports or []:
            document_id = resolved.import_reference.document_id
            target_document = resolved.target_document

            if resolved.target_symbol is not None:
                self._imports_by_document[document_id].append(resolved.target_symbol)
                _append_unique(
                    self._importers_by_symbol[resolved.target_symbol.symbol_id],
                    document_id,
                )

            _append_unique(
                self._importers_by_document[target_document.document_id],
                document_id,
            )
            self._index_document_path(target_document)

        if symbol_index is None:
            return

        for export in exports or []:
            if export.symbol_name is None:
                continue

            self._exports_by_document[export.document_id].extend(
                module_symbols(symbol_index, export.document_id, export.symbol_name)
            )

    def _index_document_path(self, document: Document) -> None:
        """Make a document findable by its relative path or bare file name."""
        for key in (
            document.relative_path,
            posixpath.basename(document.relative_path),
        ):
            _append_unique(self._document_ids_by_path[key], document.document_id)

    def document_ids_for_path(self, path_or_name: str) -> list[str]:
        return list(self._document_ids_by_path.get(path_or_name, []))

    def importers_of_symbol(self, symbol_id: str) -> list[str]:
        """Document ids of the files that import `symbol_id` by name."""
        return list(self._importers_by_symbol.get(symbol_id, []))

    def imports_of_document(self, document_id: str) -> list[Symbol]:
        return list(self._imports_by_document.get(document_id, []))

    def exports_of_document(self, document_id: str) -> list[Symbol]:
        return list(self._exports_by_document.get(document_id, []))

    def importers_of_document(self, document_id: str) -> list[str]:
        """Document ids of the files that import `document_id`."""
        return list(self._importers_by_document.get(document_id, []))

    def declares(self, symbol_id: str) -> list[Symbol]:
        return self._targets_of(symbol_id, RelationshipKind.DECLARES)

    def outgoing(self, symbol_id: str) -> list[Relationship]:
        return list(self._outgoing.get(symbol_id, []))

    def children_of(self, symbol_id: str) -> list[Symbol]:
        return list(self._children_by_parent.get(symbol_id, []))

    def parents_of(self, symbol_id: str) -> list[Symbol]:
        symbol = self._symbols_by_id.get(symbol_id)

        if symbol is None or symbol.parent_symbol_id is None:
            return []

        parent = self._symbols_by_id.get(symbol.parent_symbol_id)

        return [parent] if parent is not None else []

    def callers_of(self, symbol_id: str) -> list[Symbol]:
        return self._sources_of(symbol_id, RelationshipKind.CALLS)

    def callees_of(self, symbol_id: str) -> list[Symbol]:
        return self._targets_of(symbol_id, RelationshipKind.CALLS)

    def base_types_of(self, symbol_id: str) -> list[Symbol]:
        return self._targets_of(symbol_id, RelationshipKind.EXTENDS)

    def subtypes_of(self, symbol_id: str) -> list[Symbol]:
        return self._sources_of(symbol_id, RelationshipKind.EXTENDS)

    def has_type_of(self, symbol_id: str) -> list[Symbol]:
        return self._targets_of(symbol_id, RelationshipKind.HAS_TYPE)

    def typed_by(self, symbol_id: str) -> list[Symbol]:
        return self._sources_of(symbol_id, RelationshipKind.HAS_TYPE)

    def returns_of(self, symbol_id: str) -> list[Symbol]:
        return self._targets_of(symbol_id, RelationshipKind.RETURNS)

    def _sources_of(
        self,
        symbol_id: str,
        kind: RelationshipKind,
    ) -> list[Symbol]:
        return self._resolve(
            relationship.source_symbol_id
            for relationship in self._incoming.get(symbol_id, [])
            if relationship.kind == kind
        )

    def _targets_of(
        self,
        symbol_id: str,
        kind: RelationshipKind,
    ) -> list[Symbol]:
        return self._resolve(
            relationship.target_symbol_id
            for relationship in self._outgoing.get(symbol_id, [])
            if relationship.kind == kind
        )

    def _resolve(self, symbol_ids: Iterable[str]) -> list[Symbol]:
        symbols: list[Symbol] = []

        for symbol_id in symbol_ids:
            symbol = self._symbols_by_id.get(symbol_id)

            if symbol is None:
                continue

            symbols.append(symbol)

        return symbols


def module_symbols(
    symbol_index: SymbolIndex,
    document_id: str,
    name: str,
) -> list[Symbol]:
    """Top-level symbols in `document_id` declaring `name`."""
    return [
        symbol
        for symbol in symbol_index.lookup_by_name(name)
        if symbol.document_id == document_id and symbol.parent_symbol_id is None
    ]


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)
