from ingestion.loader import load_code_files


def main():
    root_dir = input("Enter the path to your code folder:").strip()
    documents = load_code_files(root_dir)

    print(f"\nLoaded {len(documents)} files. \n")

    for doc in documents[:5]:
        print("=" * 60)
        print(f"File: {doc['relative_path']}")
        print(f"Extension: {doc['extension']}")
        print("Preview:")
        print(doc["content"][:300])
        print()


if __name__ == "__main__":
    main()
