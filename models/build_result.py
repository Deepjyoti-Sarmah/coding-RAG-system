from dataclasses import dataclass, field

from graph.code_graph import CodeGraph
from indexing.symbol_index import SymbolIndex
from models.entities.document import Document
from models.entities.reference import Reference
from models.entities.resolve_reference import ResolvedReference
from models.entities.symbol import Symbol
from models.relationships import relationship


@dataclass(slots=True)
class BuildResult:
    documents: list[Document] = field(default_factory=list)

    symbols: list[Symbol] = field(default_factory=list)

    references: list[Reference] = field(default_factory=list)

    resolved_references: list[ResolvedReference] = field(default_factory=list)

    relationships: list[relationship.Relationship] = field(default_factory=list)

    graph: CodeGraph = field(default_factory=CodeGraph)
