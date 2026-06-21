from chunking.splitter import chunk_documents
from ingestion.loader import load_code_files


def main():
    root_dir = input("Enter the path to your code folder:").strip()

    documents = load_code_files(root_dir)
    print(f"\nLoaded {len(documents)} files. \n")

    chunks = chunk_documents(documents, chunk_size=1200, overlap=200)
    print(f"Created {len(documents)} files.")

    for chunk in chunks[:5]:
        print("=" * 60)
        print(f"File: {chunk['relative_path']}")
        print(f"Extension: {chunk['extension']}")
        print("Preview:")
        print(chunk["content"][:300])
        print()


if __name__ == "__main__":
    main()
