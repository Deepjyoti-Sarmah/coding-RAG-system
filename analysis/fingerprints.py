import hashlib

from models.entities.symbol_kind import SymbolKind


def compute_content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def compute_signature_hash(signature: str) -> str:
    return hashlib.sha256(signature.encode("utf-8")).hexdigest()


def build_stable_key(
    *,
    relative_path: str,
    language: str,
    qualified_name: str,
    kind: SymbolKind,
) -> str:
    return f"{relative_path}|{language}|{qualified_name}|{kind.value}"
