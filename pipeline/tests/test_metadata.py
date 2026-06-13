"""
tests/test_metadata.py — Unit tests for enrichment/metadata.py.
"""

import json
from pathlib import Path
import pytest

from config.loader import FilterConfig
from enrichment.metadata import (
    _resolve_company,
    _size_category,
    enrich_with_metadata,
    filter_ai_relevant,
    load_metadata,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_metadata():
    return {
        "Scale AI": {
            "founded_year": 2016,
            "headquarters": "San Francisco, CA",
            "employee_count": 800,
            "industry": "AI/ML",
            "is_public": False,
            "stock_ticker": None,
        },
        "DataRobot": {
            "founded_year": 2012,
            "headquarters": "Boston, MA",
            "employee_count": 12000,
            "industry": "Cloud Computing",
            "is_public": False,
            "stock_ticker": None,
        },
        "NVIDIA": {
            "founded_year": 1993,
            "headquarters": "Santa Clara, CA",
            "employee_count": 29600,
            "industry": "AI/ML",
            "is_public": True,
            "stock_ticker": "NVDA",
        },
        "Microsoft": {
            "founded_year": 1975,
            "headquarters": "Redmond, WA",
            "employee_count": 221000,
            "industry": "Software",
            "is_public": True,
            "stock_ticker": "MSFT",
        }
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_size_category():
    assert _size_category(None) == "Unknown"
    assert _size_category(500) == "Small"
    assert _size_category(9999) == "Small"
    assert _size_category(10000) == "Medium"
    assert _size_category(15000) == "Medium"
    assert _size_category(30000) == "Medium"
    assert _size_category(30001) == "Large"
    assert _size_category(250000) == "Large"


def test_load_metadata(tmp_path, mock_metadata):
    meta_path = tmp_path / "company_metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(mock_metadata, f)
        
    loaded = load_metadata(meta_path)
    assert len(loaded) == 4
    assert loaded["NVIDIA"]["stock_ticker"] == "NVDA"


def test_resolve_company(mock_metadata):
    # 1. Exact match
    assert _resolve_company("NVIDIA", mock_metadata) == "NVIDIA"
    
    # 2. Case-insensitive exact match
    assert _resolve_company("nvidia", mock_metadata) == "NVIDIA"
    assert _resolve_company("sCaLe Ai", mock_metadata) == "Scale AI"
    
    # 3. Fuzzy match via difflib
    assert _resolve_company("ScaleAI", mock_metadata) == "Scale AI"
    assert _resolve_company("Data Robot Inc.", mock_metadata, cutoff=0.6) == "DataRobot"
    
    # 4. No match found
    assert _resolve_company("Unknown Company LLC", mock_metadata) is None


def test_enrich_with_metadata(mock_metadata):
    articles = [
        # Match Scale AI (exact)
        {
            "article_id": "ART001",
            "company_name": "Scale AI",
            "pub_year": 2020,
            "category": "FinTech",
        },
        # Match nvidia (case-insensitive)
        {
            "article_id": "ART002",
            "company_name": "nvidia",
            "pub_year": 2023,
            "category": "AI_ML",
        },
        # No match
        {
            "article_id": "ART003",
            "company_name": "Nonexistent Corp",
            "pub_year": 2022,
            "category": "SaaS_Software",
        },
        # Missing company_name
        {
            "article_id": "ART004",
            "pub_year": 2021,
            "category": "Cloud_Computing",
        }
    ]
    
    enriched = enrich_with_metadata(articles, mock_metadata)
    
    assert len(enriched) == 4
    
    # Check Scale AI enrichment
    row0 = enriched[0]
    assert row0["metadata_matched"] is True
    assert row0["meta_founded_year"] == 2016
    assert row0["meta_employee_count"] == 800
    assert row0["company_age"] == 4  # 2020 - 2016
    assert row0["company_size_category"] == "Small"
    
    # Check case-insensitive enrichment
    row1 = enriched[1]
    assert row1["metadata_matched"] is True
    assert row1["meta_stock_ticker"] == "NVDA"
    assert row1["company_age"] == 30  # 2023 - 1993
    assert row1["company_size_category"] == "Medium"
    
    # Check no-match enrichment
    row2 = enriched[2]
    assert row2["metadata_matched"] is False
    assert row2["meta_founded_year"] is None
    assert row2["company_age"] is None
    assert row2["company_size_category"] == "Unknown"
    
    # Check missing company_name enrichment
    row3 = enriched[3]
    assert row3["metadata_matched"] is False
    assert row3["company_age"] is None
    assert row3["company_size_category"] == "Unknown"


def test_company_age_calculation():
    # 1. Normal calculation (integer years)
    articles = [{"company_name": "Scale AI", "pub_year": 2023}]
    metadata = {"Scale AI": {"founded_year": 2016}}
    enriched = enrich_with_metadata(articles, metadata)
    assert enriched[0]["company_age"] == 7
    
    # 2. String year parsing (should handle string representations)
    articles_str = [{"company_name": "Scale AI", "pub_year": "2023"}]
    metadata_str = {"Scale AI": {"founded_year": "2016"}}
    enriched_str = enrich_with_metadata(articles_str, metadata_str)
    assert enriched_str[0]["company_age"] == 7
    
    # 3. Missing publication year -> None age
    articles_missing_pub = [{"company_name": "Scale AI"}]
    enriched_missing_pub = enrich_with_metadata(articles_missing_pub, metadata)
    assert enriched_missing_pub[0]["company_age"] is None
    
    # 4. Missing founding year -> None age
    articles_missing_found = [{"company_name": "Scale AI", "pub_year": 2023}]
    metadata_missing_found = {"Scale AI": {"founded_year": None}}
    enriched_missing_found = enrich_with_metadata(articles_missing_found, metadata_missing_found)
    assert enriched_missing_found[0]["company_age"] is None
    
    # 5. Negative age (if founding year > pub_year)
    articles_neg = [{"company_name": "Scale AI", "pub_year": 2010}]
    enriched_neg = enrich_with_metadata(articles_neg, metadata)
    assert enriched_neg[0]["company_age"] == -6


def test_company_size_category_enrichment():
    metadata = {
        "SmallCorp": {"employee_count": 5000},
        "MediumCorp": {"employee_count": 20000},
        "LargeCorp": {"employee_count": 50000},
        "UnknownCorp": {"employee_count": None},
    }
    
    articles = [
        {"company_name": "SmallCorp"},
        {"company_name": "MediumCorp"},
        {"company_name": "LargeCorp"},
        {"company_name": "UnknownCorp"},
    ]
    
    enriched = enrich_with_metadata(articles, metadata)
    
    assert enriched[0]["company_size_category"] == "Small"
    assert enriched[1]["company_size_category"] == "Medium"
    assert enriched[2]["company_size_category"] == "Large"
    assert enriched[3]["company_size_category"] == "Unknown"


def test_filter_ai_relevant():
    filter_config = FilterConfig(
        ai_relevant_categories=frozenset(["AI_ML", "Data_Analytics"]),
        ai_relevant_industries=frozenset(["AI/ML", "Data Analytics"]),
    )
    
    articles = [
        # AI relevance by category only
        {"article_id": "ART1", "category": "AI_ML", "meta_industry": "Finance"},
        # AI relevance by industry only
        {"article_id": "ART2", "category": "SaaS_Software", "meta_industry": "AI/ML"},
        # AI relevance by both
        {"article_id": "ART3", "category": "Data_Analytics", "meta_industry": "Data Analytics"},
        # Not relevant
        {"article_id": "ART4", "category": "FinTech", "meta_industry": "Cloud Computing"},
        # Missing values
        {"article_id": "ART5"},
    ]
    
    filtered = filter_ai_relevant(articles, filter_config)
    
    assert len(filtered) == 3
    retained_ids = [row["article_id"] for row in filtered]
    assert "ART1" in retained_ids
    assert "ART2" in retained_ids
    assert "ART3" in retained_ids
    assert "ART4" not in retained_ids
    assert "ART5" not in retained_ids
