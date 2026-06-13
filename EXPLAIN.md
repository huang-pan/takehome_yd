# EXPLAIN.md — System Design Decisions & Evolution

This document outlines the architecture, design choices, and evolution of the YipitData Tech News ETL and Semantic Search pipeline.

---

## Component Deep Dives
- **Core ETL decisions**: Detailed parsing heuristics and validation schemas are documented in [pipeline/EXPLAIN.md](file:///Users/huangpan/Documents/YipitData/takehome_yd/pipeline/EXPLAIN.md).
- **Search and Vector DB decisions**: Choice of embedding model and hybrid SQL/similarity details are documented in [search/EXPLAIN.md](file:///Users/huangpan/Documents/YipitData/takehome_yd/search/EXPLAIN.md).

---

## Architectural Evolution

The pipeline transitions from standard Python ETL to advanced semantic search:
- **String Distance to Neural Semantics**: Part 1 matches company names using `difflib.get_close_matches` (low overhead, no models needed). Part 2/3 uses neural sentence-embeddings (`all-MiniLM-L6-v2`) to capture deep conceptual meanings in article titles and summaries.
- **Relational Data to Vector Storage**: Cleaned data is indexed in an in-memory DuckDB database to allow structured SQL querying integrated directly with vector similarity computations.

---

## Key Design Decisions

### 1. Core ETL (Part 1)
- **Midpoint revenue parsing**: Captures numeric value and multiplier, handles currency symbols (USD conversion), and uses the midpoint for ranges (policy decision).
- **Ambiguous date normalizer**: Deterministic `strptime` formats with an EU heuristic (if the first token >12, use `D/M/Y`, otherwise default to `M/D/Y`).
- **Pydantic schemas**: Soft row-level validation (invalid rows logged and skipped) with hard column-level boundaries to prevent data corruption.

### 2. Semantic Search & DuckDB (Part 2 & 3)
- **all-MiniLM-L6-v2 model**: Small size (~90MB), fast execution on CPUs, and outputs unit-normalized vectors where cosine similarity simplifies to dot products.
- **Hybrid Search strategy**: Executes SQL filtering *first* inside DuckDB using column indexing, then computes cosine similarity *only* on the filtered subset. This is computationally much more efficient than full-table similarity calculations.

---

## Edge Cases & Environment Challenges

- **PyTorch & NumPy Version Conflict**: The available platform PyTorch version is capped at `2.2.2`, which is incompatible with NumPy 2.x and causes crash errors. Additionally, newer `transformers` versions drop PyTorch if `torch < 2.4.0` is installed. We resolved this by explicitly pinning `numpy<2.0.0`, `sentence-transformers==2.7.0`, and `transformers<4.41.0`.
- **Self-Similarity Exclusion**: When precomputing top-K most similar articles, the search logic explicitly excludes the source article ID to avoid returning itself.
- **JSON Serialization**: Custom serialization converts DuckDB's NumPy ndarrays into standard lists (`.tolist()`) prior to JSON serialization for CSV export.
