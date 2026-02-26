"""Currency Edge Case Test Suite

Core Requirement 2: Handle 3+ currency edge cases correctly.

This test suite covers:
- FX rate service unavailable
- Amount below currency minimum (e.g., $0.01 → JPY)
- Unsupported currency handling
- Zero amount handling (card verification)
- Minimum/maximum boundary values
- Excessive decimal places
- Negative amounts
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta

from framework.agents.currency_agent import (
    CurrencyAgent,
    CurrencyConversionError
)
from framework.agents.payment_agent import PaymentAgent
from framework.models.currency import CurrencyCode, get_currency
from framework.models.transaction import (
    AuthorizationRequest,
    PaymentMethod,
    TransactionStatus
)


class TestCurrencyEdgeCases:
    """Edge case tests for currency operations."""

    @pytest.fixture
    def currency_agent(self):
        """Create currency agent with test FX rates."""
        return CurrencyAgent()

    @pytest.fixture
    def payment_agent(self, currency_agent):
        """Create payment agent with correct logic."""
        return PaymentAgent(
            currency_agent=currency_agent,
            simulate_bug=False
        )

    def test_fx_rate_unavailable(self, payment_agent):
        """
        TC-EDGE-001: FX rate service unavailable.

        ARRANGE:
        - Request conversion for unsupported pair (no FX rate)

        ACT:
        - Submit authorization

        ASSERT:
        - Authorization fails gracefully
        - Error code: FX_RATE_UNAVAILABLE
        - Error message contains currency pair
        - No transaction created
        """
        # ARRANGE
        request = AuthorizationRequest(
            merchant_id="merchant_001",
            customer_id="customer_001",
            amount=Decimal("100.00"),
            currency=CurrencyCode.EUR,
            settlement_currency=CurrencyCode.PEN,  # Rate not in default rates
            payment_method=PaymentMethod.CARD,
            idempotency_key="test_no_rate_001"
        )

        # ACT
        response = payment_agent.authorize_payment(request)

        # ASSERT
        assert response.status == TransactionStatus.FAILED
        assert response.error_code == "FX_RATE_UNAVAILABLE"
        assert "EUR" in response.message
        assert "PEN" in response.message
        assert response.authorized_amount == Decimal("0")

        # No transaction should be created
        transaction = payment_agent.get_transaction(response.transaction_id)
        assert transaction is None

    def test_minimum_amount_conversion_becomes_valid(self, currency_agent):
        """
        TC-EDGE-002: Minimum amount conversion (becomes valid).

        ARRANGE:
        - Amount: €0.01 EUR (minimum)
        - Convert to JPY

        ACT:
        - Perform conversion

        ASSERT:
        - Result: ¥2 JPY (rounded up from 1.6125)
        - Meets JPY minimum (¥1)
        """
        # ARRANGE
        min_eur = get_currency(CurrencyCode.EUR).min_amount  # €0.01

        # ACT
        result, fx_rate = currency_agent.convert_amount(
            amount=min_eur,
            from_currency=CurrencyCode.EUR,
            to_currency=CurrencyCode.JPY,
            round_before_conversion=False
        )

        # ASSERT
        # 0.01 EUR * 161.25 = 1.6125 JPY → rounds to ¥2
        assert result == Decimal("2")

        # Verify meets JPY minimum
        min_jpy = get_currency(CurrencyCode.JPY).min_amount
        assert result >= min_jpy

    def test_maximum_amount_conversion_no_overflow(self, currency_agent):
        """
        TC-EDGE-003: Maximum amount conversion (no overflow).

        ARRANGE:
        - Amount: €999,999.99 EUR (maximum)
        - Convert to CLP (high rate)

        ACT:
        - Perform conversion

        ASSERT:
        - Result: Large CLP amount
        - No overflow error
        - Within CLP maximum
        """
        # ARRANGE
        max_eur = get_currency(CurrencyCode.EUR).max_amount  # €999,999.99

        # ACT
        result, fx_rate = currency_agent.convert_amount(
            amount=max_eur,
            from_currency=CurrencyCode.EUR,
            to_currency=CurrencyCode.CLP,
            round_before_conversion=False
        )

        # ASSERT
        # 999,999.99 * 1052 = 1,051,999,894.48 → 1,051,999,894 CLP
        expected = Decimal("1051999894")
        assert result == expected

        # Verify within CLP maximum
        max_clp = get_currency(CurrencyCode.CLP).max_amount
        assert result <= max_clp

    def test_amount_below_minimum_rejected(self, currency_agent):
        """
        TC-EDGE-004: Amount below minimum rejected.

        ARRANGE:
        - Amount: €0.001 (below EUR minimum of €0.01)

        ACT:
        - Validate amount

        ASSERT:
        - Validation fails
        - Error message mentions minimum
        """
        # ARRANGE
        below_min = Decimal("0.001")

        # ACT
        is_valid, error_msg = currency_agent.validate_amount_for_currency(
            amount=below_min,
            currency=CurrencyCode.EUR
        )

        # ASSERT
        assert not is_valid
        assert "below minimum" in error_msg.lower()
        assert "0.01" in error_msg  # EUR minimum

    def test_amount_above_maximum_rejected(self, currency_agent):
        """
        TC-EDGE-005: Amount above maximum rejected.

        ARRANGE:
        - Amount: €1,000,000.00 (above EUR maximum)

        ACT:
        - Validate amount

        ASSERT:
        - Validation fails
        - Error message mentions maximum
        """
        # ARRANGE
        above_max = Decimal("1000000.00")

        # ACT
        is_valid, error_msg = currency_agent.validate_amount_for_currency(
            amount=above_max,
            currency=CurrencyCode.EUR
        )

        # ASSERT
        assert not is_valid
        assert "exceeds maximum" in error_msg.lower()
        assert "999999.99" in error_msg  # EUR maximum

    def test_excessive_decimal_places_rejected(self, currency_agent):
        """
        TC-EDGE-006: Excessive decimal places rejected.

        ARRANGE:
        - Amount: €100.999 (3 decimals, EUR supports 2)

        ACT:
        - Validate amount

        ASSERT:
        - Validation fails
        - Error message mentions decimal places
        """
        # ARRANGE
        excessive_decimals = Decimal("100.999")

        # ACT
        is_valid, error_msg = currency_agent.validate_amount_for_currency(
            amount=excessive_decimals,
            currency=CurrencyCode.EUR
        )

        # ASSERT
        assert not is_valid
        assert "decimal places" in error_msg.lower()
        assert "3" in error_msg  # Has 3 decimals
        assert "2" in error_msg  # Supports 2 decimals

    def test_zero_amount_authorization_card_verification(self, payment_agent):
        """
        TC-EDGE-007: Zero amount authorization (card verification).

        ARRANGE:
        - Amount: €0.00
        - Purpose: Card verification

        ACT:
        - Submit authorization

        ASSERT:
        - Fails with INVALID_AMOUNT
        - OR succeeds with zero amount (depends on business logic)
        """
        # ARRANGE
        request = AuthorizationRequest(
            merchant_id="merchant_001",
            customer_id="customer_001",
            amount=Decimal("0.00"),
            currency=CurrencyCode.EUR,
            settlement_currency=CurrencyCode.USD,
            payment_method=PaymentMethod.CARD,
            idempotency_key="test_zero_amount_001"
        )

        # ACT
        response = payment_agent.authorize_payment(request)

        # ASSERT: Either succeeds with zero or fails gracefully
        if response.status == TransactionStatus.AUTHORIZED:
            assert response.authorized_amount == Decimal("0.00")
            assert response.settlement_amount == Decimal("0.00")
        elif response.status == TransactionStatus.FAILED:
            assert response.error_code == "INVALID_AMOUNT"
            assert "0" in response.message.lower()

    def test_repeating_decimal_conversion(self, currency_agent):
        """
        TC-EDGE-008: Repeating decimal in conversion.

        ARRANGE:
        - Amount: €33.33 (1/3 of 100)
        - Creates repeating decimal in conversion

        ACT:
        - Convert to CLP

        ASSERT:
        - Result is correctly rounded
        - Precision loss is minimal
        """
        # ARRANGE
        amount = Decimal("33.33")

        # ACT
        result, fx_rate = currency_agent.convert_amount(
            amount=amount,
            from_currency=CurrencyCode.EUR,
            to_currency=CurrencyCode.CLP,
            round_before_conversion=False
        )

        # ASSERT
        # 33.33 * 1052 = 35,063.16 → 35,063 CLP
        assert result == Decimal("35063")

        # Verify precision loss is minimal
        raw_conversion = amount * fx_rate
        difference = abs(result - raw_conversion)
        assert difference < Decimal("1.0")  # Less than 1 CLP difference

    def test_same_currency_conversion_no_rounding_change(self, currency_agent):
        """
        TC-EDGE-009: Same currency conversion (no-op).

        ARRANGE:
        - Convert EUR → EUR

        ACT:
        - Perform conversion

        ASSERT:
        - Amount unchanged
        - FX rate = 1.0
        - No rounding applied
        """
        # ARRANGE
        amount = Decimal("49.99")

        # ACT
        result, fx_rate = currency_agent.convert_amount(
            amount=amount,
            from_currency=CurrencyCode.EUR,
            to_currency=CurrencyCode.EUR,
            round_before_conversion=False
        )

        # ASSERT
        assert result == amount
        assert fx_rate == Decimal("1.0")

    def test_stale_fx_rate_warning(self, currency_agent, caplog):
        """
        TC-EDGE-010: Stale FX rate warning logged.

        ARRANGE:
        - Request FX rate with stale timestamp (10 minutes ago)

        ACT:
        - Get FX rate

        ASSERT:
        - Rate is returned (fails gracefully)
        - Warning logged about staleness
        """
        # ARRANGE
        import logging
        caplog.set_level(logging.WARNING)
        stale_timestamp = datetime.utcnow() - timedelta(minutes=10)

        # ACT
        fx_rate = currency_agent.get_fx_rate(
            from_currency=CurrencyCode.EUR,
            to_currency=CurrencyCode.CLP,
            timestamp=stale_timestamp
        )

        # ASSERT: Rate returned
        assert fx_rate == Decimal("1052.00")

        # ASSERT: Warning logged
        assert any("stale" in log.lower() for log in caplog.text.split('\n'))

    def test_invalid_amount_in_authorization_request(self, payment_agent):
        """
        TC-EDGE-011: Invalid amount in authorization request.

        ARRANGE:
        - Amount with excessive decimals

        ACT:
        - Submit authorization

        ASSERT:
        - Fails with INVALID_AMOUNT
        - Error message is clear
        """
        # ARRANGE
        request = AuthorizationRequest(
            merchant_id="merchant_001",
            customer_id="customer_001",
            amount=Decimal("100.999"),  # 3 decimals for EUR
            currency=CurrencyCode.EUR,
            settlement_currency=CurrencyCode.USD,
            payment_method=PaymentMethod.CARD,
            idempotency_key="test_invalid_amount_001"
        )

        # ACT
        response = payment_agent.authorize_payment(request)

        # ASSERT
        assert response.status == TransactionStatus.FAILED
        assert response.error_code == "INVALID_AMOUNT"
        assert "decimal" in response.message.lower()

    def test_converted_amount_below_target_minimum(self, currency_agent):
        """
        TC-EDGE-012: Converted amount below target minimum.

        ARRANGE:
        - Small JPY amount → EUR
        - Result may be below EUR minimum

        ACT:
        - Convert ¥1 JPY → EUR

        ASSERT:
        - Conversion produces valid amount
        - OR validation catches sub-minimum result
        """
        # ARRANGE
        small_jpy = Decimal("1")  # ¥1 JPY

        # ACT
        result, fx_rate = currency_agent.convert_amount(
            amount=small_jpy,
            from_currency=CurrencyCode.JPY,
            to_currency=CurrencyCode.EUR,
            round_before_conversion=False
        )

        # ASSERT
        # 1 JPY * 0.0062034 = 0.0062034 EUR → rounds to €0.01 EUR
        assert result == Decimal("0.01")

        # Validate result
        is_valid, error = currency_agent.validate_amount_for_currency(
            result, CurrencyCode.EUR
        )
        assert is_valid  # Should meet EUR minimum

    def test_bidirectional_conversion_roundtrip(self, currency_agent):
        """
        TC-EDGE-013: Bidirectional conversion roundtrip.

        ARRANGE:
        - Convert EUR → CLP → EUR

        ACT:
        - Perform roundtrip conversion

        ASSERT:
        - Original amount recovered within tolerance
        - Acceptable precision loss
        """
        # ARRANGE
        original = Decimal("49.99")

        # ACT: EUR → CLP
        clp_amount, _ = currency_agent.convert_amount(
            original,
            CurrencyCode.EUR,
            CurrencyCode.CLP,
            round_before_conversion=False
        )

        # ACT: CLP → EUR
        back_to_eur, _ = currency_agent.convert_amount(
            clp_amount,
            CurrencyCode.CLP,
            CurrencyCode.EUR,
            round_before_conversion=False
        )

        # ASSERT: Should be close to original (within tolerance)
        difference = abs(back_to_eur - original)
        assert difference <= Decimal("0.01"), \
            f"Roundtrip loss too high: {difference} EUR"

    def test_three_decimal_currency_precision(self, currency_agent):
        """
        TC-EDGE-014: Three-decimal currency precision handling.

        ARRANGE:
        - Convert to three-decimal currency (KWD)
        - Amount creates complex decimal

        ACT:
        - Convert EUR 99.99 → KWD

        ASSERT:
        - Result has max 3 decimal places
        - Fils (0.001 KWD) precision maintained
        """
        # ARRANGE
        amount = Decimal("99.99")

        # ACT
        result, fx_rate = currency_agent.convert_amount(
            amount=amount,
            from_currency=CurrencyCode.EUR,
            to_currency=CurrencyCode.KWD,
            round_before_conversion=False
        )

        # ASSERT
        # 99.99 * 0.3345 = 33.44655 → 33.447 KWD
        expected = Decimal("33.447")
        assert result == expected

        # Verify max 3 decimal places
        amount_str = str(result)
        if '.' in amount_str:
            decimal_places = len(amount_str.split('.')[1].rstrip('0'))
            assert decimal_places <= 3

    @pytest.mark.parametrize("currency,min_amount,max_amount", [
        (CurrencyCode.EUR, Decimal("0.01"), Decimal("999999.99")),
        (CurrencyCode.JPY, Decimal("1"), Decimal("9999999")),
        (CurrencyCode.KWD, Decimal("0.001"), Decimal("999999.999")),
        (CurrencyCode.CLP, Decimal("1"), Decimal("999999999")),
    ])
    def test_boundary_values_for_all_currencies(
        self,
        currency_agent,
        currency,
        min_amount,
        max_amount
    ):
        """
        TC-EDGE-015: Test boundary values for each currency type.

        Tests minimum and maximum amounts for different currency types.
        """
        # Test minimum (should be valid)
        is_valid, error = currency_agent.validate_amount_for_currency(
            min_amount, currency
        )
        assert is_valid, f"Minimum {min_amount} should be valid for {currency}"

        # Test below minimum (should be invalid)
        below_min = min_amount / Decimal("2")
        is_valid, error = currency_agent.validate_amount_for_currency(
            below_min, currency
        )
        assert not is_valid, f"Below minimum should be invalid for {currency}"

        # Test maximum (should be valid)
        is_valid, error = currency_agent.validate_amount_for_currency(
            max_amount, currency
        )
        assert is_valid, f"Maximum {max_amount} should be valid for {currency}"

        # Test above maximum (should be invalid)
        above_max = max_amount + Decimal("1")
        is_valid, error = currency_agent.validate_amount_for_currency(
            above_max, currency
        )
        assert not is_valid, f"Above maximum should be invalid for {currency}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
