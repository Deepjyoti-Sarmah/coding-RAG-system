from analysis.fingerprints import compute_content_hash
from models.entities.documents import Document


def insert_many(conn, documents: list[Document]) -> None:
    conn.executemany(
        """
        INSERT INTO documents (
            document_id, absolute_path, relative_path, file_name,
            extension, language, size_bytes, line_count, content, file_hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                document.document_id,
                document.absolute_path,
                document.relative_path,
                document.file_name,
                document.extension,
                document.language,
                document.size_bytes,
                document.line_count,
                document.content,
                compute_content_hash(document.content),
            )
            for document in documents
        ],
    )


def fetch_all(conn) -> list[Document]:
    rows = conn.execute(
        """
        SELECT document_id, absolute_path, relative_path, file_name,
               extension, language, size_bytes, line_count, content
        FROM documents
        """
    ).fetchall()

    return [
        Document(
            document_id=row["document_id"],
            absolute_path=row["absolute_path"],
            relative_path=row["relative_path"],
            file_name=row["file_name"],
            extension=row["extension"],
            language=row["language"],
            size_bytes=row["size_bytes"],
            line_count=row["line_count"],
            content=row["content"],
        )
        for row in rows
    ]
