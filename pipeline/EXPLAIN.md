# EXPLAIN.md — Technical Decisions & Trade-offs

## Approach
Decomposed the pipeline into single-responsibility layers:
1. **`cleaning/`**: Stateless pure functions transforming one field at a time.
2. **`enrichment/`**: Joins company metadata and filters AI relevance.
3. **`validation/`**: Pydantic v2 schemas enforcing boundaries.
4. **`config/`**: YAML filter configuration loader.
5. **`pipeline.py`**: Thin orchestrator for CLI I/O and execution.

For a visual overview of the modules and data flow, see the [Architecture Diagrams](https://github.com/huang-pan/takehome_yd/blob/main/pipeline/MERMAID.md).

---

## Key Design Decisions

- **Revenue Parsing**: Detects currency symbols (converts to USD), captures magnitude suffixes (`M`, `B`, `K`), parses ranges using their midpoint, and returns integer USD.
- **Date Normalization**: Standardizes 7 date formats deterministically using `strptime`. Resolves US/EU ambiguity (`02/03/2023`) via a day heuristic: if the first number is >12, it is treated as EU `D/M/Y`, otherwise defaults to US `M/D/Y`.
- **Fuzzy Name Matching**: Exact match fallback using `difflib.get_close_matches` (cutoff=0.75) to handle name drift without heavy ML libraries.
- **Schema Validation**: Uses three Pydantic v2 schemas (`Raw`, `Cleaned`, `Enriched`). Employs soft validation at row-level (bad rows are skipped and logged; pipeline does not crash).

---

## Edge Cases Handled
- **Revenue**: `N/A`/`null`/empty/NaN → 0; ranges midpoint; currencies converted (GBP×1.27, EUR×1.10, JPY÷150).
- **Date**: UTC timezone Z syntax resolved first; string months resolved; missing values → `None`.
- **Category**: Unknown categories standardized → `"Unknown"`.
- **Company Metadata**: Unmatched metadata handled gracefully with `metadata_matched=False` and null fields.

---

## Trade-offs
- **Stdlib over Pandas**: Part 1 uses pure python (DictReader/DictWriter) to avoid heavy dependencies and keep memory overhead minimal at the cost of slightly verbose row iteration.
- **difflib over Embeddings**: fast, local, zero model download overhead, sufficient for typo/drift name matching.
- **Soft Validation**: Drops invalid rows rather than crashing, favoring continuous data processing.

---

## What I Would Improve With More Time

1. **Parallel Processing**: For large scale datasets, utilize `ProcessPoolExecutor` to clean and parse rows concurrently.
2. **Atomic Writes**: Write results to a temporary file and atomically rename it upon successful completion to prevent corrupt or partial output files on failure.
3. **Config Validation**: Validate the configuration keys in `filter_config.yaml` against the schema enums during initialization to catch typing errors early.
4. **CI/CD Integration**: Run the pytest suite automatically in a GitHub Actions pipeline on every commit.

---

## Evolution: Integration with Semantic Search (Part 2 & 3)
The ETL output `ai_articles_enriched.csv` serves as the ingest for the `search` module. While Part 1 uses lightweight CPU-bound string matching (`difflib`), the `search` module upgrades to neural sentence-embeddings (`all-MiniLM-L6-v2`) and integrates with DuckDB to support hybrid vector similarity and SQL queries.
