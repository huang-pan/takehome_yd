# YipitData Core ETL Pipeline — Implementation Plan

## Overview

Build a production-quality Python ETL pipeline that ingests `tech_news.csv` and `company_metadata.json`, applies data cleaning/transformation, enriches with metadata, and outputs `ai_articles_enriched.csv`. Deliverables also include `README.md`, `EXPLAIN.md`, and `requirements.txt`.

---

## Data Observations

- **500 rows**, 10 columns: `article_id`, `title`, `company_name`, `published_date`, `category`, `revenue`, `summary`, `url`, `author`, `word_count`
- **21 distinct companies** in CSV, all present in metadata (perfect match — no fuzzy matching needed, but will still implement)
- **19 messy category values** → 8 clean canonical categories
- **Revenue**: multi-currency (USD/GBP/EUR/JPY), varied formats (B/M/K suffixes, raw numbers, ranges, N/A)
- **Dates**: 6+ formats (ISO, US MM/DD/YYYY, EU DD/MM/YYYY, "21 Feb 2020", "October 19, 2022", "23-08-2023")

---

## Proposed File Structure

```
takehome_yd/
├── pipeline.py              # Main entry point — orchestrates ETL
├── cleaning/
│   ├── __init__.py
│   ├── revenue.py           # Revenue cleaning logic
│   ├── dates.py             # Date normalization logic
│   └── categories.py        # Category standardization logic
├── enrichment/
│   ├── __init__.py
│   └── metadata.py          # Company metadata joining & validation
├── ai_articles_enriched.csv # Output
├── README.md
├── EXPLAIN.md
└── requirements.txt
```

---

## Proposed Changes

### Revenue Cleaner — [NEW] cleaning/revenue.py

Handles all revenue edge cases:
- Strip currency symbols (£, €, ¥, $), remove commas
- Detect suffix multipliers: `B`/`billion` → ×1B, `M`/`million` → ×1M, `K` → ×1K
- Handle ranges: `"$10M - $20M"` → midpoint
- Currency conversion: GBP×1.27, EUR×1.1, JPY÷150
- Null/invalid → 0 (integer output)

### Date Normalizer — [NEW] cleaning/dates.py

Handles all date format variants:
- `2022-02-17` (ISO)
- `02/23/2023` (US M/D/Y) vs `23-08-2023` (EU D/M/Y) — **key ambiguity**: use `dateutil.parser` with `dayfirst=False` as default, fallback with `dayfirst=True`
- `21 Feb 2020`, `October 19, 2022` (natural language)
- Returns `datetime` object; invalid → `NaT`
- Extracts: `pub_year`, `pub_quarter`, `pub_month`

### Category Standardizer — [NEW] cleaning/categories.py

Mapping taxonomy:
| Raw Values | Canonical |
|---|---|
| AI/ML, AI & ML, Artificial Intelligence, Machine Learning | AI_ML |
| Analytics, Data Analytics, Big Data | Data_Analytics |
| Cloud, Cloud Computing, Cloud Services | Cloud_Computing |
| Cybersecurity, Security, InfoSec | Cybersecurity |
| FinTech, Finance, Financial Technology | FinTech |
| SaaS, Enterprise Software, Software | SaaS_Software |

### Metadata Enricher — [NEW] enrichment/metadata.py

- Joins metadata by `company_name` (exact match first, fuzzy fallback via `difflib`)
- Flags unmatched companies in logs
- Derives:
  - `company_age` = article `pub_year` − `founded_year`
  - `company_size_category`: Small (<10K), Medium (10K–30K), Large (>30K)
- Industry-based filtering: keeps articles where **article category OR company industry** maps to AI/ML/Data Analytics domains

### Main Pipeline — [NEW] pipeline.py

Orchestrates the full ETL with:
- CLI args for input/output paths
- Logging at INFO level
- Step-by-step processing with row counts at each stage
- Outputs `ai_articles_enriched.csv`

### Documentation — [NEW] README.md, EXPLAIN.md, requirements.txt

Concise docs covering setup, usage, decisions, and trade-offs.

---

## Key Design Decisions

1. **Standard library preferred**: Use `csv`, `json`, `datetime`, `re`, `logging`, `difflib`. Only `pandas` (optional fast path) and `python-dateutil` added as optional deps.
2. **No sentence-transformers**: The task says "recommend" — embedding models aren't needed for this pipeline (no semantic search/similarity task specified beyond fuzzy name matching which `difflib` handles fine).
3. **Date ambiguity**: `dateutil.parser` with US-first convention is the default; EU-style dates detected heuristically when day >12.
4. **Output filter**: `ai_articles_enriched.csv` filters to AI/ML-relevant articles (category is `AI_ML` or `Data_Analytics`, OR company industry is `AI/ML` or `Data Analytics`).

---

## Verification Plan

### Automated
- `python3 pipeline.py` — end-to-end run, check exit code 0
- Validate output CSV row count and column presence
- Spot-check revenue parsing for known tricky values

### Manual
- Review `ai_articles_enriched.csv` in spreadsheet
- Confirm derived fields (`company_age`, `company_size_category`) look correct
