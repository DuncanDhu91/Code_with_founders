"""Multi-Currency Checkout Integration Tests

Core Requirement 1: Verify authorization amount correctness across 5+ currency pairs.

This test suite covers:
- EUR → CLP (the €2.3M incident scenario)
- USD → BRL
- GBP → JPY
- BRL → EUR (reversed direction)
- EUR → KWD (3-decimal currency)

Each test verifies:
- Authorization amount matches expected conversion
- No rounding-before-conversion (the bug!)
- Correct decimal precision for currency type
- Webhook payload has correct amounts
"""

import pytest
from decimal import Decimal

from framework.agents.currency_agent import CurrencyAgent
from framework.agents.payment_agent import PaymentAgent
from framework.models.currency import CurrencyCode, get_currency
from framework.models.transaction import (
    AuthorizationRequest,
    AuthorizationResponse,
    PaymentMethod,
    TransactionStatus
)


class TestMultiCurrencyCheckout:
    """Integration tests for multi-currency authorization flow."""

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

    def test_eur_to_clp_authorization_incident_scenario(self, payment_agent):
        """
        TC-AUTH-001: EUR → CLP Authorization (The €2.3M Bug Case)

        ARRANGE:
        - Customer sees €49.99 EUR
        - Merchant settles in CLP
        - FX rate: 1052.00

        ACT:
        - Submit authorization request

        ASSERT:
        - Authorized amount: CLP 52,595 (NOT 52,600)
        - FX rate stored correctly
        - Webhook contains correct amount
        """
        # ARRANGE
        request = AuthorizationRequest(
            merchant_id="merchant_chile_001",
            customer_id="customer_eu_001",
            amount=Decimal("49.99"),
            currency=CurrencyCode.EUR,
            settlement_currency=CurrencyCode.CLP,
            payment_method=PaymentMethod.CARD,
            idempotency_key="test_eur_clp_001"
        )

        # ACT
        response = payment_agent.authorize_payment(request)

        # ASSERT: Authorization succeeded
        assert response.status == TransactionStatus.AUTHORIZED
        assert response.transaction_id is not None

        # ASSERT: Correct authorized amount (THE CRITICAL ASSERTION)
        assert response.authorized_amount == Decimal("52595"), \
            f"Expected CLP 52,595, got {response.authorized_amount}. " \
            "Bug detected: rounding happened BEFORE conversion!"

        # ASSERT: Currency details
        assert response.authorized_currency == CurrencyCode.CLP
        assert response.settlement_amount == Decimal("52595")
        assert response.settlement_currency == CurrencyCode.CLP
        assert response.fx_rate == Decimal("1052.00")

        # ASSERT: No error
        assert response.error_code is None
        assert response.message == "Authorization successful"

        # ASSERT: Transaction record
        transaction = payment_agent.get_transaction(response.transaction_id)
        assert transaction is not None
        assert transaction.original_amount == Decimal("49.99")
        assert transaction.original_currency == CurrencyCode.EUR
        assert transaction.settlement_amount == Decimal("52595")
        assert transaction.settlement_currency == CurrencyCode.CLP
        assert transaction.fx_rate == Decimal("1052.00")
        assert transaction.fx_rate_timestamp is not None

        # ASSERT: Webhook
        webhooks = payment_agent.get_webhooks_for_merchant("merchant_chile_001")
        assert len(webhooks) == 1
        webhook = webhooks[0]
        assert webhook.event_type == "payment.authorized"
        assert webhook.transaction_id == response.transaction_id
        assert webhook.status == TransactionStatus.AUTHORIZED
        assert webhook.amount == Decimal("52595")
        assert webhook.currency == CurrencyCode.CLP
        assert webhook.metadata["fx_rate"] == "1052.00"

    def test_usd_to_brl_authorization(self, payment_agent):
        """
        TC-AUTH-002: USD → BRL Authorization

        ARRANGE:
        - Customer pays $100.00 USD
        - Merchant settles in BRL
        - FX rate: 4.9545

        ACT:
        - Submit authorization

        ASSERT:
        - Authorized amount: R$ 495.45 BRL
        - Both currencies have 2 decimal places
        """
        # ARRANGE
        request = AuthorizationRequest(
            merchant_id="merchant_brazil_001",
            customer_id="customer_us_001",
            amount=Decimal("100.00"),
            currency=CurrencyCode.USD,
            settlement_currency=CurrencyCode.BRL,
            payment_method=PaymentMethod.CARD,
            idempotency_key="test_usd_brl_001"
        )

        # ACT
        response = payment_agent.authorize_payment(request)

        # ASSERT
        assert response.status == TransactionStatus.AUTHORIZED
        assert response.authorized_amount == Decimal("495.45")
        assert response.authorized_currency == CurrencyCode.BRL
        assert response.fx_rate == Decimal("4.9545")

        # Verify 2 decimal places
        amount_str = str(response.authorized_amount)
        if '.' in amount_str:
            decimal_places = len(amount_str.split('.')[1])
            assert decimal_places <= 2

    def test_gbp_to_jpy_authorization_zero_decimal(self, payment_agent):
        """
        TC-AUTH-003: GBP → JPY Authorization (Zero-Decimal Target)

        ARRANGE:
        - Customer pays £100.00 GBP
        - Merchant settles in JPY (zero-decimal)
        - FX rate: 186.45

        ACT:
        - Submit authorization

        ASSERT:
        - Authorized amount: ¥18,645 JPY (whole number)
        - No decimal places in result
        """
        # ARRANGE
        request = AuthorizationRequest(
            merchant_id="merchant_japan_001",
            customer_id="customer_uk_001",
            amount=Decimal("100.00"),
            currency=CurrencyCode.GBP,
            settlement_currency=CurrencyCode.JPY,
            payment_method=PaymentMethod.CARD,
            idempotency_key="test_gbp_jpy_001"
        )

        # ACT
        response = payment_agent.authorize_payment(request)

        # ASSERT
        assert response.status == TransactionStatus.AUTHORIZED
        assert response.authorized_amount == Decimal("18645")
        assert response.authorized_currency == CurrencyCode.JPY

        # CRITICAL: Verify no decimal places (zero-decimal currency)
        assert response.authorized_amount % 1 == 0, \
            "JPY amount must be whole number (zero decimals)"

    def test_brl_to_eur_authorization_reverse_direction(self, payment_agent):
        """
        TC-AUTH-004: BRL → EUR Authorization (Reverse Direction)

        ARRANGE:
        - Customer pays R$ 500.00 BRL
        - Merchant settles in EUR
        - FX rate: 0.1860 (BRL to EUR)

        ACT:
        - Submit authorization

        ASSERT:
        - Authorized amount: €93.00 EUR
        - Reverse conversion works correctly
        """
        # ARRANGE
        request = AuthorizationRequest(
            merchant_id="merchant_eu_001",
            customer_id="customer_brazil_001",
            amount=Decimal("500.00"),
            currency=CurrencyCode.BRL,
            settlement_currency=CurrencyCode.EUR,
            payment_method=PaymentMethod.CARD,
            idempotency_key="test_brl_eur_001"
        )

        # ACT
        response = payment_agent.authorize_payment(request)

        # ASSERT
        assert response.status == TransactionStatus.AUTHORIZED
        assert response.authorized_amount == Decimal("93.00")
        assert response.authorized_currency == CurrencyCode.EUR
        assert response.fx_rate == Decimal("0.1860")

    def test_eur_to_kwd_authorization_three_decimal(self, payment_agent):
        """
        TC-AUTH-005: EUR → KWD Authorization (Three-Decimal Currency)

        ARRANGE:
        - Customer pays €100.00 EUR
        - Merchant settles in KWD (three-decimal)
        - FX rate: 0.3345

        ACT:
        - Submit authorization

        ASSERT:
        - Authorized amount: KD 33.450 (3 decimal places)
        - Correct fils (smallest KWD unit)
        """
        # ARRANGE
        request = AuthorizationRequest(
            merchant_id="merchant_kuwait_001",
            customer_id="customer_eu_001",
            amount=Decimal("100.00"),
            currency=CurrencyCode.EUR,
            settlement_currency=CurrencyCode.KWD,
            payment_method=PaymentMethod.CARD,
            idempotency_key="test_eur_kwd_001"
        )

        # ACT
        response = payment_agent.authorize_payment(request)

        # ASSERT
        assert response.status == TransactionStatus.AUTHORIZED
        assert response.authorized_amount == Decimal("33.450")
        assert response.authorized_currency == CurrencyCode.KWD

        # Verify 3 decimal places maximum
        amount_str = str(response.authorized_amount)
        if '.' in amount_str:
            decimal_places = len(amount_str.split('.')[1].rstrip('0'))
            assert decimal_places <= 3, \
                f"KWD should have max 3 decimal places, got {decimal_places}"

    def test_eur_to_cop_authorization_high_rate(self, payment_agent):
        """
        TC-AUTH-006: EUR → COP Authorization (High FX Rate)

        ARRANGE:
        - Customer pays €50.00 EUR
        - Merchant settles in COP (Colombian Peso)
        - FX rate: 4250.00 (high rate)

        ACT:
        - Submit authorization

        ASSERT:
        - Authorized amount: COL$ 212,500 COP
        - Large conversion doesn't overflow
        """
        # ARRANGE
        request = AuthorizationRequest(
            merchant_id="merchant_colombia_001",
            customer_id="customer_eu_001",
            amount=Decimal("50.00"),
            currency=CurrencyCode.EUR,
            settlement_currency=CurrencyCode.COP,
            payment_method=PaymentMethod.CARD,
            idempotency_key="test_eur_cop_001"
        )

        # ACT
        response = payment_agent.authorize_payment(request)

        # ASSERT
        assert response.status == TransactionStatus.AUTHORIZED
        assert response.authorized_amount == Decimal("212500")
        assert response.authorized_currency == CurrencyCode.COP
        assert response.fx_rate == Decimal("4250.00")

        # Verify no decimal places (COP is zero-decimal)
        assert response.authorized_amount % 1 == 0

    @pytest.mark.parametrize("from_currency,to_currency,amount,expected_amount", [
        (CurrencyCode.EUR, CurrencyCode.CLP, Decimal("49.99"), Decimal("52595")),
        (CurrencyCode.EUR, CurrencyCode.JPY, Decimal("100.00"), Decimal("16125")),
        (CurrencyCode.USD, CurrencyCode.KRW, Decimal("50.00"), Decimal("66608")),
        (CurrencyCode.GBP, CurrencyCode.CLP, Decimal("75.50"), Decimal("91846")),
        (CurrencyCode.EUR, CurrencyCode.USD, Decimal("100.00"), Decimal("108.50")),
        (CurrencyCode.EUR, CurrencyCode.KWD, Decimal("100.00"), Decimal("33.450")),
    ], ids=[
        "eur_clp_incident",
        "eur_jpy_zero_decimal",
        "usd_krw_zero_decimal",
        "gbp_clp_zero_decimal",
        "eur_usd_same_decimal",
        "eur_kwd_three_decimal"
    ])
    def test_parametrized_currency_conversions(
        self,
        payment_agent,
        from_currency,
        to_currency,
        amount,
        expected_amount
    ):
        """
        TC-AUTH-007: Parametrized test for multiple currency pairs.

        Tests 6+ currency pairs with a single test function.
        """
        # ARRANGE
        request = AuthorizationRequest(
            merchant_id="merchant_test_001",
            customer_id="customer_test_001",
            amount=amount,
            currency=from_currency,
            settlement_currency=to_currency,
            payment_method=PaymentMethod.CARD,
            idempotency_key=f"test_{from_currency}_{to_currency}"
        )

        # ACT
        response = payment_agent.authorize_payment(request)

        # ASSERT
        assert response.status == TransactionStatus.AUTHORIZED, \
            f"Authorization failed for {from_currency} → {to_currency}"

        assert response.authorized_amount == expected_amount, \
            f"{from_currency} → {to_currency}: expected {expected_amount}, " \
            f"got {response.authorized_amount}"

        # Verify decimal places match target currency
        to_config = get_currency(to_currency)
        if to_config.decimal_places == 0:
            assert response.authorized_amount % 1 == 0, \
                f"{to_currency} must have zero decimal places"

    def test_same_currency_no_conversion(self, payment_agent):
        """
        TC-AUTH-008: Same currency (no conversion needed).

        ARRANGE:
        - Customer pays EUR, merchant settles EUR
        - No conversion needed

        ACT:
        - Submit authorization

        ASSERT:
        - Amount unchanged
        - FX rate = 1.0
        - No settlement currency in response
        """
        # ARRANGE
        request = AuthorizationRequest(
            merchant_id="merchant_eu_001",
            customer_id="customer_eu_001",
            amount=Decimal("100.00"),
            currency=CurrencyCode.EUR,
            settlement_currency=CurrencyCode.EUR,
            payment_method=PaymentMethod.CARD,
            idempotency_key="test_eur_eur_001"
        )

        # ACT
        response = payment_agent.authorize_payment(request)

        # ASSERT
        assert response.status == TransactionStatus.AUTHORIZED
        assert response.authorized_amount == Decimal("100.00")
        assert response.authorized_currency == CurrencyCode.EUR

        # No conversion happened
        assert response.fx_rate is None or response.fx_rate == Decimal("1.0")
        assert response.settlement_amount is None

    def test_webhook_contains_all_required_fields(self, payment_agent):
        """
        TC-AUTH-009: Verify webhook payload completeness.

        ARRANGE:
        - Process a multi-currency authorization

        ACT:
        - Retrieve webhook

        ASSERT:
        - All required fields present
        - FX rate included in metadata
        - Timestamp present
        """
        # ARRANGE
        request = AuthorizationRequest(
            merchant_id="merchant_test_webhook",
            customer_id="customer_001",
            amount=Decimal("49.99"),
            currency=CurrencyCode.EUR,
            settlement_currency=CurrencyCode.CLP,
            payment_method=PaymentMethod.CARD,
            idempotency_key="test_webhook_001",
            metadata={"order_id": "ORDER-12345"}
        )

        # ACT
        response = payment_agent.authorize_payment(request)
        webhooks = payment_agent.get_webhooks_for_merchant("merchant_test_webhook")

        # ASSERT
        assert len(webhooks) == 1
        webhook = webhooks[0]

        # Required fields
        assert webhook.event_type == "payment.authorized"
        assert webhook.transaction_id == response.transaction_id
        assert webhook.status == TransactionStatus.AUTHORIZED
        assert webhook.amount == Decimal("52595")
        assert webhook.currency == CurrencyCode.CLP
        assert webhook.settlement_amount == Decimal("52595")
        assert webhook.settlement_currency == CurrencyCode.CLP
        assert webhook.timestamp is not None

        # Metadata
        assert "merchant_id" in webhook.metadata
        assert "customer_id" in webhook.metadata
        assert webhook.metadata["fx_rate"] == "1052.00"

    def test_transaction_record_completeness(self, payment_agent):
        """
        TC-AUTH-010: Verify transaction record has all fields.

        ARRANGE:
        - Process authorization

        ACT:
        - Retrieve transaction record

        ASSERT:
        - All fields populated
        - FX rate timestamp set
        - Metadata preserved
        """
        # ARRANGE
        request = AuthorizationRequest(
            merchant_id="merchant_001",
            customer_id="customer_001",
            amount=Decimal("49.99"),
            currency=CurrencyCode.EUR,
            settlement_currency=CurrencyCode.CLP,
            payment_method=PaymentMethod.CARD,
            idempotency_key="test_txn_record_001",
            metadata={"order_id": "ORDER-12345", "source": "test"}
        )

        # ACT
        response = payment_agent.authorize_payment(request)
        transaction = payment_agent.get_transaction(response.transaction_id)

        # ASSERT
        assert transaction is not None
        assert transaction.transaction_id == response.transaction_id
        assert transaction.merchant_id == "merchant_001"
        assert transaction.customer_id == "customer_001"
        assert transaction.original_amount == Decimal("49.99")
        assert transaction.original_currency == CurrencyCode.EUR
        assert transaction.settlement_amount == Decimal("52595")
        assert transaction.settlement_currency == CurrencyCode.CLP
        assert transaction.authorized_amount == Decimal("52595")
        assert transaction.fx_rate == Decimal("1052.00")
        assert transaction.fx_rate_timestamp is not None
        assert transaction.status == TransactionStatus.AUTHORIZED
        assert transaction.payment_method == PaymentMethod.CARD
        assert transaction.created_at is not None
        assert transaction.metadata["order_id"] == "ORDER-12345"
        assert transaction.metadata["source"] == "test"

    def test_multiple_authorizations_independent(self, payment_agent):
        """
        TC-AUTH-011: Verify multiple authorizations are independent.

        ARRANGE:
        - Process 3 authorizations with different amounts

        ACT:
        - Submit all 3

        ASSERT:
        - All succeed
        - Transaction IDs are unique
        - Amounts are correct
        - No cross-contamination
        """
        # ARRANGE
        requests = [
            AuthorizationRequest(
                merchant_id="merchant_001",
                customer_id="customer_001",
                amount=Decimal("49.99"),
                currency=CurrencyCode.EUR,
                settlement_currency=CurrencyCode.CLP,
                payment_method=PaymentMethod.CARD,
                idempotency_key=f"test_multi_001"
            ),
            AuthorizationRequest(
                merchant_id="merchant_001",
                customer_id="customer_002",
                amount=Decimal("100.00"),
                currency=CurrencyCode.EUR,
                settlement_currency=CurrencyCode.JPY,
                payment_method=PaymentMethod.CARD,
                idempotency_key=f"test_multi_002"
            ),
            AuthorizationRequest(
                merchant_id="merchant_001",
                customer_id="customer_003",
                amount=Decimal("75.50"),
                currency=CurrencyCode.GBP,
                settlement_currency=CurrencyCode.CLP,
                payment_method=PaymentMethod.CARD,
                idempotency_key=f"test_multi_003"
            )
        ]

        # ACT
        responses = [payment_agent.authorize_payment(req) for req in requests]

        # ASSERT: All succeeded
        assert all(r.status == TransactionStatus.AUTHORIZED for r in responses)

        # ASSERT: Unique transaction IDs
        txn_ids = [r.transaction_id for r in responses]
        assert len(txn_ids) == len(set(txn_ids)), "Transaction IDs must be unique"

        # ASSERT: Correct amounts
        assert responses[0].authorized_amount == Decimal("52595")
        assert responses[1].authorized_amount == Decimal("16125")
        assert responses[2].authorized_amount == Decimal("91846")

        # ASSERT: No cross-contamination in webhooks
        webhooks = payment_agent.get_webhooks_for_merchant("merchant_001")
        assert len(webhooks) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
