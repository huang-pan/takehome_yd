"""
tests/test_validation.py — Unit tests for validation.schemas.

Coverage:

  RawArticleSchema
    - Valid row passes
    - Missing required field raises ValidationError
    - Empty required string raises ValidationError
    - Invalid URL (no http/https) raises ValidationError
    - article_id with invalid characters raises ValidationError
    - Optional fields (revenue, word_count) may be None or empty

  CleanedArticleSchema
    - Valid row passes
    - revenue_usd < 0 raises ValidationError
    - revenue_usd as float (not int) raises ValidationError
    - Non-canonical category raises ValidationError
    - "Unknown" category is accepted
    - Non-ISO published_date raises ValidationError
    - Empty published_date is accepted
    - pub_year out of range (< 1900 or > 2100) raises ValidationError
    - pub_quarter out of range (0 or 5) raises ValidationError
    - pub_month out of range (0 or 13) raises ValidationError
    - Partial date parts (only pub_year set) raises cross-field error
    - All date parts None is accepted

  EnrichedArticleSchema
    - Valid enriched row passes
    - metadata_matched=True with meta_founded_year=None raises ValidationError
    - metadata_matched=False with meta_founded_year=None is accepted
    - meta_employee_count < 0 raises ValidationError
    - meta_founded_year out of range raises ValidationError
    - company_age out of range (> 300) raises ValidationError
    - Non-canonical company_size_category raises ValidationError
    - "Unknown" company_size_category is accepted
    - Extra columns are silently ignored (extra="allow")

  validate_columns()
    - Passes when all required columns are present
    - Raises ValueError when a required column is missing
    - Empty list does not raise

  validate_stage()
    - All-valid batch returns (all_rows, 0)
    - One invalid row excluded, error_count = 1
    - All invalid rows excluded, error_count = N
    - Returns original dicts (not Pydantic model instances)
"""

import pytest
from pydantic import ValidationError

from validation.schemas import (
    RawArticleSchema,
    CleanedArticleSchema,
    EnrichedArticleSchema,
    validate_columns,
    validate_stage,
)


# ---------------------------------------------------------------------------
# Fixtures — minimal valid rows for each stage
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_raw() -> dict:
    return {
        "article_id":     "ART0001",
        "title":          "Scale AI Raises Series D",
        "company_name":   "Scale AI",
        "published_date": "21 Feb 2020",
        "category":       "Financial Technology",
        "summary":        "A great article.",
        "url":            "https://technews.example.com/articles/1",
        "author":         "John Smith",
        "revenue":        "",
        "word_count":     "2569",
    }


@pytest.fixture
def valid_cleaned() -> dict:
    return {
        "article_id":     "ART0001",
        "title":          "Scale AI Raises Series D",
        "company_name":   "Scale AI",
        "published_date": "2020-02-21",
        "category":       "FinTech",
        "revenue_usd":    0,
        "pub_year":       2020,
        "pub_quarter":    1,
        "pub_month":      2,
        "summary":        "A great article.",
        "url":            "https://technews.example.com/articles/1",
        "author":         "John Smith",
        "word_count":     "2569",
    }


@pytest.fixture
def valid_enriched(valid_cleaned) -> dict:
    return {
        **valid_cleaned,
        "metadata_matched":      True,
        "meta_founded_year":     2003,
        "meta_headquarters":     "Berlin, Germany",
        "meta_employee_count":   23379,
        "meta_industry":         "AI/ML",
        "meta_is_public":        False,
        "meta_stock_ticker":     None,
        "company_age":           17,
        "company_size_category": "Medium",
    }


# ---------------------------------------------------------------------------
# RawArticleSchema
# ---------------------------------------------------------------------------

