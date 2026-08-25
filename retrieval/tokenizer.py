"""Token counting for context budgeting.

Uses a real BPE tokenizer (tiktoken, o200k_base) so budgets reflect what
an LLM actually counts. The encoder is loaded lazily and cached; if it
cannot be created (offline first run, missing cache), counting falls back
to the deterministic chars/4 heuristic rather than failing retrieval.
"""

from functools import lru_cache

_FALLBACK_CHARS_PER_TOKEN = 4


@lru_cache(maxsize=1)
def _encoder():
    import tiktoken

    return tiktoken.get_encoding("o200k_base")


@lru_cache(maxsize=1)
def _encoder_available() -> bool:
    try:
        _encoder()
    except Exception:  # noqa: BLE001 - any load failure means fallback
        return False

    return True


def count_tokens(text: str) -> int:
    if not text:
        return 0

    if _encoder_available():
        # disallowed_special=(): code legitimately contains strings that
        # look like special tokens; treat them as plain text.
        return len(_encoder().encode(text, disallowed_special=()))

    return max(1, len(text) // _FALLBACK_CHARS_PER_TOKEN)
