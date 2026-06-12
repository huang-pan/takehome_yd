"""
tests/test_dates.py — Unit tests for cleaning.dates.

Coverage:
  normalize_date()
    Null / missing inputs
      - None, empty string, whitespace-only
      - "nan", "n/a", "null", "none"

    ISO formats
      - Date-only:           "2022-02-17"
      - ISO 8601 with UTC Z: "2021-09-11T00:00:00Z"

    US format  (M/D/Y)
      - "02/23/2023"
      - "12/28/2021"
      - "04/30/2020"

    EU format  (D/M/Y) — day > 12 heuristic
      - "23-08-2023"  (dash)
      - "23/08/2023"  (slash, if added to formats)
      - Boundary: day == 12 (ambiguous, treated as US)
      - Boundary: day == 13 (unambiguous EU)

    Abbreviated day-month-year
      - "21 Feb 2020"
      - "27 Sep 2020"
      - "02 Jan 2021"  (day <= 12, still parsed correctly)

    Full month name
      - "October 19, 2022"
      - "July 24, 2021"
      - "February 17, 2020"

    Abbreviated month name with comma
      - "Oct 19, 2022"

    Invalid / unrecognisable
      - "not-a-date"
      - "99/99/9999"
      - "32-13-2020"
      - Returns None, does NOT raise

    Return type
      - Always datetime or None

  extract_date_parts()
    - None input → all None
    - Quarter boundaries: Jan(Q1), Mar(Q1), Apr(Q2), Jun(Q2),
                          Jul(Q3), Sep(Q3), Oct(Q4), Dec(Q4)
    - Year and month extraction correctness
"""

import pytest
from datetime import datetime
from cleaning.dates import normalize_date, extract_date_parts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def dt(year, month, day):
    """Shorthand for datetime(year, month, day)."""
    return datetime(year, month, day)


# ---------------------------------------------------------------------------
# Null / missing inputs → None
# ---------------------------------------------------------------------------

class TestNullInputs:
    @pytest.mark.parametrize("value", [
        None,
        "",
        "   ",
        "nan",
        "NaN",
        "n/a",
        "N/A",
        "null",
        "Null",
        "none",
        "None",
    ])
    def test_null_values_return_none(self, value):
        assert normalize_date(value) is None


# ---------------------------------------------------------------------------
# Return type is always datetime or None
# ---------------------------------------------------------------------------

class TestReturnType:
    @pytest.mark.parametrize("value", [
        "2022-02-17", "02/23/2023", "21 Feb 2020", "October 19, 2022",
    ])
    def test_valid_returns_datetime(self, value):
        result = normalize_date(value)
        assert isinstance(result, datetime)

    @pytest.mark.parametrize("value", [None, "", "N/A", "not-a-date"])
    def test_invalid_or_null_returns_none(self, value):
        assert normalize_date(value) is None


# ---------------------------------------------------------------------------
# ISO formats
# ---------------------------------------------------------------------------

class TestISOFormats:
    def test_iso_date_only(self):
        assert normalize_date("2022-02-17") == dt(2022, 2, 17)

    def test_iso_date_only_jan(self):
        assert normalize_date("2020-01-15") == dt(2020, 1, 15)

    def test_iso_date_only_dec(self):
        assert normalize_date("2023-12-13") == dt(2023, 12, 13)

    def test_iso_8601_with_utc_z(self):
        assert normalize_date("2021-09-11T00:00:00Z") == dt(2021, 9, 11)

    def test_iso_8601_with_utc_z_jan(self):
        assert normalize_date("2021-01-01T00:00:00Z") == dt(2021, 1, 1)

    def test_iso_8601_with_utc_z_dec(self):
        assert normalize_date("2023-12-22T00:00:00Z") == dt(2023, 12, 22)


# ---------------------------------------------------------------------------
# US format M/D/Y
# ---------------------------------------------------------------------------

class TestUSFormat:
    def test_us_slash_standard(self):
        assert normalize_date("02/23/2023") == dt(2023, 2, 23)

    def test_us_slash_dec(self):
        assert normalize_date("12/28/2021") == dt(2021, 12, 28)

    def test_us_slash_apr(self):
        assert normalize_date("04/30/2020") == dt(2020, 4, 30)

    def test_us_slash_oct(self):
        assert normalize_date("10/14/2023") == dt(2023, 10, 14)

    def test_us_slash_month_12_day_26(self):
        assert normalize_date("12/26/2022") == dt(2022, 12, 26)


# ---------------------------------------------------------------------------
# EU format D/M/Y or D-M-Y  (leading day > 12 triggers heuristic)
# ---------------------------------------------------------------------------