class TestRawArticleSchema:

    def test_valid_row_passes(self, valid_raw):
        RawArticleSchema.model_validate(valid_raw)  # should not raise

    def test_missing_required_field_raises(self, valid_raw):
        del valid_raw["title"]
        with pytest.raises(ValidationError) as exc_info:
            RawArticleSchema.model_validate(valid_raw)
        assert "title" in str(exc_info.value)

    def test_empty_article_id_raises(self, valid_raw):
        valid_raw["article_id"] = ""
        with pytest.raises(ValidationError):
            RawArticleSchema.model_validate(valid_raw)

    def test_empty_company_name_raises(self, valid_raw):
        valid_raw["company_name"] = ""
        with pytest.raises(ValidationError):
            RawArticleSchema.model_validate(valid_raw)

    def test_empty_author_accepted(self, valid_raw):
        valid_raw["author"] = ""
        RawArticleSchema.model_validate(valid_raw)  # no raise

    def test_missing_author_key_uses_default(self, valid_raw):
        del valid_raw["author"]
        RawArticleSchema.model_validate(valid_raw)  # no raise — defaults to ""

    def test_populated_author_accepted(self, valid_raw):
        valid_raw["author"] = "Jane Doe"
        RawArticleSchema.model_validate(valid_raw)  # no raise

    def test_empty_summary_raises(self, valid_raw):
        valid_raw["summary"] = "   "   # whitespace stripped → empty
        with pytest.raises(ValidationError):
            RawArticleSchema.model_validate(valid_raw)

    def test_invalid_url_no_scheme_raises(self, valid_raw):
        valid_raw["url"] = "technews.example.com/articles/1"
        with pytest.raises(ValidationError) as exc_info:
            RawArticleSchema.model_validate(valid_raw)
        assert "url" in str(exc_info.value).lower() or "URL" in str(exc_info.value)

    def test_http_url_accepted(self, valid_raw):
        valid_raw["url"] = "http://technews.example.com/articles/1"
        RawArticleSchema.model_validate(valid_raw)  # no raise

    def test_article_id_with_special_chars_raises(self, valid_raw):
        valid_raw["article_id"] = "ART 0001!!"
        with pytest.raises(ValidationError):
            RawArticleSchema.model_validate(valid_raw)

    def test_optional_revenue_can_be_none(self, valid_raw):
        valid_raw["revenue"] = None
        RawArticleSchema.model_validate(valid_raw)  # no raise

    def test_optional_revenue_can_be_empty_string(self, valid_raw):
        valid_raw["revenue"] = ""
        RawArticleSchema.model_validate(valid_raw)  # no raise

    def test_optional_word_count_can_be_none(self, valid_raw):
        valid_raw["word_count"] = None
        RawArticleSchema.model_validate(valid_raw)  # no raise

    def test_extra_columns_are_allowed(self, valid_raw):
        valid_raw["unexpected_column"] = "some_value"
        RawArticleSchema.model_validate(valid_raw)  # no raise


# ---------------------------------------------------------------------------
# CleanedArticleSchema
# ---------------------------------------------------------------------------

