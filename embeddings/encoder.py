from sentence_transformers import SentenceTransformer
from torch.nn.functional import embedding


class EmbeddingEncoder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model = SentenceTransformer(model_name)

    def encode_texts(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def encode_query(self, query: str) -> list[float]:
        embedding = self.model.encode(query, convert_to_numpy=True)
        return embedding.tolist()
