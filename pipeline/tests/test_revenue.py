"""
tests/test_revenue.py — Unit tests for cleaning.revenue.clean_revenue.

Coverage:
  Null / missing inputs
    - None, empty string, whitespace-only
    - "N/A", "n/a", "NA", "null", "Null", "NULL", "nan", "NaN"
    - "Not disclosed", "Not Disclosed", "--"

  Plain USD values
    - Integer string: "5000000"
    - Float string:   "584.8"         (treated as bare dollars, not millions)
    - Dollar symbol:  "$584.8M"

  Magnitude suffixes (case-insensitive)
    - B / b / billion / Billion
    - M / m / million / Million
    - K / k

  Currency conversion
    - GBP  £ symbol       → × 1.27
    - EUR  € symbol       → × 1.10
    - JPY  ¥ symbol       → ÷ 150
    - Inline ISO code:    "1599.7M USD", "548.3M EUR", "296.9B JPY"

  Range inputs (midpoint)
    - "$10M - $20M"
    - "$10M – $20M"   (en-dash)
    - Unitless range: "10000000 - 20000000"

  Real-world samples from tech_news.csv
    - "£245,788,308"
    - "¥19,433,464,710"
    - "$6649.8M"
    - "$0.10B"
    - "$0.08 billion"
    - "€548,334,039"
    - "$87.3M"
    - "1599.7M USD"

  Return type
    - Always int, never float
"""

import math
import pytest
from cleaning.revenue import clean_revenue, CURRENCY_RATES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GBP = CURRENCY_RATES["GBP"]   # 1.27
EUR = CURRENCY_RATES["EUR"]   # 1.10
JPY = CURRENCY_RATES["JPY"]   # 1/150


# ---------------------------------------------------------------------------
# Null / missing inputs → 0
# ---------------------------------------------------------------------------

class TestNullInputs:
    """All null-like inputs must return integer 0."""

    @pytest.mark.parametrize("value", [
        None,
        "",
        "   ",
        "N/A",
        "n/a",
        "NA",
        "null",
        "Null",
        "NULL",
        "nan",
        "NaN",
        "Not disclosed",
        "Not Disclosed",
        "NOT DISCLOSED",
        "--",
        "none",
        "None",
    ])
    def test_null_values_return_zero(self, value):
        assert clean_revenue(value) == 0

    def test_float_nan_returns_zero(self):
        """float('nan') cast to string is 'nan' — must return 0."""
        assert clean_revenue(float("nan")) == 0

    def test_none_returns_zero(self):
        assert clean_revenue(None) == 0


# ---------------------------------------------------------------------------
# Return type is always int
# ---------------------------------------------------------------------------

class TestReturnType:
    @pytest.mark.parametrize("value", [
        "$5.2B", "£100M", "1000000", "0", None, "N/A",
    ])
    def test_always_returns_int(self, value):
        result = clean_revenue(value)
        assert isinstance(result, int), f"Expected int, got {type(result)} for input {value!r}"


# ---------------------------------------------------------------------------
# Plain USD amounts
# ---------------------------------------------------------------------------

class TestPlainUSD:
    def test_plain_integer_string(self):
        assert clean_revenue("5000000") == 5_000_000

    def test_plain_integer_with_commas(self):
        assert clean_revenue("5,200,000") == 5_200_000

    def test_dollar_symbol_plain_number(self):
        assert clean_revenue("$100") == 100

    def test_zero_string(self):
        assert clean_revenue("0") == 0

    def test_zero_dollar(self):
        assert clean_revenue("$0") == 0


# ---------------------------------------------------------------------------
# Magnitude suffixes — USD
# ---------------------------------------------------------------------------

class TestMagnitudeSuffixes:
    # Billions
    def test_upper_B(self):
        assert clean_revenue("$5.2B") == 5_200_000_000

    def test_lower_b(self):
        assert clean_revenue("$5.2b") == 5_200_000_000

    def test_word_billion(self):
        assert clean_revenue("$5.2 billion") == 5_200_000_000

    def test_word_Billion_titlecase(self):
        assert clean_revenue("$5.2 Billion") == 5_200_000_000

    def test_small_B_fraction(self):
        assert clean_revenue("$0.10B") == 100_000_000

    def test_small_billion_word(self):
        assert clean_revenue("$0.08 billion") == 80_000_000

    # Millions
    def test_upper_M(self):
        assert clean_revenue("$87.3M") == 87_300_000

    def test_lower_m(self):
        assert clean_revenue("$87.3m") == 87_300_000

    def test_word_million(self):
        assert clean_revenue("5.2 million") == 5_200_000

    def test_large_M_value(self):
        assert clean_revenue("$6649.8M") == 6_649_800_000

    def test_decimal_M(self):
        assert clean_revenue("$584.8M") == 584_800_000

    # Thousands
    def test_upper_K(self):
        assert clean_revenue("$500K") == 500_000

    def test_lower_k(self):
        assert clean_revenue("$500k") == 500_000


