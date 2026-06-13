# EXPLAIN.md — Technical Decisions & Trade-offs

## Approach

I designed the semantic search component to be modular, efficient, and robust:

1. **`search_engine.py`**: A dedicated `SemanticSearchEngine` class that decouples embedding generation (via `sentence-transformers`), storage (via `DuckDB`), and mathematical operations (via `scikit-learn`'s cosine similarity). It resolves queries dynamically: if the query matches an existing `article_id`, it retrieves the precomputed embedding; otherwise, it generates a new embedding.
2. **`search.py`**: Orchestrates loading, embedding generation, self-similarity exclusion, DuckDB indexing, filtering, column renaming, and CSV export.
3. **`tests/test_search.py`**: Validates the core engine features (embeddings, loading, similarity, and hybrid search) to ensure technical excellence.

For a visual overview of the modules and data flow, see the [Architecture Diagrams](https://github.com/huang-pan/takehome_yd/blob/main/search/MERMAID.md).

---

## Key Design Decisions & Model Selection

### 1. Choice of Embedding Model: `all-MiniLM-L6-v2`
I selected the `all-MiniLM-L6-v2` model from Hugging Face because:
- **Efficiency**: It is a highly optimized, lightweight model (only 22.7 million parameters, ~90MB disk size). It generates embeddings of 384 dimensions.
- **Speed**: It executes extremely fast on standard CPUs, making it ideal for standard Python workloads and local development without a GPU.
- **Performance**: Despite its small size, it scores competitively on standard sentence similarity benchmarks (STS).
- **Format**: It natively produces unit-normalized vectors. This means the cosine similarity between two embeddings reduces to a simple dot product, significantly optimizing computation.

### 2. DuckDB Integration & Vector Storage
DuckDB was used as an in-memory SQL database. It is highly optimized for analytical queries (OLAP) and allows rapid DataFrame ingestion. 
- **Array Storage**: Python list-of-floats is automatically mapped to DuckDB's native `DOUBLE[]` (list) type.
- **Hybrid Search Flow**: The query pipeline executes SQL filtering *first* inside DuckDB using index/column-based operations, which drastically reduces the candidate set. It then extracts the filtered embeddings and performs cosine similarity in Python. This is computationally much more efficient than doing a full-table vector search followed by filtering.

---

## Edge Case Handling

1. **Empty/Null Text Inputs**: When concatenating `title` and `summary` (e.g. `df["title"].fillna("") + ". " + df["summary"].fillna("")`), missing fields are resolved to empty strings instead of resulting in `NaN` or causing execution failures.
2. **Self-Similarity Exclusion**: In Part 3, we add a `top_similar_articles` column representing the top 3 similar articles. A naive similarity search would return the article itself at index 0 (with a cosine score of `1.0`). The pipeline explicitly filters out the article itself from the ranked list before extracting the top 3.
3. **DuckDB List Types**: The pandas-to-duckdb interface converts Python lists into NumPy arrays. Python's default JSON serializer cannot serialize `np.ndarray`. I wrote custom serializer logic in `export_to_csv` (checking for `hasattr(x, "tolist")` and calling `.tolist()`) to format arrays as clean JSON arrays in the CSV.
4. **Environment Compatibility & Dependency Pinning**: We resolved package compatibility issues in this environment where the available PyTorch version was capped at `2.2.2`. PyTorch 2.2.2 is incompatible with NumPy 2.x (crashing on array API initialization). Furthermore, newer `transformers` versions disable PyTorch support when `torch < 2.4.0` is detected, throwing a `NameError: name 'nn' is not defined` error during import. We solved these conflicts by pinning `numpy<2.0`, `sentence-transformers==2.7.0`, and `transformers<4.41.0` to achieve a stable, portable environment.

---

## Trade-offs

### 1. Precomputing Similarity vs. On-the-Fly Queries
- **Precomputing**: In the pipeline, we precompute the full `N x N` cosine similarity matrix to add the `top_similar_articles` column for all 500 rows. This is extremely fast for N=500 (~0.1s).
- **Scale Trade-off**: If the dataset grew to 1,000,000 articles, precomputing an `N x N` matrix would consume too much memory (~4TB). For large-scale data, we would store embeddings in a dedicated vector index (like HNSW or DuckDB's native vss extension) and perform on-the-fly top-K queries.

### 2. Pure Python Similarity vs. Database-level Vector Search
- **Decision**: I computed similarity using `scikit-learn` / `numpy` on the extracted vectors rather than installing the experimental `duckdb_vss` extension.
- **Trade-off**: While native DB vector search is faster for massive tables, using `scikit-learn` is 100% portable, requires zero C-bindings compile issues, and is extremely robust across different platforms.

---

## What I Would Improve With More Time

1. **Incremental Updates**: Instead of rebuilding the DuckDB table and regenerating all embeddings, implement upsert logic that only computes embeddings for new/modified articles.
2. **Asymmetric Search Models**: If user queries are much shorter than articles (e.g., search term "GPT-4" vs. a full article title/summary), a model trained on asymmetric search (like `msmarco-distilbert-base-v4`) would produce better similarity results than `all-MiniLM-L6-v2` (which is tuned for symmetric sentence similarity).
3. **Fuzzy SQL Filtering**: Support full-text search (FTS) in DuckDB to enable text-based keyword matching alongside vector similarity.
