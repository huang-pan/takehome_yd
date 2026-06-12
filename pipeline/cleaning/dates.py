"""
dates.py — Date normalization across multiple input formats.

Handles:
  - ISO 8601:       "2022-02-17"
  - US format:      "02/23/2023"
  - EU format:      "23-08-2023"
  - Day-Month-Year: "21 Feb 2020", "27 Sep 2020"
  - Long form:      "October 19, 2022", "July 24, 2021"
  - Mixed:          "23-08-2023" (detected when day part > 12)

Returns a datetime object (or None for invalid/missing input) and
extracts year, quarter, and month as helper fields.
"""

import re
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Ordered list of (format_string, dayfirst) pairs to try with strptime.
# We try unambiguous formats first, then fall back to ambiguous ones.
_STRPTIME_FORMATS: list[tuple[str, bool]] = [
    ("%Y-%m-%dT%H:%M:%SZ", False),  # 2021-09-11T00:00:00Z  (ISO 8601 with UTC Z)
    ("%Y-%m-%d",           False),  # 2022-02-17             (ISO date-only)
    ("%m/%d/%Y",           False),  # 02/23/2023             (US)
    ("%d/%m/%Y",           True),   # 23/08/2023             (EU slash)
    ("%d-%m-%Y",           True),   # 23-08-2023             (EU dash)
    ("%d %b %Y",           True),   # 21 Feb 2020
    ("%d %B %Y",           True),   # 21 February 2020
    ("%B %d, %Y",          False),  # October 19, 2022
    ("%b %d, %Y",          False),  # Oct 19, 2022
]


def _is_eu_dmy(text: str) -> bool:
    """
    Heuristic: if the first numeric token is > 12 it can only be a day,
    so the format must be D-M-Y (EU).
    """
    m = re.match(r"^(\d{1,2})[-/]", text)
    if m:
        return int(m.group(1)) > 12
    return False


def normalize_date(raw: object) -> Optional[datetime]:
    """
    Parse a raw date string into a :class:`datetime` object.

    Tries multiple formats in a defined priority order.  When the first
    numeric token is > 12, the string is unambiguously D-M-Y (EU style)
    and US formats are skipped.

    Parameters
    ----------
    raw : object
        Raw date value from the CSV.

    Returns
    -------
    datetime or None
        Parsed datetime, or ``None`` for invalid / missing input.

    Examples
    --------
    >>> normalize_date("2022-02-17")
    datetime.datetime(2022, 2, 17, 0, 0)
    >>> normalize_date("02/23/2023")
    datetime.datetime(2023, 2, 23, 0, 0)
    >>> normalize_date("21 Feb 2020")
    datetime.datetime(2020, 2, 21, 0, 0)
    >>> normalize_date("October 19, 2022")
    datetime.datetime(2022, 10, 19, 0, 0)
    >>> normalize_date("N/A") is None
    True
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.lower() in ("nan", "n/a", "null", "none", ""):
        return None

    eu_first = _is_eu_dmy(text)

    for fmt, dayfirst in _STRPTIME_FORMATS:
        # Skip US-style format when the date is clearly EU D-M-Y
        if eu_first and not dayfirst and fmt in ("%m/%d/%Y",):
            continue
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    logger.warning("Could not parse date: '%s'", raw)
    return None


def extract_date_parts(dt: Optional[datetime]) -> dict[str, Optional[int]]:
    """
    Extract year, quarter, and month from a datetime object.

    Parameters
    ----------
    dt : datetime or None

    Returns
    -------
    dict
        Keys: ``pub_year``, ``pub_quarter``, ``pub_month``.
        All values are ``None`` when *dt* is ``None``.

    Examples
    --------
    >>> extract_date_parts(datetime(2022, 8, 15))
    {'pub_year': 2022, 'pub_quarter': 3, 'pub_month': 8}
    """
    if dt is None:
        return {"pub_year": None, "pub_quarter": None, "pub_month": None}
    return {
        "pub_year":    dt.year,
        "pub_quarter": (dt.month - 1) // 3 + 1,
        "pub_month":   dt.month,
    }
