"""
tests/test_categories.py — Unit tests for cleaning/categories.py.
"""

import pytest

from cleaning.categories import CANONICAL_CATEGORIES, standardize_category


def test_standardize_category_canonical():
    # Test valid mapped inputs for each canonical category
    assert standardize_category("ai/ml") == "AI_ML"
    assert standardize_category("artificial intelligence") == "AI_ML"
    
    assert standardize_category("data analytics") == "Data_Analytics"
    assert standardize_category("big data") == "Data_Analytics"
    
    assert standardize_category("cloud computing") == "Cloud_Computing"
    assert standardize_category("cloud services") == "Cloud_Computing"
    
    assert standardize_category("cybersecurity") == "Cybersecurity"
    assert standardize_category("infosec") == "Cybersecurity"
    
    assert standardize_category("fintech") == "FinTech"
    assert standardize_category("finance") == "FinTech"
    
    assert standardize_category("saas") == "SaaS_Software"
    assert standardize_category("software") == "SaaS_Software"


def test_standardize_category_case_insensitivity():
    # Test case variations
    assert standardize_category("Artificial Intelligence") == "AI_ML"
    assert standardize_category("Big Data") == "Data_Analytics"
    assert standardize_category("CLOUD SERVICES") == "Cloud_Computing"
    assert standardize_category("InfoSec") == "Cybersecurity"
    assert standardize_category("FinTech") == "FinTech"
    assert standardize_category("SaaS") == "SaaS_Software"


def test_standardize_category_whitespace():
    # Test leading/trailing whitespaces
    assert standardize_category("   ai/ml   ") == "AI_ML"
    assert standardize_category("\tbig data\n") == "Data_Analytics"
    assert standardize_category("  saas  ") == "SaaS_Software"


def test_standardize_category_none_and_empty():
    # Test None and empty values
    assert standardize_category(None) == "Unknown"
    assert standardize_category("") == "Unknown"
    assert standardize_category("   ") == "Unknown"


def test_standardize_category_unknown():
    # Test unmapped categories
    assert standardize_category("hardware") == "Unknown"
    assert standardize_category("social media") == "Unknown"
    assert standardize_category("agtech") == "Unknown"


def test_standardize_category_non_strings():
    # Test non-string input objects
    assert standardize_category(123) == "Unknown"
    assert standardize_category(True) == "Unknown"
