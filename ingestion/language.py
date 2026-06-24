EXTENSION_TO_LANGUAGE = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".md": "markdown",
}


def detect_language(extension: str) -> str:
    return EXTENSION_TO_LANGUAGE.get(
        extension.lower(),
        "unknown",
    )
