from sklearn.metrics.pairwise import cosine_similarity


def search_chunks(
    query_embedding: list[float],
    chunk_embedding: list[list[float]],
    chunks: list[dict],
    top_k: int = 5,
) -> list[dict]:
    similarities = cosine_similarity([query_embedding], chunk_embedding)[0]

    scored_results = []

    for chunk, score in zip(chunks, similarities):
        scored_results.append(
            {
                "score": float(score),
                "chunk": chunk,
            }
        )

    scored_results.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return scored_results[:top_k]
