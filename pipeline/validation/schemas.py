"""
schemas.py — Pydantic v2 schemas for each ETL pipeline stage boundary.

Stage 1 → RawArticleSchema
    Validates the raw CSV row immediately after ingestion.
    Checks all expected columns are present and non-empty where required.

Stage 2 → CleanedArticleSchema
    Validates after cleaning (revenue, date, category transforms).
    Enforces: revenue_usd ≥ 0 (int), canonical category, valid date
    parts (pub_year 1900-2100, pub_quarter 1-4, pub_month 1-12).

Stage 3/4 → EnrichedArticleSchema
    Validates after metadata join and derived field computation.
    Enforces: company_age plausibility, employee_count ≥ 0,
    company_size_category in allowed set.

Usage
-----
    from validation import validate_stage, CleanedArticleSchema
    valid_rows, error_count = validate_stage(rows, CleanedArticleSchema, stage="clean")
"""

import logging
import re
from typing import Any, Literal, Optional, Type

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)
from pydantic import ValidationError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants mirrored from cleaning/categories.py
# ---------------------------------------------------------------------------
CANONICAL_CATEGORIES = Literal[
    "AI_ML",
    "Data_Analytics",
    "Cloud_Computing",
    "Cybersecurity",
    "FinTech",
    "SaaS_Software",
    "Unknown",
]

SIZE_CATEGORIES = Literal["Small", "Medium", "Large", "Unknown"]

# ISO date pattern (YYYY-MM-DD)
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------------------------------------------------------------------------
# Stage 1 — Raw (post-ingest)
# ---------------------------------------------------------------------------

class RawArticleSchema(BaseModel):
    """
    Schema for a raw CSV row immediately after ingestion.

    All fields are strings (CSV reader produces strings).
    Validates required fields are present and non-empty.
    Optional fields (revenue, word_count) may be empty.
    Extra fields from an expanded CSV are silently allowed.
    """

    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    article_id:     str = Field(..., min_length=1, description="Unique article identifier")
    title:          str = Field(..., min_length=1, description="Article headline")
    company_name:   str = Field(..., min_length=1, description="Company the article is about")
    published_date: str = Field(..., min_length=1, description="Raw publication date string")
    category:       str = Field(..., min_length=1, description="Raw article category")
    summary:        str = Field(..., min_length=1, description="Article summary text")
    url:            str = Field(..., min_length=1, description="Source URL")

    # Optional in the CSV
    author:     str           = Field(default="", description="Article author (may be empty)")
    revenue:    Optional[str] = Field(default=None, description="Raw revenue string (may be empty)")
    word_count: Optional[str] = Field(default=None, description="Article word count (may be empty)")

    @field_validator("url")
    @classmethod
    def url_looks_valid(cls, v: str) -> str:
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError(f"URL does not start with http(s)://: '{v}'")
        return v

    @field_validator("article_id")
    @classmethod
    def article_id_format(cls, v: str) -> str:
        if not re.match(r"^[A-Z0-9_-]+$", v, re.IGNORECASE):
            raise ValueError(f"article_id contains unexpected characters: '{v}'")
        return v


# ---------------------------------------------------------------------------
# Stage 2 — Cleaned (post-clean)
# ---------------------------------------------------------------------------

class CleanedArticleSchema(BaseModel):
    """
    Schema for a row after the cleaning stage.

    Enforces:
    - revenue_usd  : integer, ≥ 0
    - category     : one of the 7 canonical values (incl. "Unknown")
    - published_date: ISO YYYY-MM-DD string (or empty if unparseable)
    - pub_year     : 1900–2100  (None allowed for unparseable dates)
    - pub_quarter  : 1–4        (None allowed)
    - pub_month    : 1–12       (None allowed)
    """

    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    article_id:     str = Field(..., min_length=1)
    company_name:   str = Field(..., min_length=1)
    published_date: str = Field(default="", description="ISO date or empty")
    category:       CANONICAL_CATEGORIES = Field(..., description="Canonical category")
    revenue_usd:    int  = Field(..., ge=0, description="Revenue in USD, must be ≥ 0")

    pub_year:    Optional[int] = Field(default=None, ge=1900, le=2100)
    pub_quarter: Optional[int] = Field(default=None, ge=1, le=4)
    pub_month:   Optional[int] = Field(default=None, ge=1, le=12)

    @field_validator("published_date")
    @classmethod
    def date_is_iso_or_empty(cls, v: str) -> str:
        if v and not _ISO_DATE_RE.match(v):
            raise ValueError(
                f"published_date must be ISO YYYY-MM-DD or empty, got: '{v}'"
            )
        return v

    @model_validator(mode="after")
    def date_parts_consistent(self) -> "CleanedArticleSchema":
        """If pub_year is set, quarter and month must also be set (and vice-versa)."""
        parts = (self.pub_year, self.pub_quarter, self.pub_month)
        none_count = sum(1 for p in parts if p is None)
        if none_count not in (0, 3):
            raise ValueError(
                "pub_year, pub_quarter, and pub_month must all be set or all be None; "
                f"got year={self.pub_year}, quarter={self.pub_quarter}, month={self.pub_month}"
            )
        return self