# ---------------------------------------------------------------------------
# Currency conversion
# ---------------------------------------------------------------------------

class TestCurrencyConversion:
    def test_gbp_symbol(self):
        result = clean_revenue("£245,788,308")
        expected = int(round(245_788_308 * GBP))
        assert result == expected

    def test_eur_symbol(self):
        result = clean_revenue("€548,334,039")
        expected = int(round(548_334_039 * EUR))
        assert result == expected

    def test_jpy_symbol_large(self):
        result = clean_revenue("¥19,433,464,710")
        expected = int(round(19_433_464_710 * JPY))
        assert result == expected

    def test_gbp_with_M_suffix(self):
        result = clean_revenue("£100M")
        expected = int(round(100_000_000 * GBP))
        assert result == expected

    def test_eur_with_M_suffix(self):
        result = clean_revenue("€200M")
        expected = int(round(200_000_000 * EUR))
        assert result == expected

    def test_inline_usd_iso_code(self):
        result = clean_revenue("1599.7M USD")
        assert result == 1_599_700_000

    def test_inline_eur_iso_code(self):
        result = clean_revenue("548.3M EUR")
        expected = int(round(548_300_000 * EUR))
        assert result == expected

    def test_inline_gbp_iso_code(self):
        result = clean_revenue("100M GBP")
        expected = int(round(100_000_000 * GBP))
        assert result == expected

    def test_inline_jpy_iso_code(self):
        result = clean_revenue("296.9B JPY")
        expected = int(round(296_900_000_000 * JPY))
        assert result == expected

    def test_gbp_plain_number(self):
        result = clean_revenue("£19,046,363")
        expected = int(round(19_046_363 * GBP))
        assert result == expected


# ---------------------------------------------------------------------------
# Range inputs → midpoint
# ---------------------------------------------------------------------------

class TestRangeInputs:
    def test_dollar_M_range_hyphen(self):
        # ($10M + $20M) / 2 = $15M
        assert clean_revenue("$10M - $20M") == 15_000_000

    def test_dollar_M_range_en_dash(self):
        assert clean_revenue("$10M – $20M") == 15_000_000

    def test_dollar_B_range(self):
        # ($1B + $2B) / 2 = $1.5B
        assert clean_revenue("$1B - $2B") == 1_500_000_000

    def test_unitless_range(self):
        assert clean_revenue("10000000 - 20000000") == 15_000_000

    def test_asymmetric_range(self):
        # ($5M + $15M) / 2 = $10M
        assert clean_revenue("$5M - $15M") == 10_000_000

    def test_range_with_gbp(self):
        lo = int(round(10_000_000 * GBP))
        hi = int(round(20_000_000 * GBP))
        expected = (lo + hi) // 2
        result = clean_revenue("£10M - £20M")
        assert abs(result - expected) <= 1   # allow rounding ±1


# ---------------------------------------------------------------------------
# Real-world samples from tech_news.csv
# ---------------------------------------------------------------------------

class TestRealWorldSamples:
    """Values seen in the actual dataset — regression guard."""

    def test_gbp_raw_integer(self):
        assert clean_revenue("£245,788,308") == int(round(245_788_308 * GBP))

    def test_jpy_raw_large_integer(self):
        assert clean_revenue("¥19,433,464,710") == int(round(19_433_464_710 * JPY))

    def test_large_M_usd(self):
        assert clean_revenue("$6649.8M") == 6_649_800_000

    def test_fractional_B_usd(self):
        assert clean_revenue("$0.10B") == 100_000_000

    def test_fractional_billion_word(self):
        assert clean_revenue("$0.08 billion") == 80_000_000

    def test_eur_raw_integer(self):
        assert clean_revenue("€548,334,039") == int(round(548_334_039 * EUR))

    def test_small_M_usd(self):
        assert clean_revenue("$87.3M") == 87_300_000

    def test_usd_iso_suffix(self):
        assert clean_revenue("1599.7M USD") == 1_599_700_000

    def test_small_M_usd_2(self):
        assert clean_revenue("$20.1M") == 20_100_000

    def test_another_M_usd(self):
        assert clean_revenue("$37.3M") == 37_300_000
