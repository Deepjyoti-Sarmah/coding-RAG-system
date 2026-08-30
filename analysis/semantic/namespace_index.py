"""Namespace -> declaring-document index, for languages (C#) where an
import names a namespace that any number of files anywhere in the tree
may contribute types to, rather than a single guessable file path.
"""

from dataclasses import dataclass, field


@dataclass(slots=True)
class NamespaceIndex:
    _documents_by_namespace: dict[str, list[str]] = field(default_factory=dict)
    _namespace_by_document: dict[str, str] = field(default_factory=dict)

    def add(self, *, namespace: str, document_id: str) -> None:
        self._documents_by_namespace.setdefault(namespace, []).append(document_id)
        self._namespace_by_document[document_id] = namespace

    def document_ids_for(self, namespace: str) -> list[str]:
        return self._documents_by_namespace.get(namespace, [])

    def namespace_for(self, document_id: str) -> str | None:
        return self._namespace_by_document.get(document_id)
