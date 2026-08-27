import re

TOKEN_PATTERN = re.compile(r"[A-Za-z_]\w*")

# Small code-search-oriented stopword list. Keep it pinned with tests.
STOPWORDS = {
    "where",
    "is",
    "the",
    "a",
    "an",
    "how",
    "does",
    "do",
    "what",
    "who",
    "why",
    "when",
    "of",
    "in",
    "to",
    "for",
    "and",
    "or",
    "this",
    "that",
    "it",
    "are",
    "be",
}


def split_identifier(token: str) -> str:
    """Split camelCase and snake_case into space-separated words.

    Keeps the original token; callers can decide to keep both.
    """
    split = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", token).replace("_", " ")
    return split