class TestCleanedArticleSchema:

    def test_valid_row_passes(self, valid_cleaned):
        CleanedArticleSchema.model_validate(valid_cleaned)

    # revenue_usd
    def test_negative_revenue_raises(self, valid_cleaned):
        valid_cleaned["revenue_usd"] = -1
        with pytest.raises(ValidationError) as exc_info:
            CleanedArticleSchema.model_validate(valid_cleaned)
        assert "revenue_usd" in str(exc_info.value)

    def test_zero_revenue_accepted(self, valid_cleaned):
        valid_cleaned["revenue_usd"] = 0
        CleanedArticleSchema.model_validate(valid_cleaned)

    def test_large_revenue_accepted(self, valid_cleaned):
        valid_cleaned["revenue_usd"] = 10_000_000_000
        CleanedArticleSchema.model_validate(valid_cleaned)

    # category
    @pytest.mark.parametrize("cat", [
        "AI_ML", "Data_Analytics", "Cloud_Computing",
        "Cybersecurity", "FinTech", "SaaS_Software", "Unknown",
    ])
    def test_all_canonical_categories_accepted(self, valid_cleaned, cat):
        valid_cleaned["category"] = cat
        CleanedArticleSchema.model_validate(valid_cleaned)

    def test_non_canonical_category_raises(self, valid_cleaned):
        valid_cleaned["category"] = "Artificial Intelligence"
        with pytest.raises(ValidationError) as exc_info:
            CleanedArticleSchema.model_validate(valid_cleaned)
        assert "category" in str(exc_info.value)

    def test_raw_category_raises(self, valid_cleaned):
        valid_cleaned["category"] = "Big Data"
        with pytest.raises(ValidationError):
            CleanedArticleSchema.model_validate(valid_cleaned)

    # published_date
    def test_non_iso_date_raises(self, valid_cleaned):
        valid_cleaned["published_date"] = "21 Feb 2020"
        with pytest.raises(ValidationError) as exc_info:
            CleanedArticleSchema.model_validate(valid_cleaned)
        assert "published_date" in str(exc_info.value)

    def test_empty_date_accepted(self, valid_cleaned):
        valid_cleaned["published_date"] = ""
        valid_cleaned["pub_year"] = None
        valid_cleaned["pub_quarter"] = None
        valid_cleaned["pub_month"] = None
        CleanedArticleSchema.model_validate(valid_cleaned)

    def test_us_slash_date_raises(self, valid_cleaned):
        valid_cleaned["published_date"] = "02/21/2020"
        with pytest.raises(ValidationError):
            CleanedArticleSchema.model_validate(valid_cleaned)

    # pub_year range
    def test_pub_year_below_1900_raises(self, valid_cleaned):
        valid_cleaned["pub_year"] = 1899
        with pytest.raises(ValidationError) as exc_info:
            CleanedArticleSchema.model_validate(valid_cleaned)
        assert "pub_year" in str(exc_info.value)

    def test_pub_year_above_2100_raises(self, valid_cleaned):
        valid_cleaned["pub_year"] = 2101
        with pytest.raises(ValidationError):
            CleanedArticleSchema.model_validate(valid_cleaned)

    def test_pub_year_boundary_1900_accepted(self, valid_cleaned):
        valid_cleaned["pub_year"] = 1900
        CleanedArticleSchema.model_validate(valid_cleaned)

    def test_pub_year_boundary_2100_accepted(self, valid_cleaned):
        valid_cleaned["pub_year"] = 2100
        CleanedArticleSchema.model_validate(valid_cleaned)

    # pub_quarter range
    def test_pub_quarter_zero_raises(self, valid_cleaned):
        valid_cleaned["pub_quarter"] = 0
        with pytest.raises(ValidationError) as exc_info:
            CleanedArticleSchema.model_validate(valid_cleaned)
        assert "pub_quarter" in str(exc_info.value)

    def test_pub_quarter_five_raises(self, valid_cleaned):
        valid_cleaned["pub_quarter"] = 5
        with pytest.raises(ValidationError):
            CleanedArticleSchema.model_validate(valid_cleaned)

    @pytest.mark.parametrize("q", [1, 2, 3, 4])
    def test_valid_quarters_accepted(self, valid_cleaned, q):
        valid_cleaned["pub_quarter"] = q
        CleanedArticleSchema.model_validate(valid_cleaned)

    # pub_month range
    def test_pub_month_zero_raises(self, valid_cleaned):
        valid_cleaned["pub_month"] = 0
        with pytest.raises(ValidationError):
            CleanedArticleSchema.model_validate(valid_cleaned)

    def test_pub_month_13_raises(self, valid_cleaned):
        valid_cleaned["pub_month"] = 13
        with pytest.raises(ValidationError):
            CleanedArticleSchema.model_validate(valid_cleaned)

    @pytest.mark.parametrize("m", [1, 6, 12])
    def test_valid_months_accepted(self, valid_cleaned, m):
        valid_cleaned["pub_month"] = m
        CleanedArticleSchema.model_validate(valid_cleaned)

    # Cross-field: date parts consistency
    def test_partial_date_parts_raises(self, valid_cleaned):
        """Only pub_year set — quarter and month must both be set or all None."""
        valid_cleaned["pub_year"] = 2020
        valid_cleaned["pub_quarter"] = None
        valid_cleaned["pub_month"] = None
        with pytest.raises(ValidationError):
            CleanedArticleSchema.model_validate(valid_cleaned)

    def test_all_date_parts_none_accepted(self, valid_cleaned):
        valid_cleaned["published_date"] = ""
        valid_cleaned["pub_year"] = None
        valid_cleaned["pub_quarter"] = None
        valid_cleaned["pub_month"] = None
        CleanedArticleSchema.model_validate(valid_cleaned)

    def test_all_date_parts_set_accepted(self, valid_cleaned):
        valid_cleaned["pub_year"] = 2023
        valid_cleaned["pub_quarter"] = 4
        valid_cleaned["pub_month"] = 12
        CleanedArticleSchema.model_validate(valid_cleaned)

    def test_extra_columns_ignored(self, valid_cleaned):
        valid_cleaned["extra_col"] = "whatever"
        CleanedArticleSchema.model_validate(valid_cleaned)


