# EXPLAIN.md — Technical Decisions & Trade-offs

## Approach

I decomposed the pipeline into four single-responsibility layers:

1. **`cleaning/`** — stateless pure functions that transform one field at a time, making them easy to test and reuse independently.
2. **`enrichment/`** — joins external data and derives new fields; isolated from cleaning logic.
3. **`validation/`** — Pydantic v2 schemas that enforce column presence, types, and value ranges at each stage boundary.
4. **`config/`** — YAML-driven configuration for the AI-relevance filter, decoupled from all business logic.
5. **`pipeline.py`** — thin orchestrator that wires stages together, handles CLI I/O, and owns logging.

This separation means any individual cleaner, schema, or filter rule can be changed without touching the rest of the pipeline.

---

## Key Design Decisions

### Revenue Cleaning

Revenue strings were the noisiest field. My strategy:

1. **Symbol → currency**: detect `$`, `£`, `€`, `¥` first; fall back to inline ISO codes like `"1599.7M USD"`.
2. **Magnitude suffix**: regex captures the numeric part and its suffix (`B`/`billion`, `M`/`million`, `K`) separately, then multiplies.
3. **Ranges** (`"$10M - $20M"`): parse both endpoints independently and take the midpoint. This is a policy decision — using the midpoint is conservative and reasonable when the true value is unknown.
4. **Conversion rates**: applied at parse time (GBP×1.27, EUR×1.10, JPY÷150), returning integer USD.

### Date Normalization

The dataset contains seven distinct formats. The hardest ambiguity is `02/03/2023` — is it Feb 3 (US) or Mar 2 (EU)?

**Decision**: I use a heuristic — if the leading numeric token is >12, it can only be a day, so the format must be EU (`D/M/Y`). Otherwise I default to US (`M/D/Y`), matching the dominant convention in English tech journalism. I apply `strptime` with an ordered list of format strings rather than `dateutil.parser.parse`, which gives deterministic, predictable behavior. ISO 8601 with UTC Z suffix (`2021-09-11T00:00:00Z`) is tried first since it is unambiguous.

**Trade-off**: `dateutil.parser` would handle more edge cases automatically but is harder to reason about for ambiguous inputs. Explicit `strptime` is more transparent and auditable.

### Category Standardization

I hardcoded a 19→6 mapping table rather than using string-distance or ML classification. The vocabulary is fully known (closed set), so an explicit lookup is both faster and easier to review. The mapping is defined in a single dict constant — easy to extend.

### Company Name Matching

All 21 companies in the CSV appear verbatim in `data/input/company_metadata.json`, so exact matching succeeds for all rows. I still implemented a `difflib.get_close_matches` fuzzy fallback (cutoff=0.75) to handle future data drift (e.g., `"Amazon Web Services"` vs `"AWS"`). I chose `difflib` over `sentence-transformers` because:
- No model download or GPU required
- ~10× faster at this scale
- Sufficient for company name variants (abbreviations, spacing differences)

### Schema Validation (Pydantic v2)

Three schemas enforce data quality at each stage boundary:

- **`RawArticleSchema`** (post-ingest): required fields non-empty, URL starts with `http(s)://`, `article_id` alphanumeric. `author` is optional (empty strings accepted — the dataset intentionally contains rows without authors).
- **`CleanedArticleSchema`** (post-clean): `revenue_usd ≥ 0` (int), category in the 7-value canonical `Literal`, date is ISO `YYYY-MM-DD` or empty, year/quarter/month in valid ranges, cross-field consistency (all date parts set or all None).
- **`EnrichedArticleSchema`** (post-enrich): extends cleaned schema with `metadata_matched=True` requiring non-null `meta_founded_year`, `meta_employee_count ≥ 0`, `company_age` in `[-10, 300]`, size category in `["Small","Medium","Large","Unknown"]`.

Validation is **soft** at the row level (bad rows are logged and excluded, the pipeline continues) but **hard** at the structural level (missing columns raise immediately before per-row validation begins).

### AI-Relevance Filter (YAML-configurable)

The filter is opt-in (`--filter` flag) so the output always contains all input rows by default. When enabled, an article is kept when **either** the article's canonical `category` OR the company's `meta_industry` appears in the configured sets — using OR maximises recall (a Cloud Computing article about NVIDIA, industry: AI/ML, is still relevant).

The category and industry lists live in `config/filter_config.yaml` as plain YAML lists. The `config/loader.py` module parses them into a frozen `FilterConfig` dataclass, keeping config loading fully decoupled from filtering logic. A custom config path can be supplied via `--config`.

---

## Edge Cases Handled

| Field | Edge case | Handling |
|---|---|---|
| Revenue | `N/A`, `null`, empty, NaN | → 0 |
| Revenue | `"$10M - $20M"` range | → midpoint |
| Revenue | JPY large integers (¥19B+) | → ÷150 |
| Date | EU date `23-08-2023` | Heuristic: leading token >12 → EU format |
| Date | ISO 8601 with UTC Z (`2021-09-11T00:00:00Z`) | Tried first, before date-only ISO |
| Date | `"October 19, 2022"` | `%B %d, %Y` strptime format |
| Date | Missing / `N/A` | → None; date-part columns → None |
| Category | Unmapped value | → `"Unknown"`, logged as warning |
| Company | Not in metadata | Flagged with `metadata_matched=False`, nulls for all meta fields |
| Author | Empty string | Accepted — field is optional in schema |

---

## Trade-offs

| Decision | Benefit | Cost |
|---|---|---|
| stdlib over pandas | Zero heavy deps, transparent code | Slightly more verbose row iteration |
| Explicit strptime formats | Deterministic, auditable | May miss very unusual formats |
| OR logic for AI filter | Higher recall | May include tangentially related articles |
| `difflib` over embeddings | Fast, no model download | Won't catch semantic paraphrases |
| Soft row-level validation | Pipeline never halts on one bad row | Invalid rows silently dropped from output |
| Frozen `FilterConfig` dataclass | Immutable config caught at load time | Requires re-load to change config at runtime |

---

## What I Would Improve With More Time

1. **Parallel processing** — for much larger inputs, use `concurrent.futures.ProcessPoolExecutor` for the cleaning stage.
2. **Idempotent output** — write to a temp file then atomically rename, preventing partial writes on failure.
3. **Config schema validation** — validate `filter_config.yaml` values against the canonical category/industry enums at load time, not just at filter time.
4. **CI pipeline** — run `pytest` on every commit with coverage reporting.

---

## Evolution: Integration with Semantic Search (Part 2 & 3)

The core ETL pipeline was designed to be modular and lightweight (Part 1). For Part 2 & 3, the output (`data/output/ai_articles_enriched.csv`) is fed into the `semantic_search` subdirectory. This represents an evolution in design decisions:
- **String Distance vs. Neural Embeddings**: While Part 1 uses `difflib.get_close_matches` for fast, CPU-bound string matching of company names, Part 2 upgrades the pipeline to use `sentence-transformers` (`all-MiniLM-L6-v2`) to capture deep semantic contexts from article titles and summaries.
- **Relational Data Storage to Vector DB**: The clean CSV dataset is loaded into an in-memory DuckDB instance to allow structured SQL querying integrated directly with vector similarity computations (hybrid search).
