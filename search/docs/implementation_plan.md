# Implementation Plan - Semantic Search Integration

Implement semantic search using sentence-transformers (`all-MiniLM-L6-v2`), DuckDB vector/JSON storage, and a query/export pipeline.

## User Review Required

> [!IMPORTANT]
> **Output CSV Path**
> The requirement states that we should create a pipeline that exports a CSV file, but doesn't specify a precise path. We propose exporting the CSV to `semantic_search/output/filtered_ai_articles_with_embeddings.csv`.

> [!NOTE]
> **Embedding & Similarity Column Formatting**
> For the output columns `embedding` (array/list) and `top_similar_articles` (top 3 most similar article IDs), we will serialize them as JSON-formatted strings (e.g., `[0.015, -0.023, ...]` and `["ART0002", "ART0003", "ART0004"]`). This ensures they are easily parseable and clean when saved in standard CSV format.

## Open Questions

None. The requirements in `SKILL_SEMANTIC_SEARCH.md` are clear.

---

## Proposed Changes

We will place all implementation code, tests, and documentation under the `semantic_search/` directory.

### Dependencies and Configuration

#### [NEW] [requirements.txt](file:///Users/huangpan/Documents/YipitData/takehome_yd/semantic_search/requirements.txt)
Define the python libraries needed:
- `pandas`
- `duckdb`
- `numpy`
- `scikit-learn`
- `sentence-transformers`
- `pyarrow`

### Core Engine and Search Functionality

#### [NEW] [search_engine.py](file:///Users/huangpan/Documents/YipitData/takehome_yd/semantic_search/search_engine.py)
A module containing:
- `SemanticSearchEngine` class:
  - Initializes the `SentenceTransformer` model.
  - Generates embeddings for titles + summaries.
  - Loads data and embeddings into an in-memory DuckDB instance.
  - `find_similar_articles(query_text, top_k=5)`: Computes cosine similarity of query against all stored articles using `scikit-learn`.
  - `hybrid_search(query_text, sql_filters, top_k=5)`: Filters using DuckDB SQL WHERE clauses first, then computes similarity on the remaining subset.
  - `execute_sql(query_str)`: Runs raw DuckDB queries.

### Pipeline Orchestration

#### [NEW] [pipeline.py](file:///Users/huangpan/Documents/YipitData/takehome_yd/semantic_search/pipeline.py)
The main entry point for the semantic search pipeline:
1. Loads `pipeline/data/output/ai_articles_enriched.csv`.
2. Generates embeddings using `search_engine.py`.
3. Stores embeddings as list/array of floats in a DuckDB table.
4. Computes the top 3 most similar articles (excluding itself) for every article.
5. Filters the dataset based on requirements:
   - Category = `AI_ML` OR Industry = `AI/ML`
   - Published between 2022-2024
   - Revenue >= $50M USD
6. Map metadata columns to match requested schema:
   - `meta_industry` -> `industry`
   - `meta_founded_year` -> `founded_year`
   - `meta_headquarters` -> `headquarters`
   - `meta_employee_count` -> `employee_count`
   - `meta_is_public` -> `is_public`
   - `meta_stock_ticker` -> `stock_ticker`
7. Saves the output CSV to `semantic_search/output/filtered_ai_articles_with_embeddings.csv`.

### Verification & Testing

#### [NEW] [test_search.py](file:///Users/huangpan/Documents/YipitData/takehome_yd/semantic_search/tests/test_search.py)
Pytest unit tests verifying:
- Embedding generation.
- Cosine similarity calculation.
- DuckDB table creation & query functions.
- Hybrid search functionality.
- Export file schema, row counts, and filters.

---

## Documentation

#### [NEW] [README.md](file:///Users/huangpan/Documents/YipitData/takehome_yd/semantic_search/README.md)
Concise readme (Max 1 page) explaining:
- Installation instructions (dependencies).
- How to run the pipeline.
- Example usage of key functions.
- System requirements.

#### [NEW] [EXPLAIN.md](file:///Users/huangpan/Documents/YipitData/takehome_yd/semantic_search/EXPLAIN.md)
Technical explanation (Max 1.5 pages) covering:
- Our approach and architectural decisions.
- Choice of embedding model.
- Edge cases in data cleaning & validation.
- Performance vs. accuracy trade-offs.
- Future improvements.

---

## Verification Plan

### Automated Tests
Run the pytest suite to verify correctness:
```bash
./.venv/bin/pytest semantic_search/tests
```

### Manual Verification
1. Run the semantic search pipeline:
   ```bash
   ./.venv/bin/python semantic_search/pipeline.py
   ```
2. Verify the output CSV `semantic_search/output/filtered_ai_articles_with_embeddings.csv`:
   - Checks matching article count is 48.
   - Check headers match exactly.
   - Verify `top_similar_articles` lists do not contain the article's own ID.
