EXTENSION_TO_LANGUAGE = {
    ".ts": "typescript",
    ".tsx": "tsx",
    ".js": "javascript",
    ".jsx": "jsx",
    ".py": "python",
    ".go": "go",
    ".java": "java",
    ".rs": "rust",
}


def detect_language(extension: str) -> str:
    return EXTENSION_TO_LANGUAGE.get(
        extension.lower(),
        "unknown",
    )
