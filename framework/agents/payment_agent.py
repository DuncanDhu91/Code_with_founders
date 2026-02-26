"""Payment Agent - Simulates payment processing and authorization logic.

This agent is responsible for:
- Processing payment authorization requests
- Simulating payment gateway behavior
- Generating webhooks
- Managing transaction state
"""

import uuid
from decimal import Decimal
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from framework.models.currency import CurrencyCode
from framework.models.transaction import (
    Transaction,
    AuthorizationRequest,
    AuthorizationResponse,
    WebhookPayload,
    TransactionStatus,
    PaymentMethod
)
from framework.agents.currency_agent import CurrencyAgent, CurrencyConversionError


logger = logging.getLogger(__name__)


class PaymentProcessingError(Exception):
    """Raised when payment processing fails."""
    pass


class PaymentAgent:
    """Agent for simulating payment processing in tests."""

    def __init__(
        self,
        currency_agent: CurrencyAgent,
        simulate_bug: bool = False
    ):
        """
        Initialize Payment Agent.

        Args:
            currency_agent: Currency agent for FX operations
            simulate_bug: If True, simulates the rounding bug
        """
        self.currency_agent = currency_agent
        self.simulate_bug = simulate_bug
        self.transactions: Dict[str, Transaction] = {}
        self.webhooks: Dict[str, list] = {}

    def authorize_payment(
        self,
        request: AuthorizationRequest
    ) -> AuthorizationResponse:
        """
        Process payment authorization request.

        This simulates the Yuno checkout API behavior.

        Args:
            request: Authorization request

        Returns:
            Authorization response

        Raises:
            PaymentProcessingError: If authorization fails
        """
        try:
            # Generate transaction ID
            transaction_id = f"txn_{uuid.uuid4().hex[:16]}"

            # Determine settlement currency (defaults to request currency)
            settlement_currency = request.settlement_currency or request.currency

            # Validate original amount
            is_valid, error_msg = self.currency_agent.validate_amount_for_currency(
                request.amount,
                request.currency
            )
            if not is_valid:
                return self._create_error_response(
                    transaction_id,
                    "INVALID_AMOUNT",
                    error_msg
                )

            # Perform currency conversion if needed
            if request.currency != settlement_currency:
                try:
                    authorized_amount, fx_rate = self.currency_agent.convert_amount(
                        amount=request.amount,
                        from_currency=request.currency,
                        to_currency=settlement_currency,
                        round_before_conversion=self.simulate_bug  # THE BUG TOGGLE
                    )
                except CurrencyConversionError as e:
                    return self._create_error_response(
                        transaction_id,
                        "FX_RATE_UNAVAILABLE",
                        str(e)
                    )

                # Validate converted amount
                is_valid, error_msg = self.currency_agent.validate_amount_for_currency(
                    authorized_amount,
                    settlement_currency
                )
                if not is_valid:
                    return self._create_error_response(
                        transaction_id,
                        "CONVERTED_AMOUNT_INVALID",
                        error_msg
                    )
            else:
                authorized_amount = request.amount
                fx_rate = Decimal("1.0")

            # Create transaction record
            transaction = Transaction(
                transaction_id=transaction_id,
                merchant_id=request.merchant_id,
                customer_id=request.customer_id,
                original_amount=request.amount,
                original_currency=request.currency,
                settlement_amount=authorized_amount if request.currency != settlement_currency else None,
                settlement_currency=settlement_currency if request.currency != settlement_currency else None,
                authorized_amount=authorized_amount,
                fx_rate=fx_rate if request.currency != settlement_currency else None,
                fx_rate_timestamp=datetime.utcnow(),
                status=TransactionStatus.AUTHORIZED,
                payment_method=request.payment_method,
                metadata=request.metadata
            )

            # Store transaction
            self.transactions[transaction_id] = transaction

            # Generate webhook
            self._generate_webhook(transaction)

            # Create response
            response = AuthorizationResponse(
                transaction_id=transaction_id,
                status=TransactionStatus.AUTHORIZED,
                authorized_amount=authorized_amount,
                authorized_currency=settlement_currency,
                settlement_amount=authorized_amount if request.currency != settlement_currency else None,
                settlement_currency=settlement_currency if request.currency != settlement_currency else None,
                fx_rate=fx_rate if request.currency != settlement_currency else None,
                message="Authorization successful"
            )

            logger.info(
                f"Authorized payment: {transaction_id}, "
                f"amount={request.amount} {request.currency}, "
                f"authorized={authorized_amount} {settlement_currency}, "
                f"fx_rate={fx_rate if fx_rate != Decimal('1.0') else 'N/A'}"
            )

            return response

        except Exception as e:
            logger.error(f"Payment authorization failed: {str(e)}", exc_info=True)
            raise PaymentProcessingError(f"Authorization failed: {str(e)}")

    def _create_error_response(
        self,
        transaction_id: str,
        error_code: str,
        message: str
    ) -> AuthorizationResponse:
        """Create error response."""
        return AuthorizationResponse(
            transaction_id=transaction_id,
            status=TransactionStatus.FAILED,
            authorized_amount=Decimal("0"),
            authorized_currency=CurrencyCode.USD,
            error_code=error_code,
            message=message
        )

    def _generate_webhook(self, transaction: Transaction) -> None:
        """Generate webhook payload for transaction."""
        webhook = WebhookPayload(
            event_type="payment.authorized",
            transaction_id=transaction.transaction_id,
            status=transaction.status,
            amount=transaction.authorized_amount,
            currency=transaction.settlement_currency or transaction.original_currency,
            settlement_amount=transaction.settlement_amount,
            settlement_currency=transaction.settlement_currency,
            metadata={
                "merchant_id": transaction.merchant_id,
                "customer_id": transaction.customer_id,
                "fx_rate": str(transaction.fx_rate) if transaction.fx_rate else None
            }
        )

        if transaction.merchant_id not in self.webhooks:
            self.webhooks[transaction.merchant_id] = []

        self.webhooks[transaction.merchant_id].append(webhook)

        logger.debug(f"Generated webhook for transaction {transaction.transaction_id}")

    def get_transaction(self, transaction_id: str) -> Optional[Transaction]:
        """Get transaction by ID."""
        return self.transactions.get(transaction_id)

    def get_webhooks_for_merchant(self, merchant_id: str) -> list:
        """Get all webhooks for a merchant."""
        return self.webhooks.get(merchant_id, [])

    def clear_webhooks(self, merchant_id: str) -> None:
        """Clear webhooks for a merchant (test cleanup)."""
        if merchant_id in self.webhooks:
            self.webhooks[merchant_id] = []

    def reset(self) -> None:
        """Reset agent state (for test isolation)."""
        self.transactions = {}
        self.webhooks = {}
