"""Currency Agent - Handles currency conversion logic and FX operations.

This agent is responsible for:
- Currency conversions with correct rounding order
- FX rate management
- Decimal precision handling
- Currency validation
"""

from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN, ROUND_UP
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging

from framework.models.currency import CurrencyCode, get_currency


logger = logging.getLogger(__name__)


class CurrencyConversionError(Exception):
    """Raised when currency conversion fails."""
    pass


class CurrencyAgent:
    """Agent for handling currency operations in tests."""

    def __init__(self, fx_rates: Optional[Dict[str, Decimal]] = None):
        """
        Initialize Currency Agent.

        Args:
            fx_rates: Optional dict of FX rates. If None, uses default test rates.
        """
        self.fx_rates = fx_rates or self._get_default_fx_rates()
        self.rate_cache_ttl = timedelta(minutes=5)
        self.last_rate_update = datetime.utcnow()

    def _get_default_fx_rates(self) -> Dict[str, Decimal]:
        """
        Get default FX rates for testing.

        Format: "FROM_TO" -> rate
        """
        return {
            # EUR conversions
            "EUR_USD": Decimal("1.0850"),
            "EUR_GBP": Decimal("0.8650"),
            "EUR_BRL": Decimal("5.3750"),
            "EUR_CLP": Decimal("1052.00"),  # THE CRITICAL RATE from the incident
            "EUR_JPY": Decimal("161.25"),
            "EUR_KRW": Decimal("1445.50"),
            "EUR_COP": Decimal("4250.00"),
            "EUR_MXN": Decimal("18.50"),

            # USD conversions
            "USD_EUR": Decimal("0.9217"),
            "USD_GBP": Decimal("0.7970"),
            "USD_BRL": Decimal("4.9545"),
            "USD_CLP": Decimal("969.50"),
            "USD_JPY": Decimal("148.65"),
            "USD_KRW": Decimal("1332.15"),
            "USD_COP": Decimal("3918.00"),

            # GBP conversions
            "GBP_EUR": Decimal("1.1560"),
            "GBP_USD": Decimal("1.2547"),
            "GBP_JPY": Decimal("186.45"),
            "GBP_CLP": Decimal("1216.50"),
            "GBP_COP": Decimal("4915.00"),

            # BRL conversions
            "BRL_EUR": Decimal("0.1860"),
            "BRL_USD": Decimal("0.2018"),
            "BRL_CLP": Decimal("195.75"),

            # Three-decimal currencies
            "EUR_KWD": Decimal("0.3345"),
            "USD_KWD": Decimal("0.3082"),
            "EUR_BHD": Decimal("0.4089"),
            "EUR_OMR": Decimal("0.4175"),

            # Reverse rates (for testing)
            "CLP_EUR": Decimal("0.0009506"),
            "JPY_EUR": Decimal("0.0062034"),
            "COP_EUR": Decimal("0.0002353"),
        }

    def get_fx_rate(
        self,
        from_currency: CurrencyCode,
        to_currency: CurrencyCode,
        timestamp: Optional[datetime] = None
    ) -> Decimal:
        """
        Get FX rate between two currencies.

        Args:
            from_currency: Source currency
            to_currency: Target currency
            timestamp: Optional timestamp for rate (for testing rate staleness)

        Returns:
            FX rate as Decimal

        Raises:
            CurrencyConversionError: If rate not available
        """
        if from_currency == to_currency:
            return Decimal("1.0")

        rate_key = f"{from_currency.value}_{to_currency.value}"

        if rate_key not in self.fx_rates:
            raise CurrencyConversionError(
                f"FX rate not available for {from_currency} -> {to_currency}"
            )

        # Simulate stale rate check
        if timestamp:
            age = datetime.utcnow() - timestamp
            if age > self.rate_cache_ttl:
                logger.warning(f"FX rate for {rate_key} is stale (age: {age})")

        return self.fx_rates[rate_key]

    def convert_amount(
        self,
        amount: Decimal,
        from_currency: CurrencyCode,
        to_currency: CurrencyCode,
        round_before_conversion: bool = False  # THE BUG PARAMETER
    ) -> Tuple[Decimal, Decimal]:
        """
        Convert amount from one currency to another.

        THIS IS THE CRITICAL METHOD THAT REPRODUCES THE BUG.

        Args:
            amount: Amount to convert
            from_currency: Source currency
            to_currency: Target currency
            round_before_conversion: If True, implements the BUG (rounds before converting)
                                    If False, implements CORRECT behavior (rounds after converting)

        Returns:
            Tuple of (converted_amount, fx_rate_used)

        Raises:
            CurrencyConversionError: If conversion fails
        """
        if from_currency == to_currency:
            return amount, Decimal("1.0")

        # Get FX rate
        fx_rate = self.get_fx_rate(from_currency, to_currency)

        # Get currency configs
        from_config = get_currency(from_currency)
        to_config = get_currency(to_currency)

        if round_before_conversion:
            # BUG: Round the source amount first (INCORRECT)
            rounded_source = from_config.round_amount(amount)
            converted = rounded_source * fx_rate
            final_amount = to_config.round_amount(converted)

            logger.warning(
                f"BUG MODE: Rounded {amount} -> {rounded_source} before conversion. "
                f"Result: {final_amount} {to_currency}"
            )
        else:
            # CORRECT: Convert first, then round to target currency
            converted = amount * fx_rate
            final_amount = to_config.round_amount(converted)

            logger.debug(
                f"CORRECT: Converted {amount} {from_currency} * {fx_rate} = {converted}, "
                f"rounded to {final_amount} {to_currency}"
            )

        return final_amount, fx_rate

    def validate_amount_for_currency(
        self,
        amount: Decimal,
        currency: CurrencyCode
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate if amount is valid for the given currency.

        Args:
            amount: Amount to validate
            currency: Currency code

        Returns:
            Tuple of (is_valid, error_message)
        """
        config = get_currency(currency)

        # Check minimum
        if amount < config.min_amount:
            return False, f"Amount {amount} is below minimum {config.min_amount} for {currency}"

        # Check maximum
        if amount > config.max_amount:
            return False, f"Amount {amount} exceeds maximum {config.max_amount} for {currency}"

        # Check decimal places
        amount_str = str(amount)
        if '.' in amount_str:
            decimal_places = len(amount_str.split('.')[1])
            if decimal_places > config.decimal_places:
                return False, (
                    f"Amount {amount} has {decimal_places} decimal places, "
                    f"but {currency} only supports {config.decimal_places}"
                )

        return True, None

    def calculate_expected_authorization_amount(
        self,
        original_amount: Decimal,
        original_currency: CurrencyCode,
        settlement_currency: CurrencyCode,
        use_correct_logic: bool = True
    ) -> Decimal:
        """
        Calculate expected authorization amount.

        This is used in tests to verify the system behavior.

        Args:
            original_amount: Original purchase amount
            original_currency: Currency shown to customer
            settlement_currency: Currency merchant settles in
            use_correct_logic: If True, uses correct rounding order

        Returns:
            Expected authorization amount
        """
        converted_amount, _ = self.convert_amount(
            amount=original_amount,
            from_currency=original_currency,
            to_currency=settlement_currency,
            round_before_conversion=not use_correct_logic
        )
        return converted_amount

    def format_amount_for_display(
        self,
        amount: Decimal,
        currency: CurrencyCode
    ) -> str:
        """
        Format amount for customer display.

        Args:
            amount: Amount to format
            currency: Currency code

        Returns:
            Formatted string (e.g., "€49.99", "¥5250", "KD 123.456")
        """
        config = get_currency(currency)
        return config.format_amount(amount)

    def is_zero_decimal_currency(self, currency: CurrencyCode) -> bool:
        """Check if currency is zero-decimal."""
        config = get_currency(currency)
        return config.decimal_places == 0

    def is_three_decimal_currency(self, currency: CurrencyCode) -> bool:
        """Check if currency is three-decimal."""
        config = get_currency(currency)
        return config.decimal_places == 3