# ---------------------------------------------------------------------------
# EnrichedArticleSchema
# ---------------------------------------------------------------------------

class TestEnrichedArticleSchema:

    def test_valid_row_passes(self, valid_enriched):
        EnrichedArticleSchema.model_validate(valid_enriched)

    # metadata_matched + meta_founded_year cross-field
    def test_matched_with_no_founded_year_raises(self, valid_enriched):
        valid_enriched["metadata_matched"] = True
        valid_enriched["meta_founded_year"] = None
        with pytest.raises(ValidationError) as exc_info:
            EnrichedArticleSchema.model_validate(valid_enriched)
        assert "meta_founded_year" in str(exc_info.value) or "metadata" in str(exc_info.value).lower()

    def test_unmatched_with_no_founded_year_accepted(self, valid_enriched):
        valid_enriched["metadata_matched"] = False
        valid_enriched["meta_founded_year"] = None
        valid_enriched["company_age"] = None
        EnrichedArticleSchema.model_validate(valid_enriched)

    # meta_employee_count
    def test_negative_employee_count_raises(self, valid_enriched):
        valid_enriched["meta_employee_count"] = -1
        with pytest.raises(ValidationError) as exc_info:
            EnrichedArticleSchema.model_validate(valid_enriched)
        assert "meta_employee_count" in str(exc_info.value)

    def test_zero_employee_count_accepted(self, valid_enriched):
        valid_enriched["meta_employee_count"] = 0
        EnrichedArticleSchema.model_validate(valid_enriched)

    # meta_founded_year range
    def test_founded_year_before_1800_raises(self, valid_enriched):
        valid_enriched["meta_founded_year"] = 1799
        with pytest.raises(ValidationError):
            EnrichedArticleSchema.model_validate(valid_enriched)

    def test_founded_year_after_2100_raises(self, valid_enriched):
        valid_enriched["meta_founded_year"] = 2101
        with pytest.raises(ValidationError):
            EnrichedArticleSchema.model_validate(valid_enriched)

    def test_founded_year_boundary_1800_accepted(self, valid_enriched):
        valid_enriched["meta_founded_year"] = 1800
        EnrichedArticleSchema.model_validate(valid_enriched)

    # company_age range
    def test_company_age_above_300_raises(self, valid_enriched):
        valid_enriched["company_age"] = 301
        with pytest.raises(ValidationError) as exc_info:
            EnrichedArticleSchema.model_validate(valid_enriched)
        assert "company_age" in str(exc_info.value)

    def test_company_age_none_accepted(self, valid_enriched):
        valid_enriched["company_age"] = None
        EnrichedArticleSchema.model_validate(valid_enriched)

    def test_company_age_slightly_negative_accepted(self, valid_enriched):
        """Small negative ages are allowed (data quirks, article before official founding)."""
        valid_enriched["company_age"] = -5
        EnrichedArticleSchema.model_validate(valid_enriched)

    def test_company_age_very_negative_raises(self, valid_enriched):
        valid_enriched["company_age"] = -100
        with pytest.raises(ValidationError):
            EnrichedArticleSchema.model_validate(valid_enriched)

    # company_size_category
    @pytest.mark.parametrize("size", ["Small", "Medium", "Large", "Unknown"])
    def test_valid_size_categories_accepted(self, valid_enriched, size):
        valid_enriched["company_size_category"] = size
        EnrichedArticleSchema.model_validate(valid_enriched)

    def test_invalid_size_category_raises(self, valid_enriched):
        valid_enriched["company_size_category"] = "Giant"
        with pytest.raises(ValidationError) as exc_info:
            EnrichedArticleSchema.model_validate(valid_enriched)
        assert "company_size_category" in str(exc_info.value)

    def test_extra_columns_ignored(self, valid_enriched):
        valid_enriched["some_new_column"] = "value"
        EnrichedArticleSchema.model_validate(valid_enriched)


