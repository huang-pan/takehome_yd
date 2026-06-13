# YipitData Core ETL Pipeline

Stateless, schema-validated ETL pipeline that processes technology-news articles, normalizes dates/revenues, joins company metadata, and filters for relevance.

---

## System Requirements & Installation
- Python 3.10+
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```

---

## How to Run

```bash
# Default ETL (produces pipeline/data/output/ai_articles_enriched.csv with all 500 rows)
python pipeline/pipeline.py

# With AI/ML relevance filtering (reads config/filter_config.yaml)
python pipeline/pipeline.py --filter

# Show CLI options (custom inputs/outputs, logging levels)
python pipeline/pipeline.py --help
```

---

## Directory Structure
- `cleaning/`: Stateless modules parsing revenues, dates, and categories.
- `enrichment/`: Joins company metadata, determines age, size, and filters.
- `validation/`: Enforces stage data quality boundaries via Pydantic v2 schemas.
- `config/`: Editable relevance filter rules in `filter_config.yaml`.
- `tests/`: 265 comprehensive unit tests covering parsing, validation, and metadata enrichment.

---

## Running Tests

Execute core ETL test suite:
```bash
pytest pipeline/tests -v
```

---

## Output
Output is written to `pipeline/data/output/ai_articles_enriched.csv` containing cleaned fields (`revenue_usd`, ISO `published_date`, `pub_year/month/quarter`, canonical `category`) joined with metadata (`industry`, `headquarters`, `is_public`, etc.) and derived fields (`company_age`, `company_size_category`).
