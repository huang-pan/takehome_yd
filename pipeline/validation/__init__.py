"""
validation package — Pydantic v2 schemas for each ETL stage boundary.

Three schemas enforce column presence, types, and value ranges:

  RawArticleSchema    → after Stage 1 (Ingest)
  CleanedArticleSchema → after Stage 2 (Clean)
  EnrichedArticleSchema → after Stage 3/4 (Enrich + Filter)

The validate_stage() function runs row-level validation, logs every
violation, and returns the valid rows plus a summary error count.
A structural check (validate_columns()) raises immediately if required
columns are missing from the batch.
"""

from .schemas import (
    RawArticleSchema,
    CleanedArticleSchema,
    EnrichedArticleSchema,
    validate_stage,
    validate_columns,
)

__all__ = [
    "RawArticleSchema",
    "CleanedArticleSchema",
    "EnrichedArticleSchema",
    "validate_stage",
    "validate_columns",
]
