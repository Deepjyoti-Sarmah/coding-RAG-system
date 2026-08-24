from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

from models.entities.symbols import Symbol


class MatchConfidence(Enum):
    HIGH = "high"
    MEDIUM = "medium"


@dataclass(slots=True)
class SymbolMatch:
    old_symbol: Symbol
    new_symbol: Symbol
    confidence: MatchConfidence


def match_symbols(
    *,
    old_symbols: list[Symbol],
    new_symbols: list[Symbol],
) -> list[SymbolMatch]:
    old_by_key: dict[str, list[Symbol]] = defaultdict(list)
    old_by_scope_signature: dict[tuple[str, str, str], list[Symbol]] = defaultdict(
        list
    )
    old_by_content: dict[str, list[Symbol]] = defaultdict(list)

    for symbol in old_symbols:
        old_by_key[symbol.stable_key].append(symbol)
        old_by_scope_signature[
            (
                symbol.relative_path,
                _parent_qualified_name(symbol),
                symbol.signature_hash,
            )
        ].append(symbol)
        old_by_content[symbol.content_hash].append(symbol)

    matched_old_ids: set[str] = set()
    matches: list[SymbolMatch] = []

    for new_symbol in new_symbols:
        candidates = _unclaimed(old_by_key.get(new_symbol.stable_key, []), matched_old_ids)

        if len(candidates) == 1:
            matches.append(
                SymbolMatch(
                    old_symbol=candidates[0],
                    new_symbol=new_symbol,
                    confidence=MatchConfidence.HIGH,
                )
            )
            matched_old_ids.add(candidates[0].symbol_id)
            continue

        scope = (
            new_symbol.relative_path,
            _parent_qualified_name(new_symbol),
            new_symbol.signature_hash,
        )
        candidates = _unclaimed(
            old_by_scope_signature.get(scope, []),
            matched_old_ids,
        )

        if len(candidates) == 1:
            matches.append(
                SymbolMatch(
                    old_symbol=candidates[0],
                    new_symbol=new_symbol,
                    confidence=MatchConfidence.MEDIUM,
                )
            )
            matched_old_ids.add(candidates[0].symbol_id)
            continue

        candidates = _unclaimed(
            [
                symbol
                for symbol in old_by_content.get(new_symbol.content_hash, [])
                if symbol.stable_key != new_symbol.stable_key
            ],
            matched_old_ids,
        )

        if len(candidates) == 1:
            matches.append(
                SymbolMatch(
                    old_symbol=candidates[0],
                    new_symbol=new_symbol,
                    confidence=MatchConfidence.MEDIUM,
                )
            )
            matched_old_ids.add(candidates[0].symbol_id)

    return matches


def _unclaimed(
    candidates: list[Symbol],
    matched_old_ids: set[str],
) -> list[Symbol]:
    return [
        symbol for symbol in candidates if symbol.symbol_id not in matched_old_ids
    ]


def _parent_qualified_name(symbol: Symbol) -> str:
    last_separator = symbol.qualified_name.rfind(".")

    if last_separator < 0:
        return ""

    return symbol.qualified_name[:last_separator]
