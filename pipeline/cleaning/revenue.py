"""
revenue.py — Revenue string parsing and currency normalization.

Handles:
  - Currency symbols: $, £, €, ¥ (and suffixed "USD", "EUR", "GBP", "JPY")
  - Magnitude suffixes: B/billion, M/million, K/thousand
  - Ranges like "$10M - $20M"  → midpoint
  - Null/N/A/Not disclosed/empty → 0
  - Returns integer USD value
"""

import re
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Currency conversion rates (approximate, per assignment spec)
# ---------------------------------------------------------------------------
CURRENCY_RATES: dict[str, float] = {
    "USD": 1.0,
    "GBP": 1.27,
    "EUR": 1.10,
    "JPY": 1 / 150,
}

# Symbol → ISO code
SYMBOL_MAP: dict[str, str] = {
    "$": "USD",
    "£": "GBP",
    "€": "EUR",
    "¥": "JPY",
}

# Suffix → numeric multiplier
SUFFIX_MAP: dict[str, float] = {
    "billion": 1_000_000_000,
    "b":       1_000_000_000,
    "million": 1_000_000,
    "m":       1_000_000,
    "k":       1_000,
}

# Values treated as zero / missing
_NULL_PATTERN = re.compile(
    r"^\s*(nan|null|n/?a|not\s+disclosed|none|--|)\s*$",
    re.IGNORECASE,
)


def _parse_single(raw: str) -> float:
    """
    Parse a single (non-range) revenue string into a USD float.

    Parameters
    ----------
    raw : str
        A revenue string such as "$5.2B", "£245,788,308", "1599.7M USD",
        "¥19,433,464,710", "N/A".

    Returns
    -------
    float
        USD value, or 0.0 for null/unrecognised inputs.
    """
    raw = raw.strip()

    # --- Null / missing check ---
    if _NULL_PATTERN.match(raw):
        return 0.0

    # --- Detect currency ---
    currency = "USD"
    for symbol, code in SYMBOL_MAP.items():
        if symbol in raw:
            currency = code
            raw = raw.replace(symbol, "").strip()
            break
    else:
        # Check for trailing/leading ISO code (e.g. "1599.7M USD")
        iso_match = re.search(r"\b(USD|EUR|GBP|JPY)\b", raw, re.IGNORECASE)
        if iso_match:
            currency = iso_match.group(1).upper()
            raw = raw[: iso_match.start()].strip() + raw[iso_match.end() :].strip()

    # --- Remove commas, extra spaces ---
    raw = raw.replace(",", "").strip()

    # --- Detect magnitude suffix ---
    multiplier = 1.0
    suffix_match = re.search(r"([0-9.]+)\s*(billion|million|[bBmMkK])\b", raw, re.IGNORECASE)
    if suffix_match:
        num_str = suffix_match.group(1)
        suf = suffix_match.group(2).lower()
        multiplier = SUFFIX_MAP.get(suf, 1.0)
        try:
            amount = float(num_str) * multiplier
        except ValueError:
            logger.warning("Could not parse numeric part '%s' in '%s'", num_str, raw)
            return 0.0
    else:
        # Plain number
        num_match = re.search(r"[0-9]+(?:\.[0-9]+)?", raw)
        if num_match:
            try:
                amount = float(num_match.group())
            except ValueError:
                logger.warning("Could not extract number from '%s'", raw)
                return 0.0
        else:
            logger.warning("No numeric content found in revenue string '%s'", raw)
            return 0.0

    # --- Convert to USD ---
    rate = CURRENCY_RATES.get(currency, 1.0)
    return amount * rate


def clean_revenue(raw: object) -> int:
    """
    Clean a raw revenue value and return an integer USD amount.

    Handles ranges (returns midpoint), multiple currency symbols,
    magnitude suffixes, and null/missing values.

    Parameters
    ----------
    raw : object
        Raw revenue value from the CSV (str, float, or None/NaN).

    Returns
    -------
    int
        Cleaned revenue in USD.  Returns 0 for null / unrecognised inputs.

    Examples
    --------
    >>> clean_revenue("$5.2B")
    5200000000
    >>> clean_revenue("£245,788,308")
    312151151
    >>> clean_revenue("$10M - $20M")
    15000000
    >>> clean_revenue("N/A")
    0
    >>> clean_revenue("¥19,433,464,710")
    129556431
    """
    if raw is None:
        return 0
    text = str(raw).strip()

    # Handle NaN from float representation
    if _NULL_PATTERN.match(text):
        return 0

    # --- Range detection: "X - Y" or "X to Y" ---
    range_match = re.search(
        r"([£€¥$]?[0-9,.]+(?:\s*(?:billion|million|[bBmMkK]))?(?:\s*(?:USD|EUR|GBP|JPY))?)"
        r"\s*[-–to]+\s*"
        r"([£€¥$]?[0-9,.]+(?:\s*(?:billion|million|[bBmMkK]))?(?:\s*(?:USD|EUR|GBP|JPY))?)",
        text,
        re.IGNORECASE,
    )
    if range_match:
        lo = _parse_single(range_match.group(1))
        hi = _parse_single(range_match.group(2))
        return int(round((lo + hi) / 2))

    return int(round(_parse_single(text)))