# ---------------------------------------------------------------------------
# Stage 3/4 — Enriched (post-enrich + filter)
# ---------------------------------------------------------------------------

class EnrichedArticleSchema(CleanedArticleSchema):
    """
    Schema for a row after metadata enrichment and filtering.

    Extends CleanedArticleSchema with all metadata and derived fields.
    """

    metadata_matched: bool = Field(..., description="True if company found in metadata")

    # Metadata fields — all optional (unmatched companies get None)
    meta_founded_year:   Optional[int]   = Field(default=None, ge=1800, le=2100)
    meta_headquarters:   Optional[str]   = Field(default=None)
    meta_employee_count: Optional[int]   = Field(default=None, ge=0)
    meta_industry:       Optional[str]   = Field(default=None)
    meta_is_public:      Optional[bool]  = Field(default=None)
    meta_stock_ticker:   Optional[str]   = Field(default=None)

    # Derived fields
    company_size_category: SIZE_CATEGORIES = Field(
        ..., description="Small / Medium / Large / Unknown"
    )
    company_age: Optional[int] = Field(
        default=None,
        ge=-10,    # allow minor data inconsistency (e.g. article just before founding)
        le=300,    # sanity ceiling
        description="Article pub_year minus company founding year",
    )

    @model_validator(mode="after")
    def matched_rows_have_metadata(self) -> "EnrichedArticleSchema":
        """Rows with metadata_matched=True must have non-None meta_founded_year."""
        if self.metadata_matched and self.meta_founded_year is None:
            raise ValueError(
                "metadata_matched=True but meta_founded_year is None — "
                "metadata join may be incomplete"
            )
        return self


# ---------------------------------------------------------------------------
# Structural column check (fast, pre-row-validation)
# ---------------------------------------------------------------------------

_REQUIRED_COLUMNS: dict[str, set[str]] = {
    "raw": {
        "article_id", "title", "company_name", "published_date",
        "category", "summary", "url", "author",
    },
    "clean": {
        "article_id", "company_name", "published_date", "category",
        "revenue_usd", "pub_year", "pub_quarter", "pub_month",
    },
    "enriched": {
        "article_id", "company_name", "category", "revenue_usd",
        "metadata_matched", "company_age", "company_size_category",
    },
}


def validate_columns(rows: list[dict], stage: str) -> None:
    """
    Raise a ``ValueError`` immediately if required columns are missing.

    This is a fast structural check run before per-row validation —
    if columns are missing the schema loop would generate 500 identical
    errors, so we short-circuit early.

    Parameters
    ----------
    rows : list[dict]
        Batch of rows to check (uses the first row's keys).
    stage : str
        One of ``"raw"``, ``"clean"``, ``"enriched"``.

    Raises
    ------
    ValueError
        If any required column is absent from the first row.
    """
    if not rows:
        return
    required = _REQUIRED_COLUMNS.get(stage, set())
    present  = set(rows[0].keys())
    missing  = required - present
    if missing:
        raise ValueError(
            f"[{stage}] Stage boundary column check FAILED — "
            f"missing columns: {sorted(missing)}"
        )
    logger.debug("[%s] Column check passed (%d required columns present)", stage, len(required))


# ---------------------------------------------------------------------------
# Row-level validation runner
# ---------------------------------------------------------------------------

def validate_stage(
    rows: list[dict],
    schema: Type[BaseModel],
    stage: str,
) -> tuple[list[dict], int]:
    """
    Validate every row against *schema*, log violations, return valid rows.

    Strategy
    --------
    - Structural column check first (fast fail).
    - Then per-row Pydantic validation.
    - Rows that fail validation are logged (WARNING) and excluded.
    - The pipeline continues with the valid subset — a bad row never
      silently corrupts downstream output.

    Parameters
    ----------
    rows : list[dict]
        Batch of rows to validate.
    schema : Type[BaseModel]
        Pydantic model class to validate against.
    stage : str
        Human-readable stage name used in log messages
        (``"raw"``, ``"clean"``, ``"enriched"``).

    Returns
    -------
    (valid_rows, error_count) : tuple[list[dict], int]
        *valid_rows* — rows that passed validation (original dicts, not models).
        *error_count* — number of rows that failed.
    """
    # 1. Structural check
    validate_columns(rows, stage)

    valid_rows: list[dict] = []
    error_count = 0

    for row in rows:
        try:
            schema.model_validate(row)
            valid_rows.append(row)
        except ValidationError as exc:
            error_count += 1
            article_id = row.get("article_id", "<unknown>")
            for err in exc.errors():
                field = " → ".join(str(loc) for loc in err["loc"]) or "<root>"
                logger.warning(
                    "[%s] Validation error | article_id=%s | field=%s | %s",
                    stage,
                    article_id,
                    field,
                    err["msg"],
                )

    if error_count:
        logger.warning(
            "[%s] %d/%d rows failed validation and were excluded",
            stage, error_count, len(rows),
        )
    else:
        logger.info(
            "[%s] All %d rows passed schema validation ✓",
            stage, len(rows),
        )

    return valid_rows, error_count
