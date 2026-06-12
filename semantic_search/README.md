# Semantic Search Component - YipitData Tech News

This subdirectory implements semantic search on AI-related articles using sentence embeddings, cosine similarity, and DuckDB storage.

## System Requirements
- Python 3.10+
- macOS or Linux (tested on macOS)
- Standard Unix build tools (for compiling dependencies if needed)

## Installation Instructions

1. **Activate the Virtual Environment**
   Ensure your Python virtual environment is active:
   ```bash
   source .venv/bin/activate
   ```

2. **Install Dependencies**
   Install the required libraries specified in `requirements.txt`:
   ```bash
   pip install -r semantic_search/requirements.txt
   ```
    *Note: Due to PyTorch 2.2.2 compatibility constraints with NumPy 2.x, the project requirements have been explicitly pinned in `requirements.txt` to: `numpy<2.0.0`, `sentence-transformers==2.7.0`, and `transformers<4.41.0` to guarantee out-of-the-box compatibility.*

## Running the Pipeline

To run the semantic search extraction and export pipeline:
```bash
PYTHONPATH=. python semantic_search/pipeline.py
```
This script does the following:
1. Ingests enriched articles from `pipeline/data/output/ai_articles_enriched.csv`.
2. Generates 384-dimensional sentence embeddings using the `all-MiniLM-L6-v2` model.
3. Computes the top 3 most similar articles (excluding itself) for every article in the dataset.
4. Loads data and embeddings into DuckDB.
5. Performs a SQL query to filter for AI/ML articles published between 2022-2024 with company revenue >= $50M.
6. Maps metadata columns to canonical names (`meta_industry` -> `industry`, etc.).
7. Exports the final output to `semantic_search/output/filtered_ai_articles_with_embeddings.csv`.

## Key Function Usage Examples

You can import and use the `SemanticSearchEngine` class programmatically for vector similarity and hybrid search queries.

```python
import pandas as pd
import numpy as np
from semantic_search.search_engine import SemanticSearchEngine

# 1. Initialize engine
engine = SemanticSearchEngine(model_name="all-MiniLM-L6-v2")

# 2. Load data
df = pd.read_csv("pipeline/data/output/ai_articles_enriched.csv")
texts = (df["title"] + ". " + df["summary"]).tolist()
embeddings = engine.generate_embeddings(texts)
engine.load_data(df, embeddings)

# 3. Vector Similarity Search (query text)
# Returns a list of (article_id, cosine_similarity_score)
similar_to_query = engine.find_similar_articles("NVIDIA financial results", top_k=5)
print(similar_to_query)

# 4. Vector Similarity Search (by existing article_id)
similar_to_article = engine.find_similar_articles("ART0001", top_k=3)
print(similar_to_article)

# 5. Hybrid Search (SQL filters + Vector Similarity)
sql_filter = "pub_year BETWEEN 2022 AND 2024 AND revenue_usd >= 50000000"
hybrid_results = engine.hybrid_search("large language models", sql_filter, top_k=5)
print(hybrid_results)
```

## Running Unit Tests

Run the test suite using pytest:
```bash
PYTHONPATH=. pytest semantic_search/tests
```
