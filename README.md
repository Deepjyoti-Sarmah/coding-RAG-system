```
                Code Repository
                       │
                       ▼
              Parsing (Tree-sitter)
                       │
                       ▼
          Semantic Extraction Pipeline
                       │
        ┌──────────────┴──────────────┐
        ▼                             ▼
     Entities                     Relationships
        │                             │
        └──────────────┬──────────────┘
                       ▼
             Code Knowledge Graph
                       │
     ┌─────────────────┼──────────────────┐
     ▼                 ▼                  ▼
 Retrieval        Code Navigation      Refactoring
     ▼                 ▼                  ▼
               AI Context Builder
                       ▼
                     LLM
```