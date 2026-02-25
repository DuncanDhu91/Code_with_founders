"""Unit tests for currency metadata."""

import pytest
from src.currencies import (
    CURRENCIES,
    get_currency,
    get_decimal_places,
    is_supported_currency,
)
from src.exceptions import InvalidCurrencyError


class TestCurrencyMetadata:
    """Test currency metadata registry."""

    def test_currencies_dict_contains_six_currencies(self):
        """Verify that CURRENCIES dict contains exactly 6 currencies."""
        assert len(CURRENCIES) == 6

    def test_currencies_dict_contains_expected_codes(self):
        """Verify that all expected currency codes are present."""
        expected_codes = {"USD", "EUR", "GBP", "JPY", "MXN", "BRL"}
        assert set(CURRENCIES.keys()) == expected_codes

    def test_currency_metadata_structure(self):
        """Verify that each currency has required metadata fields."""
        required_fields = {"code", "name", "symbol", "decimal_places"}
        for code, metadata in CURRENCIES.items():
            assert set(metadata.keys()) == required_fields

    def test_usd_metadata(self):
        """Verify USD metadata is correct."""
        usd = CURRENCIES["USD"]
        assert usd["code"] == "USD"
        assert usd["name"] == "US Dollar"
        assert usd["symbol"] == "$"
        assert usd["decimal_places"] == 2

    def test_eur_metadata(self):
        """Verify EUR metadata is correct."""
        eur = CURRENCIES["EUR"]
        assert eur["code"] == "EUR"
        assert eur["name"] == "Euro"
        assert eur["symbol"] == "€"
        assert eur["decimal_places"] == 2

    def test_jpy_metadata_zero_decimals(self):
        """Verify JPY has zero decimal places."""
        jpy = CURRENCIES["JPY"]
        assert jpy["code"] == "JPY"
        assert jpy["decimal_places"] == 0

    def test_get_currency_returns_metadata(self):
        """Test get_currency returns correct metadata."""
        usd = get_currency("USD")
        assert usd["code"] == "USD"
        assert usd["decimal_places"] == 2

    def test_get_currency_raises_on_invalid_code(self):
        """Test get_currency raises InvalidCurrencyError for invalid code."""
        with pytest.raises(InvalidCurrencyError) as exc_info:
            get_currency("INVALID")
        assert "INVALID" in str(exc_info.value)
        assert "not supported" in str(exc_info.value)

    def test_get_decimal_places_returns_correct_value(self):
        """Test get_decimal_places returns correct number."""
        assert get_decimal_places("USD") == 2
        assert get_decimal_places("EUR") == 2
        assert get_decimal_places("JPY") == 0

    def test_get_decimal_places_raises_on_invalid_code(self):
        """Test get_decimal_places raises InvalidCurrencyError for invalid code."""
        with pytest.raises(InvalidCurrencyError):
            get_decimal_places("XYZ")

    def test_is_supported_currency_returns_true_for_valid_codes(self):
        """Test is_supported_currency returns True for valid codes."""
        assert is_supported_currency("USD") is True
        assert is_supported_currency("EUR") is True
        assert is_supported_currency("JPY") is True

    def test_is_supported_currency_returns_false_for_invalid_codes(self):
        """Test is_supported_currency returns False for invalid codes."""
        assert is_supported_currency("INVALID") is False
        assert is_supported_currency("XYZ") is False
        assert is_supported_currency("") is False

    def test_all_currencies_have_positive_or_zero_decimal_places(self):
        """Verify all currencies have valid decimal_places (>= 0)."""
        for code, metadata in CURRENCIES.items():
            assert metadata["decimal_places"] >= 0

    def test_all_currencies_have_non_empty_names(self):
        """Verify all currencies have non-empty names."""
        for code, metadata in CURRENCIES.items():
            assert metadata["name"]
            assert len(metadata["name"]) > 0

    def test_all_currencies_have_non_empty_symbols(self):
        """Verify all currencies have non-empty symbols."""
        for code, metadata in CURRENCIES.items():
            assert metadata["symbol"]
            assert len(metadata["symbol"]) > 0

    def test_currency_codes_are_uppercase(self):
        """Verify all currency codes are uppercase."""
        for code in CURRENCIES.keys():
            assert code.isupper()

    def test_decimal_places_types(self):
        """Verify decimal_places are integers."""
        for code, metadata in CURRENCIES.items():
            assert isinstance(metadata["decimal_places"], int)

    def test_two_decimal_currencies(self):
        """Verify currencies with 2 decimal places."""
        two_decimal = ["USD", "EUR", "GBP", "MXN", "BRL"]
        for code in two_decimal:
            assert get_decimal_places(code) == 2

    def test_zero_decimal_currencies(self):
        """Verify currencies with 0 decimal places."""
        zero_decimal = ["JPY"]
        for code in zero_decimal:
            assert get_decimal_places(code) == 0


class TestExceptions:
    """Test custom exception types."""

    def test_invalid_currency_error_inherits_from_value_error(self):
        """Verify InvalidCurrencyError inherits from ValueError."""
        from src.exceptions import InvalidCurrencyError
        assert issubclass(InvalidCurrencyError, ValueError)

    def test_invalid_amount_error_inherits_from_value_error(self):
        """Verify InvalidAmountError inherits from ValueError."""
        from src.exceptions import InvalidAmountError
        assert issubclass(InvalidAmountError, ValueError)

    def test_conversion_error_inherits_from_exception(self):
        """Verify ConversionError inherits from Exception."""
        from src.exceptions import ConversionError
        assert issubclass(ConversionError, Exception)
