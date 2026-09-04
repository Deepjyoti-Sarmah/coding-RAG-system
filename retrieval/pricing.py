"""Model pricing for token-dollar savings projections.

Dated table written from published rates as of PRICE_DATE — not copied from
another project. Dollars are a *projection, not a measurement*: they depend
on a model price and a query volume this project does not control. Always
render dollars as a formula with inputs visible (N queries x tokens saved x
$/1M), never as a bare "saves $X". Input tokens only in v1.
"""

PRICE_DATE = "2026-06-24"

DEFAULT_MODEL = "sonnet"

# $ per 1M tokens: {"model": (input, output)}. As of PRICE_DATE:
# Claude Opus 5 $5.00/$25.00, Sonnet 5 $2.00/$10.00, Haiku 4.5 $1.00/$5.00.
PRICING: dict[str, tuple[float, float]] = {
    "opus": (5.00, 25.00),
    "sonnet": (2.00, 10.00),
    "haiku": (1.00, 5.00),
}


def resolve_pricing(model: str) -> tuple[float, float]:
    """Return (input, output) $/1M for a model name (case-insensitive)."""
    key = model.lower()
    if key not in PRICING:
        known = ", ".join(sorted(PRICING))
        raise ValueError(f"unknown pricing model {model!r} (known: {known})")
    return PRICING[key]


def dollars_saved(tokens_saved: float, model: str = DEFAULT_MODEL) -> float:
    """Input-token dollars saved. Computed from aggregate token means, never
    from the mean of per-query ratios."""
    price_in, _ = resolve_pricing(model)
    return tokens_saved * price_in / 1_000_000
