"""
metadata.py — Company metadata enrichment, validation, and derived field computation.

Responsibilities:
  1. Load company_metadata.json
  2. Validate article company names against metadata (exact → fuzzy fallback)
  3. Join metadata fields onto each article record
  4. Derive:
       - company_age         : pub_year - founded_year
       - company_size_category: Small / Medium / Large by employee_count
  5. Filter to AI/ML-relevant articles (category OR industry)
"""

import json
import logging
from difflib import get_close_matches
from pathlib import Path
from typing import Optional

from config.loader import FilterConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Size thresholds (employees)
# ---------------------------------------------------------------------------
SIZE_SMALL_MAX  = 10_000
SIZE_MEDIUM_MAX = 30_000  # >30K → Large


def _size_category(employee_count: Optional[int]) -> str:
    """Classify a company by headcount into Small / Medium / Large."""
    if employee_count is None:
        return "Unknown"
    if employee_count < SIZE_SMALL_MAX:
        return "Small"
    if employee_count <= SIZE_MEDIUM_MAX:
        return "Medium"
    return "Large"


def load_metadata(path: Path) -> dict[str, dict]:
    """
    Load and return the company metadata dictionary.

    Parameters
    ----------
    path : Path
        Absolute path to ``company_metadata.json``.

    Returns
    -------
    dict
        Mapping of company_name → metadata dict.
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    logger.info("Loaded metadata for %d companies", len(data))
    return data


def _resolve_company(
    name: str,
    metadata: dict[str, dict],
    cutoff: float = 0.75,
) -> Optional[str]:
    """
    Resolve a raw company name to a metadata key.

    Strategy
    --------
    1. Exact match.
    2. Case-insensitive exact match.
    3. Fuzzy match via :func:`difflib.get_close_matches` (similarity ≥ *cutoff*).

    Parameters
    ----------
    name : str
        Company name from the article.
    metadata : dict
        Loaded metadata dictionary.
    cutoff : float
        Minimum similarity ratio for fuzzy matching (0–1).

    Returns
    -------
    str or None
        Matched metadata key, or ``None`` if no match found.
    """
    # 1. Exact
    if name in metadata:
        return name

    # 2. Case-insensitive
    lower_map = {k.lower(): k for k in metadata}
    if name.lower() in lower_map:
        return lower_map[name.lower()]

    # 3. Fuzzy
    candidates = get_close_matches(name, metadata.keys(), n=1, cutoff=cutoff)
    if candidates:
        match = candidates[0]
        logger.info(
            "Fuzzy match: '%s' → '%s' (difflib)", name, match
        )
        return match

    logger.warning("No metadata match for company: '%s'", name)
    return None


def enrich_with_metadata(
    articles: list[dict],
    metadata: dict[str, dict],
) -> list[dict]:
    """
    Join metadata onto article records and compute derived fields.

    For each article:
    - Resolves ``company_name`` to a metadata key (exact/fuzzy)
    - Adds all metadata fields (prefixed with ``meta_`` where ambiguous)
    - Adds ``company_age``, ``company_size_category``
    - Adds ``metadata_matched`` (bool flag)

    Parameters
    ----------
    articles : list[dict]
        Cleaned article records (output of the cleaning stage).
    metadata : dict[str, dict]
        Company metadata loaded by :func:`load_metadata`.

    Returns
    -------
    list[dict]
        Enriched article records (all rows, including unmatched).
    """
    enriched = []
    matched = unmatched = 0

    for row in articles:
        company = row.get("company_name", "")
        key = _resolve_company(company, metadata)

        if key:
            meta = metadata[key]
            matched += 1
        else:
            meta = {}
            unmatched += 1

        # --- Flatten metadata fields ---
        row["metadata_matched"]      = key is not None
        row["meta_founded_year"]     = meta.get("founded_year")
        row["meta_headquarters"]     = meta.get("headquarters")
        row["meta_employee_count"]   = meta.get("employee_count")
        row["meta_industry"]         = meta.get("industry")
        row["meta_is_public"]        = meta.get("is_public")
        row["meta_stock_ticker"]     = meta.get("stock_ticker")

        # --- Derived: company_age ---
        pub_year = row.get("pub_year")
        founded  = meta.get("founded_year")
        if pub_year is not None and founded is not None:
            row["company_age"] = int(pub_year) - int(founded)
        else:
            row["company_age"] = None

        # --- Derived: company_size_category ---
        row["company_size_category"] = _size_category(meta.get("employee_count"))

        enriched.append(row)

    logger.info(
        "Metadata join complete: %d matched, %d unmatched", matched, unmatched
    )
    return enriched


def filter_ai_relevant(
    articles: list[dict],
    filter_config: FilterConfig,
) -> list[dict]:
    """
    Filter enriched articles to rows matching the configured relevance sets.

    An article is kept when its ``category`` OR the company's
    ``meta_industry`` appears in the sets defined by *filter_config*,
    which is loaded from ``config/filter_config.yaml``.

    Parameters
    ----------
    articles : list[dict]
        Enriched article records.
    filter_config : FilterConfig
        Loaded filter configuration (categories and industries to keep).

    Returns
    -------
    list[dict]
        Filtered subset of *articles*.
    """
    def _is_relevant(row: dict) -> bool:
        return (
            row.get("category", "") in filter_config.ai_relevant_categories
            or row.get("meta_industry") in filter_config.ai_relevant_industries
        )

    filtered = [row for row in articles if _is_relevant(row)]
    logger.info(
        "AI-relevance filter: %d/%d articles retained "
        "(categories=%s, industries=%s)",
        len(filtered),
        len(articles),
        sorted(filter_config.ai_relevant_categories),
        sorted(filter_config.ai_relevant_industries),
    )
    return filtered
