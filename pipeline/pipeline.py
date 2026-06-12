#!/usr/bin/env python3
"""
pipeline.py — YipitData Core ETL Pipeline (main entry point).

Usage
-----
    python pipeline.py
    python pipeline.py --input tech_news.csv --metadata company_metadata.json --output ai_articles_enriched.csv

The pipeline executes these stages:
  1. Ingest   — load raw CSV
  2. Clean    — revenue, dates, categories
  3. Enrich   — join company metadata, derive fields
  4. Export   — write ai_articles_enriched.csv  (all rows, same count as input)

Optional:
  --filter    Restrict output to AI/ML-relevant articles only
"""

import argparse
import csv
import logging
import sys
from pathlib import Path

from cleaning import clean_revenue, normalize_date, standardize_category
from cleaning.dates import extract_date_parts
from config.loader import load_filter_config
from enrichment.metadata import enrich_with_metadata, filter_ai_relevant, load_metadata
from validation import (
    RawArticleSchema,
    CleanedArticleSchema,
    EnrichedArticleSchema,
    validate_stage,
)

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pipeline")

# ---------------------------------------------------------------------------
# Output column order
# ---------------------------------------------------------------------------
OUTPUT_COLUMNS = [
    # Original article fields
    "article_id",
    "title",
    "company_name",
    "published_date",
    "pub_year",
    "pub_quarter",
    "pub_month",
    "category",
    "revenue_usd",
    "summary",
    "url",
    "author",
    "word_count",
    # Metadata fields
    "metadata_matched",
    "meta_founded_year",
    "meta_headquarters",
    "meta_employee_count",
    "meta_industry",
    "meta_is_public",
    "meta_stock_ticker",
    # Derived fields
    "company_age",
    "company_size_category",
]


# ---------------------------------------------------------------------------
# Stage 1: Ingest
# ---------------------------------------------------------------------------