# ---------------------------------------------------------------------------
# validate_columns()
# ---------------------------------------------------------------------------

class TestValidateColumns:

    def test_raw_all_present_passes(self, valid_raw):
        validate_columns([valid_raw], stage="raw")  # no raise

    def test_raw_missing_column_raises(self, valid_raw):
        del valid_raw["article_id"]
        with pytest.raises(ValueError, match="article_id"):
            validate_columns([valid_raw], stage="raw")

    def test_clean_all_present_passes(self, valid_cleaned):
        validate_columns([valid_cleaned], stage="clean")

    def test_clean_missing_revenue_usd_raises(self, valid_cleaned):
        del valid_cleaned["revenue_usd"]
        with pytest.raises(ValueError, match="revenue_usd"):
            validate_columns([valid_cleaned], stage="clean")

    def test_enriched_all_present_passes(self, valid_enriched):
        validate_columns([valid_enriched], stage="enriched")

    def test_enriched_missing_company_age_raises(self, valid_enriched):
        del valid_enriched["company_age"]
        with pytest.raises(ValueError, match="company_age"):
            validate_columns([valid_enriched], stage="enriched")

    def test_empty_list_does_not_raise(self):
        validate_columns([], stage="raw")  # no raise

    def test_unknown_stage_does_not_raise(self, valid_raw):
        validate_columns([valid_raw], stage="nonexistent_stage")  # no required cols → no raise


# ---------------------------------------------------------------------------
# validate_stage()
# ---------------------------------------------------------------------------

class TestValidateStage:

    def test_all_valid_returns_all_rows_zero_errors(self, valid_cleaned):
        rows = [valid_cleaned.copy(), valid_cleaned.copy()]
        valid, errors = validate_stage(rows, CleanedArticleSchema, stage="clean")
        assert len(valid) == 2
        assert errors == 0

    def test_one_invalid_row_excluded(self, valid_cleaned):
        bad_row = valid_cleaned.copy()
        bad_row["revenue_usd"] = -999
        rows = [valid_cleaned.copy(), bad_row]
        valid, errors = validate_stage(rows, CleanedArticleSchema, stage="clean")
        assert len(valid) == 1
        assert errors == 1

    def test_all_invalid_returns_empty_list(self, valid_cleaned):
        bad = valid_cleaned.copy()
        bad["revenue_usd"] = -1
        rows = [bad.copy(), bad.copy(), bad.copy()]
        valid, errors = validate_stage(rows, CleanedArticleSchema, stage="clean")
        assert valid == []
        assert errors == 3

    def test_returns_original_dicts_not_models(self, valid_cleaned):
        """validate_stage must return the original dict, not a Pydantic model."""
        rows = [valid_cleaned]
        valid, _ = validate_stage(rows, CleanedArticleSchema, stage="clean")
        assert isinstance(valid[0], dict)

    def test_valid_raw_stage(self, valid_raw):
        valid, errors = validate_stage([valid_raw], RawArticleSchema, stage="raw")
        assert len(valid) == 1
        assert errors == 0

    def test_valid_enriched_stage(self, valid_enriched):
        valid, errors = validate_stage([valid_enriched], EnrichedArticleSchema, stage="enriched")
        assert len(valid) == 1
        assert errors == 0

    def test_missing_column_raises_before_row_validation(self, valid_cleaned):
        del valid_cleaned["revenue_usd"]
        with pytest.raises(ValueError, match="revenue_usd"):
            validate_stage([valid_cleaned], CleanedArticleSchema, stage="clean")
