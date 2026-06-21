from chunking.splitter import chunk_documents
from embeddings.encoder import EmbeddingEncoder
from ingestion.loader import load_code_files
from retrieval.search import search_chunks


def main():
    root_dir = input("Enter the path to your code folder:").strip()

    documents = load_code_files(root_dir)
    print(f"\nLoaded {len(documents)} files. \n")

    if documents:
        print("First document keys:", documents[0].keys())
        print("First document path:", documents[0]["relative_path"])
        print("First document content length:", len(documents[0]["content"]))

    chunks = chunk_documents(documents, chunk_size=1200, overlap=200)
    print(f"Created {len(chunks)} chunks. \n")

    texts = [chunk["content"] for chunk in chunks]

    print("\nLoading embedding model...")
    encoder = EmbeddingEncoder()

    print("Encoding chunks...")
    chunk_embeddings = encoder.encode_texts(texts)
    print(f"Encoded {len(chunk_embeddings)} chunks.")

    while True:
        query = input("\nAsk a question about the codeabse (or type 'exit'):").strip()

        if query.lower() == "exit":
            print("Goodbye!")
            break

        query_embedding = encoder.encode_query(query)
        results = search_chunks(
            query_embedding,
            chunk_embeddings,
            chunks,
            top_k=5,
        )

        print("\nTop matching chunks:\n")

        for result in results:
            chunk = result["chunk"]

            print("=" * 60)
            print(f"Score: {result['score']:.4f}")
            print(f"File: {chunk['relative_path']}")
            print(f"Chunk ID: {chunk['chunk_id']}")
            print("Preview:")
            print(chunk["content"][:400])
            print()


if __name__ == "__main__":
    main()