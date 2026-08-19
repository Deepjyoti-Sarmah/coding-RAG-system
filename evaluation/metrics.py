from collections.abc import Iterable


def recall_at_k(expected: frozenset[str], ranked: list[str], k: int) -> float:
    """Fraction of the expected items that appear in the top k ranked results."""
    if not expected:
        return 1.0

    top = ranked[:k]
    hits = sum(1 for name in top if name in expected)

    return hits / len(expected)


def reciprocal_rank(expected: frozenset[str], ranked: list[str]) -> float:
    """1/rank of the first ranked result that is in the expected set, else 0."""
    for position, name in enumerate(ranked, start=1):
        if name in expected:
            return 1.0 / position

    return 0.0


def mean(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def token_reduction(context_tokens: int, baseline_tokens: int) -> float:
    """Fraction of baseline tokens avoided by using the context pack instead."""
    if baseline_tokens <= 0:
        return 0.0

    return 1.0 - (context_tokens / baseline_tokens)


def accuracy(results: Iterable[bool]) -> float:
    results = list(results)
    return sum(1 for r in results if r) / len(results) if results else 1.0