def ingest(path: Path) -> list[dict]:
    """Load raw CSV rows as a list of dicts."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    logger.info("Ingested %d rows from '%s'", len(rows), path)
    return rows


# ---------------------------------------------------------------------------
# Stage 2: Clean
# ---------------------------------------------------------------------------

def clean(rows: list[dict]) -> list[dict]:
    """
    Apply all cleaning transformations to raw rows.

    - Revenue → integer USD (``revenue_usd``)
    - Published date → datetime + year/quarter/month parts
    - Category → canonical string
    """
    cleaned = []
    revenue_errors = date_errors = category_errors = 0

    for row in rows:
        # --- Revenue ---
        raw_rev = row.get("revenue")
        try:
            row["revenue_usd"] = clean_revenue(raw_rev)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Revenue parse error for '%s': %s", raw_rev, exc)
            row["revenue_usd"] = 0
            revenue_errors += 1

        # --- Date ---
        raw_date = row.get("published_date")
        try:
            dt = normalize_date(raw_date)
            parts = extract_date_parts(dt)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Date parse error for '%s': %s", raw_date, exc)
            dt = None
            parts = {"pub_year": None, "pub_quarter": None, "pub_month": None}
            date_errors += 1
        row.update(parts)
        # Keep original date string; add parsed ISO for reference
        row["published_date"] = dt.strftime("%Y-%m-%d") if dt else row.get("published_date", "")

        # --- Category ---
        raw_cat = row.get("category")
        try:
            row["category"] = standardize_category(raw_cat)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Category error for '%s': %s", raw_cat, exc)
            row["category"] = "Unknown"
            category_errors += 1

        cleaned.append(row)

    logger.info(
        "Cleaning complete — revenue errors: %d, date errors: %d, category errors: %d",
        revenue_errors,
        date_errors,
        category_errors,
    )
    return cleaned


# ---------------------------------------------------------------------------
# Stage 3 & 4: Enrich + Filter
# ---------------------------------------------------------------------------

def enrich_and_filter(
    rows: list[dict],
    metadata_path: Path,
    apply_filter: bool = False,
    config_path: Path | None = None,
) -> list[dict]:
    """Join metadata, compute derived fields, and optionally filter."""
    metadata = load_metadata(metadata_path)
    enriched = enrich_with_metadata(rows, metadata)
    if apply_filter:
        filter_cfg = load_filter_config(config_path)
        enriched = filter_ai_relevant(enriched, filter_cfg)
    return enriched


# ---------------------------------------------------------------------------
# Stage 5: Export
# ---------------------------------------------------------------------------

def export(rows: list[dict], path: Path) -> None:
    """Write enriched rows to CSV with a consistent column order."""
    if not rows:
        logger.warning("No rows to export — output file will be empty")

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=OUTPUT_COLUMNS,
            extrasaction="ignore",  # drop any extra keys silently
        )
        writer.writeheader()
        writer.writerows(rows)

    logger.info("Exported %d rows to '%s'", len(rows), path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="YipitData Core ETL Pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input",
        default="data/input/tech_news.csv",
        help="Path to input CSV file",
    )
    parser.add_argument(
        "--metadata",
        default="data/input/company_metadata.json",
        help="Path to company metadata JSON file",
    )
    parser.add_argument(
        "--output",
        default="data/output/ai_articles_enriched.csv",
        help="Path for the output enriched CSV file",
    )
    parser.add_argument(
        "--filter",
        action="store_true",
        help="Restrict output to AI/ML-relevant articles (default: include all rows)",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to filter config YAML (default: config/filter_config.yaml). "
             "Only used when --filter is set.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity",
    )
    return parser


def run(
    input_path: Path,
    metadata_path: Path,
    output_path: Path,
    apply_filter: bool = False,
    config_path: Path | None = None,
) -> None:
    """Execute the full ETL pipeline."""
    logger.info("=== YipitData ETL Pipeline — START ===")
    total_validation_errors = 0

    # Stage 1: Ingest
    logger.info("[1/4] Ingesting data…")
    raw_rows = ingest(input_path)

    logger.info("[1/4] Validating raw schema…")
    raw_rows, errs = validate_stage(raw_rows, RawArticleSchema, stage="raw")
    total_validation_errors += errs

    # Stage 2: Clean
    logger.info("[2/4] Cleaning data…")
    clean_rows = clean(raw_rows)

    logger.info("[2/4] Validating cleaned schema…")
    clean_rows, errs = validate_stage(clean_rows, CleanedArticleSchema, stage="clean")
    total_validation_errors += errs

    # Stage 3 & 4: Enrich + Filter
    logger.info("[3/4] Enriching with metadata%s…",
                " (filtering enabled)" if apply_filter else "")
    final_rows = enrich_and_filter(
        clean_rows, metadata_path, apply_filter, config_path
    )

    logger.info("[3/4] Validating enriched schema…")
    final_rows, errs = validate_stage(final_rows, EnrichedArticleSchema, stage="enriched")
    total_validation_errors += errs

    # Stage 5: Export
    logger.info("[4/4] Exporting results…")
    export(final_rows, output_path)

    logger.info("=== YipitData ETL Pipeline — DONE ===")
    logger.info(
        "Summary: %d raw rows → %d output rows → '%s' | validation errors: %d",
        len(raw_rows), len(final_rows), output_path, total_validation_errors,
    )


def main() -> int:
    """Entry point; returns exit code."""
    parser = build_parser()
    args = parser.parse_args()

    # Adjust log level if requested
    logging.getLogger().setLevel(args.log_level)

    input_path    = Path(args.input)
    metadata_path = Path(args.metadata)
    output_path   = Path(args.output)

    # Validate inputs exist
    for p in (input_path, metadata_path):
        if not p.exists():
            logger.error("Input file not found: '%s'", p)
            return 1

    try:
        run(
            input_path=input_path,
            metadata_path=metadata_path,
            output_path=output_path,
            apply_filter=args.filter,
            config_path=Path(args.config) if args.config else None,
        )
    except Exception as exc:
        logger.exception("Pipeline failed: %s", exc)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
