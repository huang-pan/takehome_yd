# YipitData Data Engineering Take-Home Assignment

This project contains two primary modules to process, validate, and query tech-news articles.

---

## Architecture Overview

1. **Core ETL Pipeline ([pipeline](file:///Users/huangpan/Documents/YipitData/takehome_yd/pipeline/))**
   - Ingests raw articles, cleans noisy revenues/currencies, normalizes dates, maps categories, joins company metadata, and validates schemas using Pydantic.
   - For details, see [pipeline/README.md](https://github.com/huang-pan/takehome_yd/blob/main/pipeline/README.md).

2. **Semantic Search & Vector DB ([search](file:///Users/huangpan/Documents/YipitData/takehome_yd/search/))**
   - Generates 384-dimensional sentence embeddings (`all-MiniLM-L6-v2`), precomputes article similarity, loads data into DuckDB, and exposes hybrid SQL + vector queries.
   - For details, see [search/README.md](https://github.com/huang-pan/takehome_yd/blob/main/search/README.md).

---

## Installation & Setup

Ensure Python 3.10+ is installed:
```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install all required dependencies
pip install -r requirements.txt
```

---

## Running the Pipelines

```bash
# Run Core ETL Pipeline (generates ai_articles_enriched.csv)
python pipeline/pipeline.py

# Run Semantic Search Pipeline (generates filtered_ai_articles_with_embeddings.csv)
PYTHONPATH=. python search/pipeline.py
```

---

## Running All Tests

Execute all 256 unit tests across both modules:
```bash
PYTHONPATH=. pytest pipeline/tests search/tests -v
```
