# Semantic Search & Vector DB Component

Integrates sentence embeddings (`all-MiniLM-L6-v2`), cosine similarity, and DuckDB storage to provide semantic search and hybrid querying capabilities.

---

## Installation & Requirements
- Python 3.10+
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```
  *(Packages are explicitly pinned to numpy<2.0, sentence-transformers==2.7.0, and transformers<4.41.0 to guarantee compatibility with PyTorch 2.2.2).*

---

## How to Run

```bash
# Execute search pipeline (generates search/output/filtered_ai_articles_with_embeddings.csv)
PYTHONPATH=. python search/pipeline.py

# Run unit tests
PYTHONPATH=. pytest search/tests -v
```

---

## Programmatic Usage Example

```python
import pandas as pd
from search.search_engine import SemanticSearchEngine

# 1. Initialize and load data/embeddings
engine = SemanticSearchEngine()
df = pd.read_csv("pipeline/data/output/ai_articles_enriched.csv")
texts = (df["title"] + ". " + df["summary"]).tolist()
embeddings = engine.generate_embeddings(texts)
engine.load_data(df, embeddings)

# 2. Vector Similarity Search
similar = engine.find_similar_articles("NVIDIA financial results", top_k=5)

# 3. Hybrid Search (SQL Filters + Vector Similarity)
sql_filter = "pub_year BETWEEN 2022 AND 2024 AND revenue_usd >= 50000000"
hybrid = engine.hybrid_search("large language models", sql_filter, top_k=5)
```

---

## Output Description
Output is written to `search/output/filtered_ai_articles_with_embeddings.csv` containing:
- Renamed canonical metadata columns (`industry`, `is_public`, etc.).
- `embedding`: The 384-dimensional vector representation.
- `top_similar_articles`: List of article IDs matching the top 3 most similar articles.
