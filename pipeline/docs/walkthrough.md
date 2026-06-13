# Walkthrough — YipitData Core ETL Pipeline

## What Was Built

A fully modular Python ETL pipeline with zero ML dependencies.

### Files Created

| File | Purpose |
|---|---|
| [pipeline.py](file:///Users/huangpan/Documents/YipitData/takehome_yd/pipeline.py) | Main 4-stage orchestrator with CLI |
| [cleaning/revenue.py](file:///Users/huangpan/Documents/YipitData/takehome_yd/cleaning/revenue.py) | Revenue parsing, currency conversion, range midpoint |
| [cleaning/dates.py](file:///Users/huangpan/Documents/YipitData/takehome_yd/cleaning/dates.py) | Date normalization across 7 formats |
| [cleaning/categories.py](file:///Users/huangpan/Documents/YipitData/takehome_yd/cleaning/categories.py) | 19→6 category taxonomy mapping |
| [enrichment/metadata.py](file:///Users/huangpan/Documents/YipitData/takehome_yd/enrichment/metadata.py) | Metadata join, derived fields, AI filter |
| [README.md](file:///Users/huangpan/Documents/YipitData/takehome_yd/README.md) | Setup + usage instructions |
| [EXPLAIN.md](file:///Users/huangpan/Documents/YipitData/takehome_yd/EXPLAIN.md) | Decisions, trade-offs, edge cases |
| [requirements.txt](file:///Users/huangpan/Documents/YipitData/takehome_yd/requirements.txt) | Only `python-dateutil` |
| [ai_articles_enriched.csv](file:///Users/huangpan/Documents/YipitData/takehome_yd/ai_articles_enriched.csv) | Output (326 rows, 22 columns) |

---

## Pipeline Run Results

```
500 raw rows  →  326 filtered rows  →  ai_articles_enriched.csv
Revenue errors: 0 | Date errors: 0 | Category errors: 0
Metadata match: 500/500 (100%)
```

**Category breakdown in output:**

| Category | Count |
|---|---|
| AI_ML | 103 |
| Data_Analytics | 86 |
| Cloud_Computing | 41 |
| FinTech | 37 |
| Cybersecurity | 30 |
| SaaS_Software | 29 |

**Company size in output:**

| Size | Count |
|---|---|
| Medium (10K–30K) | 185 |
| Large (>30K) | 106 |
| Small (<10K) | 35 |

---

## Key Fixes During Implementation

- Discovered ISO 8601 datetime strings (`2021-09-11T00:00:00Z`) in the data not covered by initial format list → added `%Y-%m-%dT%H:%M:%SZ` as the first format to try. Final run: **zero date warnings**.

---

## Verification

- ✅ Pipeline exits with code 0
- ✅ 22-column output schema matches spec
- ✅ `pub_year` populated for all 326 output rows
- ✅ Revenue converts correctly (`$0.10B` → `100000000`)
- ✅ Dates normalized to `YYYY-MM-DD` ISO format
- ✅ `company_age` and `company_size_category` present and logical
- ✅ All 500 companies matched to metadata (0 unmatched)
