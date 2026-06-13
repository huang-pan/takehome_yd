# Semantic Search Architecture & Design Diagrams

This document contains Mermaid diagrams illustrating the structure, dependencies, and data flows of the semantic search component.

---

## 1. Module Dependency Graph

The following diagram shows how the components in the `search` subdirectory relate to each other and to the external libraries and data resources:

```mermaid
graph TD
    CLI["search.py (Entry point / CLI)"]
    ENGINE["search_engine.py (SemanticSearchEngine)"]
    MODEL["sentence-transformers (all-MiniLM-L6-v2)"]
    DB["duckdb (In-memory OLAP Database)"]
    SCIKIT["scikit-learn (cosine_similarity)"]
    CSV_IN[("pipeline/data/output/ai_articles_enriched.csv")]
    CSV_OUT[("search/output/filtered_ai_articles_with_embeddings.csv")]

    CLI -->|"Instantiates & calls"| ENGINE
    ENGINE -->|"Loads & runs"| MODEL
    ENGINE -->|"Ingests & queries"| DB
    ENGINE -->|"Computes similarities"| SCIKIT
    CSV_IN -->|"pd.read_csv()"| CLI
    CLI -->|"export_to_csv()"| CSV_OUT
```

---

## 2. Pipeline ETL & Semantic Search Data Flow

This diagram traces the sequence of data transformations and logic steps that occur when running `search.py`:

```mermaid
flowchart TD
    A[/"ai_articles_enriched.csv (500 rows)"/] --> B["Ingest & Reset DataFrame Index"]
    
    subgraph text_prep ["Text Preparation"]
        C["Concatenate title & summary (Handle nulls/empty)"]
    end
    
    subgraph embedding_gen ["Embedding Generation"]
        D["all-MiniLM-L6-v2 model (Generate 500 x 384 embeddings)"]
    end
    
    subgraph similarity ["Top Similar Articles Precomputation"]
        E["Compute 500 x 500 Similarity Matrix (Normalized dot products)"]
        F["Exclude self-similarity (idx != current) (Extract top 3 similar IDs)"]
    end
    
    subgraph db_load ["DuckDB Loading"]
        G["Add embeddings & top similar list to DataFrame (Load table 'articles')"]
    end
    
    subgraph db_filter ["DuckDB Hybrid Filtering"]
        H["SQL Query Execution (Filter AI_ML, 2022-2024, Revenue >= $50M, Rename meta_* columns)"]
    end
    
    subgraph export ["Export Preparation"]
        I["Convert embeddings and top similar arrays to JSON strings"]
        J[/"filtered_ai_articles_with_embeddings.csv (48 rows, 18 columns)"/]
    end

    B --> C --> D --> E --> F --> G --> H --> I --> J
```

---

## 3. SemanticSearchEngine Class Structure

Below is the class diagram for the core semantic search controller:

```mermaid
classDiagram
    class SemanticSearchEngine {
        +SentenceTransformer model
        +duckdb.DuckDBPyConnection conn
        +bool is_loaded
        +__init__(str model_name, str db_path)
        +generate_embeddings(list texts) ndarray
        +load_data(DataFrame df, ndarray embeddings) void
        +execute_sql(str query_str) DataFrame
        +find_similar_articles(str query_text, int top_k) list
        +hybrid_search(str query_text, str sql_filters, int top_k) list
        -_resolve_query_embedding(str query) ndarray
    }
```

---

## 4. Hybrid Search Query Execution Flow

This diagram illustrates how the `hybrid_search()` method integrates SQL-based database queries with vector similarity calculations:

```mermaid
flowchart TD
    Q["Query: query_text, sql_filters, top_k"] --> A{"Is query_text a valid article_id?"}
    
    A -->|Yes| B["Retrieve precomputed embedding from DuckDB"]
    A -->|No| C["Encode query_text using SentenceTransformer"]
    
    B --> D["Run SQL SELECT query on DuckDB using sql_filters"]
    C --> D
    
    D --> E["Extract filtered article IDs & embeddings"]
    E --> F["Compute cosine similarity against query embedding"]
    F --> G["Sort results descending by similarity score"]
    G --> H["Select top_k similar articles"]
    H --> R["Return list of (article_id, score)"]
```
