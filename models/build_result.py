from dataclasses import dataclass, field

from graph.code_graph import CodeGraph
from models.entities import resolved_import_reference
from models.entities.documents import Document
from models.entities.import_references import ImportReference
from models.entities.references import Reference
from models.entities.resolved_reference import ResolvedReference
from models.entities.symbols import Symbol
from models.relationships.relationships import Relationship


@dataclass(slots=True)
class BuildResult:
    documents: list[Document] = field(default_factory=list)

    symbols: list[Symbol] = field(default_factory=list)

    import_reference: list[ImportReference] = field(default_factory=list)

    resolved_import_reference: list[
        resolved_import_reference.ResolvedImportReference
    ] = field(default_factory=list)

    references: list[Reference] = field(default_factory=list)

    resolved_references: list[ResolvedReference] = field(default_factory=list)

    relationships: list[Relationship] = field(default_factory=list)

    graph: CodeGraph = field(default_factory=CodeGraph)
