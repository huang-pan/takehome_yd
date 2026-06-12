"""
categories.py — Category taxonomy standardization.

Maps the 19 messy raw category strings found in tech_news.csv to a
consistent set of 6 canonical categories.
"""

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Canonical taxonomy
# ---------------------------------------------------------------------------
CANONICAL_CATEGORIES = {
    "AI_ML",
    "Data_Analytics",
    "Cloud_Computing",
    "Cybersecurity",
    "FinTech",
    "SaaS_Software",
}

# Raw value → canonical (case-insensitive lookup is applied before this map)
CATEGORY_MAP: dict[str, str] = {
    # AI / Machine Learning
    "ai/ml":                   "AI_ML",
    "ai & ml":                 "AI_ML",
    "ai&ml":                   "AI_ML",
    "artificial intelligence": "AI_ML",
    "machine learning":        "AI_ML",
    # Data / Analytics
    "analytics":               "Data_Analytics",
    "data analytics":          "Data_Analytics",
    "big data":                "Data_Analytics",
    # Cloud
    "cloud":                   "Cloud_Computing",
    "cloud computing":         "Cloud_Computing",
    "cloud services":          "Cloud_Computing",
    # Security
    "cybersecurity":           "Cybersecurity",
    "security":                "Cybersecurity",
    "infosec":                 "Cybersecurity",
    # FinTech / Finance
    "fintech":                 "FinTech",
    "finance":                 "FinTech",
    "financial technology":    "FinTech",
    # SaaS / Software
    "saas":                    "SaaS_Software",
    "enterprise software":     "SaaS_Software",
    "software":                "SaaS_Software",
}


def standardize_category(raw: object) -> str:
    """
    Map a raw category string to a canonical category name.

    Parameters
    ----------
    raw : object
        Raw category value from the CSV.

    Returns
    -------
    str
        Canonical category name from CANONICAL_CATEGORIES,
        or "Unknown" if no mapping is found.

    Examples
    --------
    >>> standardize_category("Artificial Intelligence")
    'AI_ML'
    >>> standardize_category("Big Data")
    'Data_Analytics'
    >>> standardize_category("Cloud Services")
    'Cloud_Computing'
    >>> standardize_category("InfoSec")
    'Cybersecurity'
    """
    if raw is None:
        return "Unknown"
    key = str(raw).strip().lower()
    canonical = CATEGORY_MAP.get(key)
    if canonical is None:
        logger.warning("Unmapped category: '%s'", raw)
        return "Unknown"
    return canonical
