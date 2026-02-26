"""Currency Test Helpers

Core Requirement 3: Test utilities for reusable test logic.

This module provides:
- API client helpers for payment operations
- Assertion utilities for currency amounts
- FX rate mocking functions
- Test data factories
"""

from decimal import Decimal
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

from framework.agents.currency_agent import CurrencyAgent
from framework.agents.payment_agent import PaymentAgent
from framework.models.currency import CurrencyCode, get_currency
from framework.models.transaction import (
    AuthorizationRequest,
    AuthorizationResponse,
    PaymentMethod,
    TransactionStatus
)


# ============================================================================
# API Client Helpers
# ============================================================================

class PaymentTestClient:
    """Helper class for testing payment operations."""

    def __init__(self, simulate_bug: bool = False):
        """
        Initialize payment test client.

        Args:
            simulate_bug: If True, simulates rounding bug
        """
        self.currency_agent = CurrencyAgent()
        self.payment_agent = PaymentAgent(
            currency_agent=self.currency_agent,
            simulate_bug=simulate_bug
        )

    def authorize(
        self,
        amount: Decimal,
        currency: CurrencyCode,
        settlement_currency: Optional[CurrencyCode] = None,
        merchant_id: str = "test_merchant",
        customer_id: str = "test_customer",
        payment_method: PaymentMethod = PaymentMethod.CARD,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuthorizationResponse:
        """
        Authorize a payment.

        Args:
            amount: Payment amount
            currency: Payment currency
            settlement_currency: Settlement currency (defaults to payment currency)
            merchant_id: Merchant ID
            customer_id: Customer ID
            payment_method: Payment method
            metadata: Additional metadata

        Returns:
            Authorization response
        """
        request = AuthorizationRequest(
            merchant_id=merchant_id,
            customer_id=customer_id,
            amount=amount,
            currency=currency,
            settlement_currency=settlement_currency,
            payment_method=payment_method,
            idempotency_key=f"test_{datetime.utcnow().timestamp()}",
            metadata=metadata or {}
        )
        return self.payment_agent.authorize_payment(request)

    def get_transaction(self, transaction_id: str):
        """Get transaction by ID."""
        return self.payment_agent.get_transaction(transaction_id)

    def get_webhooks(self, merchant_id: str):
        """Get webhooks for merchant."""
        return self.payment_agent.get_webhooks_for_merchant(merchant_id)

    def reset(self):
        """Reset client state (for test isolation)."""
        self.payment_agent.reset()


# ============================================================================
# Assertion Utilities
# ============================================================================

def assert_currency_amount_equals(
    actual: Decimal,
    expected: Decimal,
    currency: CurrencyCode,
    context: str = ""
) -> None:
    """
    Assert currency amounts are equal with proper rounding.

    Args:
        actual: Actual amount
        expected: Expected amount
        currency: Currency code
        context: Additional context for error message

    Raises:
        AssertionError: If amounts don't match
    """
    config = get_currency(currency)
    rounded_actual = config.round_amount(actual)
    rounded_expected = config.round_amount(expected)

    if rounded_actual != rounded_expected:
        message = (
            f"Currency amount mismatch for {currency}:\n"
            f"  Expected: {config.format_amount(expected)} (raw: {expected})\n"
            f"  Actual:   {config.format_amount(actual)} (raw: {actual})\n"
            f"  Difference: {abs(actual - expected)}\n"
        )
        if context:
            message += f"  Context: {context}\n"
        raise AssertionError(message)


def assert_authorization_successful(
    response: AuthorizationResponse,
    expected_amount: Optional[Decimal] = None,
    expected_currency: Optional[CurrencyCode] = None
) -> None:
    """
    Assert authorization was successful.

    Args:
        response: Authorization response
        expected_amount: Expected authorized amount (optional)
        expected_currency: Expected currency (optional)

    Raises:
        AssertionError: If authorization failed or amounts don't match
    """
    assert response.status == TransactionStatus.AUTHORIZED, \
        f"Authorization failed: {response.error_code} - {response.message}"

    assert response.transaction_id is not None, \
        "Transaction ID missing"

    if expected_amount is not None:
        assert response.authorized_amount == expected_amount, \
            f"Expected amount {expected_amount}, got {response.authorized_amount}"

    if expected_currency is not None:
        assert response.authorized_currency == expected_currency, \
            f"Expected currency {expected_currency}, got {response.authorized_currency}"


def assert_authorization_failed(
    response: AuthorizationResponse,
    expected_error_code: Optional[str] = None
) -> None:
    """
    Assert authorization failed.

    Args:
        response: Authorization response
        expected_error_code: Expected error code (optional)

    Raises:
        AssertionError: If authorization succeeded or wrong error code
    """
    assert response.status == TransactionStatus.FAILED, \
        f"Expected authorization to fail, but got status {response.status}"

    assert response.error_code is not None, \
        "Error code missing in failed authorization"

    if expected_error_code is not None:
        assert response.error_code == expected_error_code, \
            f"Expected error code {expected_error_code}, got {response.error_code}"


def assert_decimal_precision(
    amount: Decimal,
    currency: CurrencyCode
) -> None:
    """
    Assert decimal precision matches currency requirements.

    Args:
        amount: Amount to check
        currency: Currency code

    Raises:
        AssertionError: If precision doesn't match
    """
    config = get_currency(currency)

    # Check decimal places
    amount_str = str(amount)
    if '.' in amount_str:
        decimal_places = len(amount_str.split('.')[1].rstrip('0'))
        assert decimal_places <= config.decimal_places, \
            f"{currency} should have max {config.decimal_places} decimal places, " \
            f"got {decimal_places}"

    # For zero-decimal currencies, ensure no fractional part
    if config.decimal_places == 0:
        assert amount % 1 == 0, \
            f"{currency} is zero-decimal, but got fractional amount {amount}"


# ============================================================================
# FX Rate Helpers
# ============================================================================

def create_fx_rates(**pairs: Decimal) -> Dict[str, Decimal]:
    """
    Create FX rate dictionary from currency pairs.

    Example:
        rates = create_fx_rates(
            EUR_USD=Decimal("1.0850"),
            EUR_CLP=Decimal("1052.00")
        )

    Args:
        **pairs: Currency pair rates (FROM_TO=rate)

    Returns:
        FX rate dictionary
    """
    return {key: value for key, value in pairs.items()}


def get_test_fx_rate(
    from_currency: CurrencyCode,
    to_currency: CurrencyCode
) -> Decimal:
    """
    Get default test FX rate for a currency pair.

    Args:
        from_currency: Source currency
        to_currency: Target currency

    Returns:
        FX rate as Decimal
    """
    agent = CurrencyAgent()
    return agent.get_fx_rate(from_currency, to_currency)


def calculate_expected_conversion(
    amount: Decimal,
    from_currency: CurrencyCode,
    to_currency: CurrencyCode,
    fx_rate: Optional[Decimal] = None,
    round_before: bool = False
) -> Decimal:
    """
    Calculate expected conversion result.

    Args:
        amount: Amount to convert
        from_currency: Source currency
        to_currency: Target currency
        fx_rate: Optional FX rate (uses default if not provided)
        round_before: If True, rounds before conversion (bug)

    Returns:
        Expected converted amount
    """
    if fx_rate is None:
        agent = CurrencyAgent()
        fx_rate = agent.get_fx_rate(from_currency, to_currency)

    from_config = get_currency(from_currency)
    to_config = get_currency(to_currency)

    if round_before:
        # BUG: Round source first
        rounded_source = from_config.round_amount(amount)
        converted = rounded_source * fx_rate
        final_amount = to_config.round_amount(converted)
    else:
        # CORRECT: Convert first, then round
        converted = amount * fx_rate
        final_amount = to_config.round_amount(converted)

    return final_amount


# ============================================================================
# Test Data Factories
# ============================================================================

class AuthorizationRequestBuilder:
    """Builder for creating test authorization requests."""

    def __init__(self):
        """Initialize with defaults."""
        self.merchant_id = "test_merchant"
        self.customer_id = "test_customer"
        self.amount = Decimal("100.00")
        self.currency = CurrencyCode.EUR
        self.settlement_currency = None
        self.payment_method = PaymentMethod.CARD
        self.metadata = {}

    def with_merchant(self, merchant_id: str) -> 'AuthorizationRequestBuilder':
        """Set merchant ID."""
        self.merchant_id = merchant_id
        return self

    def with_customer(self, customer_id: str) -> 'AuthorizationRequestBuilder':
        """Set customer ID."""
        self.customer_id = customer_id
        return self

    def with_amount(self, amount: Decimal) -> 'AuthorizationRequestBuilder':
        """Set amount."""
        self.amount = amount
        return self

    def with_currency(self, currency: CurrencyCode) -> 'AuthorizationRequestBuilder':
        """Set currency."""
        self.currency = currency
        return self

    def with_settlement_currency(
        self,
        currency: CurrencyCode
    ) -> 'AuthorizationRequestBuilder':
        """Set settlement currency."""
        self.settlement_currency = currency
        return self

    def with_payment_method(
        self,
        method: PaymentMethod
    ) -> 'AuthorizationRequestBuilder':
        """Set payment method."""
        self.payment_method = method
        return self

    def with_metadata(self, **kwargs) -> 'AuthorizationRequestBuilder':
        """Add metadata."""
        self.metadata.update(kwargs)
        return self

    def build(self) -> AuthorizationRequest:
        """Build authorization request."""
        return AuthorizationRequest(
            merchant_id=self.merchant_id,
            customer_id=self.customer_id,
            amount=self.amount,
            currency=self.currency,
            settlement_currency=self.settlement_currency,
            payment_method=self.payment_method,
            idempotency_key=f"test_{datetime.utcnow().timestamp()}",
            metadata=self.metadata
        )


def create_authorization_request(
    amount: Decimal,
    currency: CurrencyCode,
    settlement_currency: Optional[CurrencyCode] = None,
    **kwargs
) -> AuthorizationRequest:
    """
    Create authorization request with defaults.

    Args:
        amount: Payment amount
        currency: Payment currency
        settlement_currency: Settlement currency (optional)
        **kwargs: Additional fields

    Returns:
        Authorization request
    """
    return AuthorizationRequestBuilder() \
        .with_amount(amount) \
        .with_currency(currency) \
        .with_settlement_currency(settlement_currency) \
        .with_metadata(**kwargs) \
        .build()


# ============================================================================
# Bug Detection Helpers
# ============================================================================

def compare_bug_vs_correct(
    amount: Decimal,
    from_currency: CurrencyCode,
    to_currency: CurrencyCode
) -> Tuple[Decimal, Decimal, Decimal]:
    """
    Compare buggy vs correct conversion logic.

    Args:
        amount: Amount to convert
        from_currency: Source currency
        to_currency: Target currency

    Returns:
        Tuple of (correct_result, buggy_result, loss_per_transaction)
    """
    agent = CurrencyAgent()

    # Correct logic
    correct_result, _ = agent.convert_amount(
        amount, from_currency, to_currency,
        round_before_conversion=False
    )

    # Buggy logic
    buggy_result, _ = agent.convert_amount(
        amount, from_currency, to_currency,
        round_before_conversion=True
    )

    loss = buggy_result - correct_result

    return correct_result, buggy_result, loss


def calculate_annual_loss(
    loss_per_transaction: Decimal,
    transactions_per_day: int,
    days_per_year: int = 365
) -> Decimal:
    """
    Calculate annual loss from per-transaction loss.

    Args:
        loss_per_transaction: Loss per transaction (in target currency)
        transactions_per_day: Number of transactions per day
        days_per_year: Days per year (default: 365)

    Returns:
        Annual loss in target currency
    """
    annual_transactions = transactions_per_day * days_per_year
    return loss_per_transaction * annual_transactions


# ============================================================================
# Validation Helpers
# ============================================================================

def validate_webhook_payload(webhook, expected_amount: Decimal) -> None:
    """
    Validate webhook payload structure and content.

    Args:
        webhook: Webhook payload
        expected_amount: Expected amount

    Raises:
        AssertionError: If validation fails
    """
    # Check required fields
    assert webhook.event_type is not None, "Event type missing"
    assert webhook.transaction_id is not None, "Transaction ID missing"
    assert webhook.status is not None, "Status missing"
    assert webhook.amount is not None, "Amount missing"
    assert webhook.currency is not None, "Currency missing"
    assert webhook.timestamp is not None, "Timestamp missing"

    # Check amount
    assert webhook.amount == expected_amount, \
        f"Expected webhook amount {expected_amount}, got {webhook.amount}"


def validate_transaction_record(
    transaction,
    expected_original_amount: Decimal,
    expected_original_currency: CurrencyCode,
    expected_settlement_amount: Optional[Decimal] = None
) -> None:
    """
    Validate transaction record completeness.

    Args:
        transaction: Transaction object
        expected_original_amount: Expected original amount
        expected_original_currency: Expected original currency
        expected_settlement_amount: Expected settlement amount (optional)

    Raises:
        AssertionError: If validation fails
    """
    assert transaction is not None, "Transaction not found"
    assert transaction.transaction_id is not None
    assert transaction.merchant_id is not None
    assert transaction.customer_id is not None

    # Check amounts
    assert transaction.original_amount == expected_original_amount
    assert transaction.original_currency == expected_original_currency

    if expected_settlement_amount is not None:
        assert transaction.settlement_amount == expected_settlement_amount

    # Check timestamps
    assert transaction.created_at is not None
    if transaction.settlement_amount is not None:
        assert transaction.fx_rate_timestamp is not None


# ============================================================================
# Test Data Constants
# ============================================================================

# Bug detector amounts (amounts that expose rounding bugs)
BUG_DETECTOR_AMOUNTS = {
    CurrencyCode.EUR: [
        Decimal("49.99"),  # Rounds to 50.00 (triggers bug)
        Decimal("99.99"),  # Rounds to 100.00
        Decimal("0.01"),   # Edge case: minimum amount
    ],
    CurrencyCode.USD: [
        Decimal("50.01"),  # Fractional
        Decimal("99.99"),
    ]
}

# Critical currency pairs (most likely to have bugs)
CRITICAL_PAIRS = [
    (CurrencyCode.EUR, CurrencyCode.CLP),  # The incident
    (CurrencyCode.EUR, CurrencyCode.JPY),  # High volume
    (CurrencyCode.USD, CurrencyCode.KRW),  # Common pair
    (CurrencyCode.GBP, CurrencyCode.COP),  # Zero-decimal
    (CurrencyCode.EUR, CurrencyCode.KWD),  # Three-decimal
]

# Expected conversions (for quick reference)
EXPECTED_CONVERSIONS = {
    ("EUR", "CLP", "49.99"): Decimal("52595"),
    ("EUR", "JPY", "100.00"): Decimal("16125"),
    ("USD", "KRW", "50.00"): Decimal("66608"),
    ("EUR", "USD", "100.00"): Decimal("108.50"),
    ("EUR", "KWD", "100.00"): Decimal("33.450"),
}
