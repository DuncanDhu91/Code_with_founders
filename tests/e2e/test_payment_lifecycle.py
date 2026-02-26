"""End-to-End Payment Lifecycle Tests.

Tests complete payment flows from authorization through settlement.

Test Coverage:
- Authorization → Capture → Settlement currency consistency
- Currency data preserved across payment lifecycle
- Customer receipt shows correct display amount
- Merchant dashboard shows correct settlement amount
- Refund flow calculates correct amount in original currency

Edge Cases Covered:
- Complete cross-border payment flow
- Multi-stage currency consistency
- Customer vs merchant view reconciliation
- FX rate locking throughout lifecycle
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, Any

from framework.agents.currency_agent import CurrencyAgent
from framework.agents.payment_agent import PaymentAgent
from framework.models.currency import CurrencyCode, get_currency
from framework.models.transaction import (
    AuthorizationRequest,
    TransactionStatus,
    PaymentMethod,
    Transaction
)
from tests.utils.webhook_test_helpers import (
    WebhookCollector,
    wait_for_webhook,
    assert_webhook_payload
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def currency_agent():
    """Provide fresh CurrencyAgent."""
    return CurrencyAgent()


@pytest.fixture
def payment_agent(currency_agent):
    """Provide fresh PaymentAgent."""
    return PaymentAgent(currency_agent=currency_agent, simulate_bug=False)


@pytest.fixture
def webhook_collector(payment_agent):
    """Provide WebhookCollector with webhook interception."""
    collector = WebhookCollector()

    original_generate = payment_agent._generate_webhook

    def patched_generate(transaction):
        original_generate(transaction)
        webhooks = payment_agent.get_webhooks_for_merchant(transaction.merchant_id)
        if webhooks:
            collector.add(webhooks[-1])

    payment_agent._generate_webhook = patched_generate

    yield collector
    collector.clear()


# ============================================================================
# TC-E2E-001: Complete Cross-Border Payment Flow
# ============================================================================

@pytest.mark.asyncio
async def test_complete_cross_border_payment_eur_to_clp(
    payment_agent,
    currency_agent,
    webhook_collector
):
    """
    TC-E2E-001: Verify complete cross-border payment lifecycle.

    ARRANGE:
    - Customer in Europe (views price in EUR)
    - Merchant in Chile (settles in CLP)
    - Product: €49.99 EUR
    - FX rate: 1 EUR = 1052 CLP

    ACT:
    - Step 1: Customer authorizes payment
    - Step 2: System converts EUR → CLP
    - Step 3: Authorization response generated
    - Step 4: Webhook emitted
    - Step 5: Transaction stored

    ASSERT:
    - Authorization successful
    - Amount converted correctly (CLP 52,595, not 52,600)
    - Transaction record complete
    - Webhook contains all data
    - Customer sees EUR 49.99
    - Merchant receives CLP 52,595
    """
    # ARRANGE
    customer_sees_amount = Decimal("49.99")
    customer_currency = CurrencyCode.EUR
    merchant_settlement_currency = CurrencyCode.CLP
    expected_settlement_amount = Decimal("52595")

    request = AuthorizationRequest(
        merchant_id="merchant_chile_cross_border",
        customer_id="customer_eu_cross_border",
        amount=customer_sees_amount,
        currency=customer_currency,
        settlement_currency=merchant_settlement_currency,
        payment_method=PaymentMethod.CARD,
        idempotency_key="test_e2e_cross_border_001",
        metadata={
            "order_id": "ORDER-XB-12345",
            "product_name": "Premium Widget",
            "customer_ip": "203.0.113.45"
        }
    )

    # ACT - Step 1: Authorize payment
    response = payment_agent.authorize_payment(request)

    # ASSERT - Step 1: Authorization response
    assert response.status == TransactionStatus.AUTHORIZED, (
        f"Authorization failed: {response.message}"
    )
    assert response.transaction_id is not None
    assert response.authorized_amount == expected_settlement_amount, (
        f"Authorized amount should be CLP 52,595, got {response.authorized_amount}"
    )
    assert response.authorized_currency == merchant_settlement_currency
    assert response.fx_rate == Decimal("1052.00")

    # ASSERT - Step 2: Transaction record
    transaction = payment_agent.get_transaction(response.transaction_id)
    assert transaction is not None, "Transaction not found"

    # Verify transaction data completeness
    assert transaction.transaction_id == response.transaction_id
    assert transaction.merchant_id == "merchant_chile_cross_border"
    assert transaction.customer_id == "customer_eu_cross_border"
    assert transaction.status == TransactionStatus.AUTHORIZED

    # Verify currency data
    assert transaction.original_amount == customer_sees_amount
    assert transaction.original_currency == customer_currency
    assert transaction.settlement_amount == expected_settlement_amount
    assert transaction.settlement_currency == merchant_settlement_currency
    assert transaction.authorized_amount == expected_settlement_amount

    # Verify FX data
    assert transaction.fx_rate == Decimal("1052.00")
    assert transaction.fx_rate_timestamp is not None

    # Verify FX timestamp is recent (within last minute)
    fx_age = datetime.utcnow() - transaction.fx_rate_timestamp
    assert fx_age < timedelta(minutes=1), (
        f"FX rate timestamp too old: {fx_age}"
    )

    # Verify metadata preserved
    assert transaction.metadata["order_id"] == "ORDER-XB-12345"

    # ASSERT - Step 3: Webhook delivery
    webhook = await wait_for_webhook(
        webhook_collector,
        transaction_id=response.transaction_id,
        expected_status=TransactionStatus.AUTHORIZED,
        timeout_seconds=5.0
    )

    assert_webhook_payload(
        webhook,
        expected_transaction_id=response.transaction_id,
        expected_status=TransactionStatus.AUTHORIZED,
        expected_amount=expected_settlement_amount,
        expected_currency=merchant_settlement_currency,
        expected_settlement_amount=expected_settlement_amount,
        expected_settlement_currency=merchant_settlement_currency,
        expected_fx_rate=Decimal("1052.00"),
        context="Cross-border EUR→CLP payment"
    )

    # ASSERT - Step 4: Customer view
    # Customer sees: EUR 49.99 charged
    customer_view = {
        "amount": transaction.original_amount,
        "currency": transaction.original_currency,
        "display": currency_agent.format_amount_for_display(
            transaction.original_amount,
            transaction.original_currency
        )
    }
    assert customer_view["amount"] == Decimal("49.99")
    assert customer_view["currency"] == CurrencyCode.EUR
    assert "49.99" in customer_view["display"]

    # ASSERT - Step 5: Merchant view
    # Merchant sees: CLP 52,595 settlement
    merchant_view = {
        "amount": transaction.settlement_amount,
        "currency": transaction.settlement_currency,
        "display": currency_agent.format_amount_for_display(
            transaction.settlement_amount,
            transaction.settlement_currency
        )
    }
    assert merchant_view["amount"] == Decimal("52595")
    assert merchant_view["currency"] == CurrencyCode.CLP
    assert "52595" in merchant_view["display"] or "52,595" in merchant_view["display"]

    # ASSERT - Final verification: Bug not present
    # If bug were present, settlement would be CLP 52,600
    assert transaction.settlement_amount < Decimal("52600"), (
        "Bug detected: amount suggests rounding happened BEFORE conversion"
    )


# ============================================================================
# TC-E2E-002: Currency Consistency Across Lifecycle
# ============================================================================

@pytest.mark.asyncio
async def test_currency_consistency_authorization_to_settlement(
    payment_agent,
    webhook_collector
):
    """
    TC-E2E-002: Verify currency data preserved throughout lifecycle.

    ARRANGE:
    - Multi-stage payment flow
    - Authorization → (Future: Capture) → Settlement

    ACT:
    - Authorize payment
    - Verify data at each stage

    ASSERT:
    - Original amount immutable
    - Settlement amount consistent
    - FX rate locked at authorization
    - All records show same data
    """
    # ARRANGE
    request = AuthorizationRequest(
        merchant_id="merchant_001",
        customer_id="customer_001",
        amount=Decimal("100.00"),
        currency=CurrencyCode.USD,
        settlement_currency=CurrencyCode.JPY,
        payment_method=PaymentMethod.CARD,
        idempotency_key="test_e2e_consistency_001"
    )

    # ACT - Stage 1: Authorization
    auth_response = payment_agent.authorize_payment(request)
    auth_transaction = payment_agent.get_transaction(auth_response.transaction_id)

    # Wait for webhook
    auth_webhook = await wait_for_webhook(
        webhook_collector,
        auth_response.transaction_id,
        TransactionStatus.AUTHORIZED
    )

    # ASSERT - Stage 1: Authorization data
    stage1_data = {
        "original_amount": auth_transaction.original_amount,
        "original_currency": auth_transaction.original_currency,
        "settlement_amount": auth_transaction.settlement_amount,
        "settlement_currency": auth_transaction.settlement_currency,
        "fx_rate": auth_transaction.fx_rate,
    }

    # Store for comparison with future stages
    original_snapshot = stage1_data.copy()

    # ASSERT - Verify authorization stage correctness
    assert stage1_data["original_amount"] == Decimal("100.00")
    assert stage1_data["original_currency"] == CurrencyCode.USD
    assert stage1_data["settlement_amount"] == Decimal("14865")  # USD 100 * 148.65
    assert stage1_data["settlement_currency"] == CurrencyCode.JPY
    assert stage1_data["fx_rate"] == Decimal("148.65")

    # ASSERT - Webhook matches transaction
    assert auth_webhook.amount == stage1_data["settlement_amount"]
    assert auth_webhook.currency == stage1_data["settlement_currency"]
    assert auth_webhook.metadata["fx_rate"] == str(stage1_data["fx_rate"])

    # ACT - Stage 2: Simulate rate change (should NOT affect this transaction)
    payment_agent.currency_agent.fx_rates["USD_JPY"] = Decimal("150.00")

    # Re-fetch transaction
    stage2_transaction = payment_agent.get_transaction(auth_response.transaction_id)

    # ASSERT - Stage 2: Data unchanged
    stage2_data = {
        "original_amount": stage2_transaction.original_amount,
        "original_currency": stage2_transaction.original_currency,
        "settlement_amount": stage2_transaction.settlement_amount,
        "settlement_currency": stage2_transaction.settlement_currency,
        "fx_rate": stage2_transaction.fx_rate,
    }

    # Verify immutability
    assert stage2_data == original_snapshot, (
        "Transaction data changed after FX rate update. "
        "Data should be immutable after authorization."
    )

    # ASSERT - Final: All stages consistent
    assert stage1_data == stage2_data, "Currency data not consistent across lifecycle"


# ============================================================================
# TC-E2E-003: Customer Receipt Validation
# ============================================================================

def test_customer_receipt_shows_correct_display_amount(payment_agent, currency_agent):
    """
    TC-E2E-003: Verify customer receipt shows original amount.

    ARRANGE:
    - Cross-border transaction
    - Customer pays in EUR
    - Merchant settles in CLP

    ACT:
    - Generate customer receipt

    ASSERT:
    - Receipt shows EUR 49.99 (customer's view)
    - Receipt includes currency symbol
    - Receipt does NOT show settlement amount
    - Receipt format matches currency conventions
    """
    # ARRANGE
    request = AuthorizationRequest(
        merchant_id="merchant_001",
        customer_id="customer_001",
        amount=Decimal("49.99"),
        currency=CurrencyCode.EUR,
        settlement_currency=CurrencyCode.CLP,
        payment_method=PaymentMethod.CARD,
        idempotency_key="test_customer_receipt_001"
    )

    # ACT
    response = payment_agent.authorize_payment(request)
    transaction = payment_agent.get_transaction(response.transaction_id)

    # Generate customer receipt data
    customer_receipt = generate_customer_receipt(transaction, currency_agent)

    # ASSERT
    assert customer_receipt["charged_amount"] == Decimal("49.99")
    assert customer_receipt["charged_currency"] == "EUR"
    assert customer_receipt["display_amount"] == "€49.99"

    # Should NOT include settlement info
    assert "settlement" not in customer_receipt or customer_receipt.get("settlement_amount") is None

    # Receipt should be human-readable
    assert "€" in customer_receipt["display_amount"], "Missing currency symbol"
    assert "49.99" in customer_receipt["display_amount"], "Missing amount"


def generate_customer_receipt(transaction: Transaction, currency_agent: CurrencyAgent) -> Dict[str, Any]:
    """Helper to generate customer receipt data."""
    return {
        "transaction_id": transaction.transaction_id,
        "charged_amount": transaction.original_amount,
        "charged_currency": transaction.original_currency.value,
        "display_amount": currency_agent.format_amount_for_display(
            transaction.original_amount,
            transaction.original_currency
        ),
        "status": transaction.status.value,
        "timestamp": transaction.created_at,
    }


# ============================================================================
# TC-E2E-004: Merchant Dashboard Settlement View
# ============================================================================

def test_merchant_dashboard_shows_correct_settlement_amount(payment_agent, currency_agent):
    """
    TC-E2E-004: Verify merchant dashboard shows settlement amount.

    ARRANGE:
    - Cross-border transaction
    - Customer pays EUR, merchant settles CLP

    ACT:
    - Generate merchant settlement report

    ASSERT:
    - Dashboard shows CLP 52,595 (merchant's view)
    - Dashboard includes FX rate
    - Dashboard shows both original and settlement
    - Settlement total calculated correctly
    """
    # ARRANGE
    request = AuthorizationRequest(
        merchant_id="merchant_dashboard_001",
        customer_id="customer_001",
        amount=Decimal("49.99"),
        currency=CurrencyCode.EUR,
        settlement_currency=CurrencyCode.CLP,
        payment_method=PaymentMethod.CARD,
        idempotency_key="test_merchant_dashboard_001"
    )

    # ACT
    response = payment_agent.authorize_payment(request)
    transaction = payment_agent.get_transaction(response.transaction_id)

    # Generate merchant dashboard data
    merchant_dashboard = generate_merchant_dashboard_entry(transaction, currency_agent)

    # ASSERT
    assert merchant_dashboard["settlement_amount"] == Decimal("52595")
    assert merchant_dashboard["settlement_currency"] == "CLP"
    assert merchant_dashboard["settlement_display"] == "CLP$52595"

    # Should include original amount for reference
    assert merchant_dashboard["customer_charged_amount"] == Decimal("49.99")
    assert merchant_dashboard["customer_charged_currency"] == "EUR"

    # Should include FX rate
    assert merchant_dashboard["fx_rate"] == Decimal("1052.00")

    # Should show merchant receives CLP
    assert "CLP" in merchant_dashboard["settlement_display"]


def generate_merchant_dashboard_entry(transaction: Transaction, currency_agent: CurrencyAgent) -> Dict[str, Any]:
    """Helper to generate merchant dashboard entry."""
    return {
        "transaction_id": transaction.transaction_id,
        "customer_charged_amount": transaction.original_amount,
        "customer_charged_currency": transaction.original_currency.value,
        "settlement_amount": transaction.settlement_amount,
        "settlement_currency": transaction.settlement_currency.value,
        "settlement_display": currency_agent.format_amount_for_display(
            transaction.settlement_amount,
            transaction.settlement_currency
        ),
        "fx_rate": transaction.fx_rate,
        "status": transaction.status.value,
        "timestamp": transaction.created_at,
    }


# ============================================================================
# TC-E2E-005: Refund Flow Currency Calculation
# ============================================================================

def test_refund_flow_calculates_correct_amount_in_original_currency(
    payment_agent,
    currency_agent
):
    """
    TC-E2E-005: Verify refund calculates correct amount in original currency.

    ARRANGE:
    - Original payment: EUR 49.99 → CLP 52,595
    - FX rate at auth: 1052
    - FX rate changes to 1055
    - Full refund requested

    ACT:
    - Calculate refund amount

    ASSERT:
    - Refund uses ORIGINAL FX rate (1052)
    - Customer receives EUR 49.99 back (or EUR 50.00 with rounding)
    - Refund amount documented
    - No profit/loss from FX rate change
    """
    # ARRANGE - Original payment
    original_request = AuthorizationRequest(
        merchant_id="merchant_001",
        customer_id="customer_001",
        amount=Decimal("49.99"),
        currency=CurrencyCode.EUR,
        settlement_currency=CurrencyCode.CLP,
        payment_method=PaymentMethod.CARD,
        idempotency_key="test_refund_flow_001"
    )

    auth_response = payment_agent.authorize_payment(original_request)
    original_transaction = payment_agent.get_transaction(auth_response.transaction_id)

    # Store original state
    original_eur_amount = original_transaction.original_amount
    original_clp_amount = original_transaction.settlement_amount
    original_fx_rate = original_transaction.fx_rate

    # Simulate FX rate change
    currency_agent.fx_rates["EUR_CLP"] = Decimal("1055.00")

    # ACT - Calculate refund using ORIGINAL rate
    # In production, this would be stored with the transaction
    refund_eur_amount = original_clp_amount / original_fx_rate

    # Round to EUR precision
    eur_config = get_currency(CurrencyCode.EUR)
    refund_eur_rounded = eur_config.round_amount(refund_eur_amount)

    # ASSERT - Refund calculation
    # CLP 52,595 / 1052 = EUR 50.0133... → EUR 50.01

    assert refund_eur_rounded == Decimal("50.01"), (
        f"Refund should be EUR 50.01, got {refund_eur_rounded}"
    )

    # Customer paid EUR 49.99, receives EUR 50.01
    # Rounding in customer's favor (acceptable)
    refund_difference = refund_eur_rounded - original_eur_amount

    assert refund_difference == Decimal("0.02"), (
        f"Refund difference should be EUR 0.02, got {refund_difference}"
    )

    # Verify refund doesn't use NEW rate
    if_used_new_rate = original_clp_amount / Decimal("1055.00")
    if_used_new_rate_rounded = eur_config.round_amount(if_used_new_rate)

    assert refund_eur_rounded != if_used_new_rate_rounded, (
        "Refund should use ORIGINAL rate, not current rate"
    )


# ============================================================================
# TC-E2E-006: Multi-Transaction Settlement Batch
# ============================================================================

@pytest.mark.asyncio
async def test_multi_transaction_settlement_batch_end_to_end(
    payment_agent,
    webhook_collector
):
    """
    TC-E2E-006: Verify end-of-day settlement batch processing.

    ARRANGE:
    - 10 transactions throughout the day
    - Various currencies → CLP settlement
    - End of day settlement batch

    ACT:
    - Process all transactions
    - Generate settlement report

    ASSERT:
    - All transactions in batch
    - Settlement total correct
    - Each transaction has webhook
    - Batch reconciliation accurate
    """
    # ARRANGE - Create day's worth of transactions
    transactions = []
    expected_clp_total = Decimal("0")

    test_scenarios = [
        (Decimal("50.00"), CurrencyCode.EUR),
        (Decimal("60.00"), CurrencyCode.USD),
        (Decimal("45.00"), CurrencyCode.GBP),
        (Decimal("100.00"), CurrencyCode.EUR),
        (Decimal("75.00"), CurrencyCode.USD),
        (Decimal("30.00"), CurrencyCode.GBP),
        (Decimal("200.00"), CurrencyCode.BRL),
        (Decimal("150.00"), CurrencyCode.EUR),
        (Decimal("90.00"), CurrencyCode.USD),
        (Decimal("120.00"), CurrencyCode.GBP),
    ]

    # ACT - Process all transactions
    for i, (amount, currency) in enumerate(test_scenarios):
        request = AuthorizationRequest(
            merchant_id="merchant_batch_001",
            customer_id=f"customer_{i:03d}",
            amount=amount,
            currency=currency,
            settlement_currency=CurrencyCode.CLP,
            payment_method=PaymentMethod.CARD,
            idempotency_key=f"test_batch_{i}"
        )

        response = payment_agent.authorize_payment(request)
        transaction = payment_agent.get_transaction(response.transaction_id)
        transactions.append(transaction)

        expected_clp_total += transaction.settlement_amount

    # Wait for all webhooks
    webhooks = await webhook_collector.wait_for_webhooks(
        count=len(transactions),
        predicate=lambda w: w.metadata.get("merchant_id") == "merchant_batch_001",
        timeout_seconds=10.0
    )

    # ASSERT - All transactions processed
    assert len(transactions) == 10, f"Expected 10 transactions, got {len(transactions)}"

    # ASSERT - All webhooks delivered
    assert len(webhooks) == 10, f"Expected 10 webhooks, got {len(webhooks)}"

    # ASSERT - Settlement batch total
    actual_clp_total = sum(txn.settlement_amount for txn in transactions)
    assert actual_clp_total == expected_clp_total

    # ASSERT - Each transaction has settlement amount
    for txn in transactions:
        assert txn.settlement_amount is not None
        assert txn.settlement_amount > 0
        assert txn.settlement_currency == CurrencyCode.CLP

    # ASSERT - Batch reconciliation
    webhook_clp_total = sum(w.amount for w in webhooks)
    assert webhook_clp_total == actual_clp_total, (
        f"Webhook total {webhook_clp_total} != transaction total {actual_clp_total}"
    )


# ============================================================================
# TC-E2E-007: FX Rate Locking Throughout Lifecycle
# ============================================================================

def test_fx_rate_locked_at_authorization_throughout_lifecycle(payment_agent):
    """
    TC-E2E-007: Verify FX rate locked at authorization persists.

    ARRANGE:
    - Transaction authorized at specific FX rate
    - FX rate changes multiple times after authorization

    ACT:
    - Retrieve transaction at different times
    - Verify FX rate unchanged

    ASSERT:
    - FX rate immutable after authorization
    - Transaction always shows original rate
    - Rate timestamp preserved
    """
    # ARRANGE
    initial_fx_rate = payment_agent.currency_agent.fx_rates["EUR_CLP"]

    request = AuthorizationRequest(
        merchant_id="merchant_001",
        customer_id="customer_001",
        amount=Decimal("49.99"),
        currency=CurrencyCode.EUR,
        settlement_currency=CurrencyCode.CLP,
        payment_method=PaymentMethod.CARD,
        idempotency_key="test_fx_lock_001"
    )

    # ACT - Stage 1: Authorization
    response = payment_agent.authorize_payment(request)
    txn_stage1 = payment_agent.get_transaction(response.transaction_id)

    # Store initial state
    locked_fx_rate = txn_stage1.fx_rate
    locked_settlement = txn_stage1.settlement_amount
    locked_timestamp = txn_stage1.fx_rate_timestamp

    # ACT - Stage 2: FX rate changes (simulate market movement)
    payment_agent.currency_agent.fx_rates["EUR_CLP"] = Decimal("1055.00")
    txn_stage2 = payment_agent.get_transaction(response.transaction_id)

    # ACT - Stage 3: FX rate changes again
    payment_agent.currency_agent.fx_rates["EUR_CLP"] = Decimal("1060.00")
    txn_stage3 = payment_agent.get_transaction(response.transaction_id)

    # ASSERT - FX rate locked at all stages
    assert txn_stage1.fx_rate == initial_fx_rate, "Stage 1 rate mismatch"
    assert txn_stage2.fx_rate == initial_fx_rate, "Stage 2 rate changed (should be locked)"
    assert txn_stage3.fx_rate == initial_fx_rate, "Stage 3 rate changed (should be locked)"

    # ASSERT - Settlement amount unchanged
    assert txn_stage1.settlement_amount == locked_settlement
    assert txn_stage2.settlement_amount == locked_settlement
    assert txn_stage3.settlement_amount == locked_settlement

    # ASSERT - Timestamp unchanged
    assert txn_stage1.fx_rate_timestamp == locked_timestamp
    assert txn_stage2.fx_rate_timestamp == locked_timestamp
    assert txn_stage3.fx_rate_timestamp == locked_timestamp

    # ASSERT - Current market rate different
    current_market_rate = payment_agent.currency_agent.fx_rates["EUR_CLP"]
    assert locked_fx_rate != current_market_rate, (
        "Test setup error: market rate should have changed"
    )
