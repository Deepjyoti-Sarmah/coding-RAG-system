from chunking.splitter import chunk_documents
from ingestion.loader import load_code_files


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

    for chunk in chunks[:5]:
        print("=" * 60)
        print(f"Chunk ID: {chunk['chunk_id']}")
        print(f"File: {chunk['relative_path']}")
        print(f"Chunk Index: {chunk['chunk_index']}")
        print("Preview:")
        print(chunk["content"][:300])
        print()


if __name__ == "__main__":
    main()
