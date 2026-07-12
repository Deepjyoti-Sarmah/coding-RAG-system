from dataclasses import dataclass


@dataclass(slots=True)
class Document:
    document_id: str

    absolute_path: str
    relative_path: str

    file_name: str

    extension: str
    language: str

    size_bytes: int
    line_count: int

    content: str
