# YipitData Core ETL Pipeline

A clean, repeatable Python pipeline that ingests messy technology-news articles, normalizes the data, joins company metadata, and produces an enriched CSV ready for analysis.

---

## System Requirements

- Python 3.11+ (venv recommended)
- No ML libraries required

## Installation

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## How to Run

```bash
# Default — all 500 rows in, 500 rows out
python pipeline.py

# Custom paths
python pipeline.py --input path/to/tech_news.csv \
                   --metadata path/to/company_metadata.json \
                   --output path/to/output.csv

# Restrict output to AI/ML-relevant articles (reads config/filter_config.yaml)
python pipeline.py --filter

# Use a custom filter config
python pipeline.py --filter --config path/to/my_filter.yaml

# Verbose debug logging
python pipeline.py --log-level DEBUG
```

---

## Project Structure

```
├── pipeline.py          # Main entry point (4-stage ETL orchestrator)
├── cleaning/
│   ├── revenue.py       # Revenue parsing & currency conversion
│   ├── dates.py         # Date normalization (7 formats)
│   └── categories.py    # Category taxonomy mapping (19 → 6)
├── enrichment/
│   └── metadata.py      # Metadata join, derived fields, configurable filter
├── validation/
│   └── schemas.py       # Pydantic v2 schemas for each stage boundary
├── config/
│   ├── filter_config.yaml  # AI-relevance filter lists (editable)
│   └── loader.py           # YAML config loader & FilterConfig dataclass
├── tests/
│   ├── test_revenue.py     # 93 revenue cleaner tests
│   ├── test_dates.py       # 50 date normalizer tests
│   ├── test_validation.py  # 83 schema validation tests
│   └── test_config.py      # 34 config loader tests
├── data/
│   ├── input/
│   │   ├── tech_news.csv
│   │   └── company_metadata.json
│   └── output/
│       └── ai_articles_enriched.csv
├── requirements.txt
├── README.md
├── EXPLAIN.md
└── semantic_search/     # Part 2 & 3: Vector Similarity Search & DuckDB Integration
    ├── requirements.txt # Dependencies for semantic search
    ├── search_engine.py # Core SemanticSearchEngine
    ├── pipeline.py      # Main semantic search pipeline script
    ├── README.md        # Semantic search running guide
    ├── EXPLAIN.md       # Technical decisions for vector storage
    ├── MERMAID.md       # Semantic search architecture diagrams
    ├── output/          # Directory containing final exported CSV
    └── tests/           # Semantic search unit tests
```

---

## Integrating with Semantic Search (Part 2 & 3)

The core ETL pipeline outputs `pipeline/data/output/ai_articles_enriched.csv`, which is then processed by the semantic search system located in `semantic_search/`. 

To set up, run, and test the semantic search features:
```bash
# 1. Install semantic search dependencies
pip install -r semantic_search/requirements.txt

# 2. Run the semantic search pipeline
PYTHONPATH=. python semantic_search/pipeline.py

# 3. Run the semantic search test suite
PYTHONPATH=. pytest semantic_search/tests
```
See [semantic_search/README.md](file:///Users/huangpan/Documents/YipitData/takehome_yd/semantic_search/README.md) for detailed information.

---

## Configuring the AI-Relevance Filter

Edit `config/filter_config.yaml` to change which categories and industries
are considered AI/ML-relevant — no Python changes required:

```yaml
ai_relevant_categories:
  - AI_ML
  - Data_Analytics

ai_relevant_industries:
  - AI/ML
  - Data Analytics
```

Values must match the canonical forms used by the pipeline:
- **categories**: output of `cleaning/categories.py` (e.g. `"AI_ML"`)
- **industries**: values in `company_metadata.json` (e.g. `"AI/ML"`)

---

## Running Tests

```bash
python -m pytest tests/ -v
```

252 tests across four test modules, covering every edge case in the
revenue cleaner, date normalizer, schema validator, and config loader.

---

## Key Function Examples

```python
from cleaning import clean_revenue, normalize_date, standardize_category

clean_revenue("£245,788,308")     # → 312151151  (GBP → USD)
clean_revenue("$10M - $20M")      # → 15000000   (range midpoint)
clean_revenue("N/A")              # → 0

normalize_date("21 Feb 2020")     # → datetime(2020, 2, 21)
normalize_date("02/23/2023")      # → datetime(2023, 2, 23)
normalize_date("23-08-2023")      # → datetime(2023, 8, 23)  (EU detected)

standardize_category("Artificial Intelligence")  # → "AI_ML"
standardize_category("Big Data")                 # → "Data_Analytics"
standardize_category("InfoSec")                  # → "Cybersecurity"
```

```python
from config.loader import load_filter_config

cfg = load_filter_config()                    # loads config/filter_config.yaml
cfg = load_filter_config("my_filter.yaml")   # custom path
cfg.ai_relevant_categories                   # frozenset — immutable
```

---

## Output

`data/output/ai_articles_enriched.csv` — all input rows enriched with:

| New Column | Description |
|---|---|
| `revenue_usd` | Cleaned revenue in integer USD |
| `pub_year / pub_quarter / pub_month` | Extracted date parts |
| `category` | Canonical category (e.g. `AI_ML`) |
| `meta_*` | All company metadata fields |
| `company_age` | Article year − company founding year |
| `company_size_category` | Small / Medium / Large by headcount |
| `metadata_matched` | Whether company was found in metadata |

Pass `--filter` to restrict to AI/ML-relevant rows only (defined in `config/filter_config.yaml`).
