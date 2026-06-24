```
Repository
 ↓
Load Files
 ↓
Parse Code
 ↓
Extract Symbols
 ↓
Create Chunks
 ↓
Embed
 ↓
Index
 ↓
Retrieve
 ↓
Generate
```
```
```



```
.
├── main.py
├── config.py
│
├── models/
│   ├── document.py
│   ├── symbol.py
│   ├── chunk.py
│   └── search_result.py
│
├── ingestion/
│   └── loader.py
│
├── parsers/
│   ├── base.py
│   ├── typescript.py
│   ├── javascript.py
│   └── python.py
│
├── chunking/
│   └── symbol_chunker.py
│
├── embeddings/
│   └── encoder.py
│
├── indexing/
│   ├── memory_index.py
│   └── faiss_index.py
│
├── retrieval/
│   ├── vector_search.py
│   ├── bm25_search.py
│   └── hybrid_search.py
│
├── evaluation/
│   └── benchmark.py
│
├── generation/
│   └── answer_generator.py
│
└── storage/
    ├── documents/
    ├── chunks/
    └── indexes/
```
```
```
