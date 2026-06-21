def split_text_with_overlap(
    text: str,
    chunk_size: int = 1200,
    overlap: int = 200,
) -> list[str]:
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)

        if end >= text_length:
            break

        start = end - overlap

    return chunks


def chunk_documents(
    documents: list[dict],
    chunk_size: int = 1200,
    overlap: int = 200,
) -> list[dict]:
    all_chunks = []

    for doc in documents:
        text_chunks = split_text_with_overlap(
            doc["content"],
            chunk_size=chunk_size,
            overlap=overlap,
        )

        for index, chunk_text in enumerate(text_chunks):
            all_chunks.append(
                {
                    "chunk_id": f"{doc['relative_path']}::chunk_{index}",
                    "relative_path": doc["relative_path"],
                    "path": doc["path"],
                    "extension": doc["extension"],
                    "chunk_index": index,
                    "content": chunk_text,
                }
            )

    return all_chunks


# evals
# benchmarking