class TestEUFormat:
    def test_eu_dash_day_gt_12(self):
        assert normalize_date("23-08-2023") == dt(2023, 8, 23)

    def test_eu_dash_day_31(self):
        assert normalize_date("31-01-2022") == dt(2022, 1, 31)

    def test_eu_dash_day_27(self):
        assert normalize_date("27-03-2021") == dt(2021, 3, 27)

    def test_eu_day_exactly_13(self):
        """13 > 12, so must be treated as EU D-M-Y."""
        assert normalize_date("13-06-2020") == dt(2020, 6, 13)

    def test_ambiguous_day_12_treated_as_us(self):
        """Day=12, month part would be 06 — US parse gives Dec 6 if slash format,
        but "12/06/2020" → US: month=12, day=6."""
        result = normalize_date("12/06/2020")
        # US interpretation: December 6, 2020
        assert result == dt(2020, 12, 6)


# ---------------------------------------------------------------------------
# Abbreviated day-month-year  e.g. "21 Feb 2020"
# ---------------------------------------------------------------------------

class TestAbbreviatedDMY:
    def test_feb(self):
        assert normalize_date("21 Feb 2020") == dt(2020, 2, 21)

    def test_sep(self):
        assert normalize_date("27 Sep 2020") == dt(2020, 9, 27)

    def test_apr(self):
        assert normalize_date("20 Apr 2020") == dt(2020, 4, 20)

    def test_day_lte_12(self):
        """Day ≤ 12 still parses correctly via %d %b %Y."""
        assert normalize_date("02 Jan 2021") == dt(2021, 1, 2)

    def test_three_letter_month_dec(self):
        assert normalize_date("15 Dec 2022") == dt(2022, 12, 15)

    def test_three_letter_month_jul(self):
        assert normalize_date("08 Jul 2023") == dt(2023, 7, 8)


# ---------------------------------------------------------------------------
# Full month name  e.g. "October 19, 2022"
# ---------------------------------------------------------------------------

class TestFullMonthName:
    def test_october(self):
        assert normalize_date("October 19, 2022") == dt(2022, 10, 19)

    def test_july(self):
        assert normalize_date("July 24, 2021") == dt(2021, 7, 24)

    def test_february(self):
        assert normalize_date("February 17, 2020") == dt(2020, 2, 17)

    def test_january(self):
        assert normalize_date("January 15, 2023") == dt(2023, 1, 15)

    def test_december(self):
        assert normalize_date("December 31, 2022") == dt(2022, 12, 31)

    def test_abbreviated_month_with_comma(self):
        assert normalize_date("Oct 19, 2022") == dt(2022, 10, 19)

    def test_abbreviated_month_jan(self):
        assert normalize_date("Jan 01, 2020") == dt(2020, 1, 1)


# ---------------------------------------------------------------------------
# Invalid / unrecognisable inputs → None (no exception raised)
# ---------------------------------------------------------------------------

class TestInvalidInputs:
    @pytest.mark.parametrize("value", [
        "not-a-date",
        "hello world",
        "99/99/9999",
        "32-13-2020",
        "2020-13-01",    # month 13 is invalid
        "abc",
        "!!??",
    ])
    def test_invalid_returns_none_no_exception(self, value):
        result = normalize_date(value)
        assert result is None

    def test_non_string_numeric_returns_none(self):
        """Integers with no date meaning should return None."""
        result = normalize_date(99999)
        assert result is None


# ---------------------------------------------------------------------------
# extract_date_parts — quarter boundaries
# ---------------------------------------------------------------------------

class TestExtractDateParts:
    def test_none_returns_all_none(self):
        result = extract_date_parts(None)
        assert result == {"pub_year": None, "pub_quarter": None, "pub_month": None}

    # Q1: Jan, Feb, Mar
    @pytest.mark.parametrize("month,expected_q", [
        (1, 1), (2, 1), (3, 1),
        (4, 2), (5, 2), (6, 2),
        (7, 3), (8, 3), (9, 3),
        (10, 4), (11, 4), (12, 4),
    ])
    def test_quarter_boundaries(self, month, expected_q):
        result = extract_date_parts(datetime(2022, month, 15))
        assert result["pub_quarter"] == expected_q

    def test_year_extraction(self):
        result = extract_date_parts(datetime(2023, 6, 1))
        assert result["pub_year"] == 2023

    def test_month_extraction(self):
        result = extract_date_parts(datetime(2022, 8, 15))
        assert result["pub_month"] == 8

    def test_full_example(self):
        result = extract_date_parts(datetime(2022, 8, 15))
        assert result == {"pub_year": 2022, "pub_quarter": 3, "pub_month": 8}

    def test_jan_q1_full(self):
        result = extract_date_parts(datetime(2020, 1, 1))
        assert result == {"pub_year": 2020, "pub_quarter": 1, "pub_month": 1}

    def test_dec_q4_full(self):
        result = extract_date_parts(datetime(2023, 12, 31))
        assert result == {"pub_year": 2023, "pub_quarter": 4, "pub_month": 12}
