"""Async Testing Utilities for Webhook Validation.

This module provides utilities for testing webhook delivery and validation
in an async-friendly manner without sleep() calls or race conditions.

Key Features:
- WebhookCollector: Captures webhook payloads in-memory
- wait_for_webhook(): Async assertion helper with timeout
- assert_webhook_payload(): Validation with detailed error messages
- create_concurrent_checkouts(): Race condition testing helper

Addresses Devil's Advocate concerns about deterministic async testing.
"""

import asyncio
from decimal import Decimal
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime, timedelta
import logging

from framework.models.transaction import WebhookPayload, TransactionStatus
from framework.models.currency import CurrencyCode


logger = logging.getLogger(__name__)


class WebhookCollector:
    """
    Captures webhook payloads in-memory for testing.

    Thread-safe collection for concurrent webhook delivery testing.
    Provides async-friendly waiting and assertion methods.

    Usage:
        collector = WebhookCollector()
        # ... trigger webhook generation ...
        webhook = await collector.wait_for_webhook(
            predicate=lambda w: w.transaction_id == "txn_123",
            timeout_seconds=5
        )
    """

    def __init__(self):
        """Initialize webhook collector."""
        self.webhooks: List[WebhookPayload] = []
        self._lock = asyncio.Lock()
        self._new_webhook_event = asyncio.Event()

    def add(self, webhook: WebhookPayload) -> None:
        """
        Add webhook to collection (synchronous).

        Args:
            webhook: Webhook payload to add
        """
        # Note: This is called from sync code (PaymentAgent)
        # We use asyncio.create_task to set the event
        self.webhooks.append(webhook)
        logger.debug(f"Webhook collected: {webhook.transaction_id}")

        # Signal waiting coroutines
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.call_soon_threadsafe(self._new_webhook_event.set)
        except RuntimeError:
            # No event loop running (sync test)
            pass

    async def wait_for_webhook(
        self,
        predicate: Callable[[WebhookPayload], bool],
        timeout_seconds: float = 5.0,
        poll_interval: float = 0.1
    ) -> Optional[WebhookPayload]:
        """
        Wait for webhook matching predicate (async).

        Uses event-based waiting instead of polling for efficiency.
        Falls back to polling every poll_interval seconds.

        Args:
            predicate: Function to test each webhook
            timeout_seconds: Maximum wait time
            poll_interval: Polling interval for fallback

        Returns:
            Matching webhook or None if timeout

        Example:
            webhook = await collector.wait_for_webhook(
                lambda w: w.transaction_id == "txn_123" and w.status == "AUTHORIZED",
                timeout_seconds=5
            )
            assert webhook is not None, "Webhook not received"
        """
        start_time = asyncio.get_event_loop().time()
        deadline = start_time + timeout_seconds

        while asyncio.get_event_loop().time() < deadline:
            # Check existing webhooks
            async with self._lock:
                for webhook in self.webhooks:
                    if predicate(webhook):
                        logger.debug(f"Found matching webhook: {webhook.transaction_id}")
                        return webhook

            # Wait for new webhook or timeout
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                break

            try:
                await asyncio.wait_for(
                    self._new_webhook_event.wait(),
                    timeout=min(remaining, poll_interval)
                )
                self._new_webhook_event.clear()
            except asyncio.TimeoutError:
                # Polling timeout, loop continues
                pass

        logger.warning(
            f"Webhook timeout after {timeout_seconds}s. "
            f"Collected {len(self.webhooks)} webhooks."
        )
        return None

    async def wait_for_webhooks(
        self,
        count: int,
        predicate: Optional[Callable[[WebhookPayload], bool]] = None,
        timeout_seconds: float = 5.0
    ) -> List[WebhookPayload]:
        """
        Wait for multiple webhooks matching predicate.

        Args:
            count: Number of webhooks to wait for
            predicate: Optional filter function
            timeout_seconds: Maximum wait time

        Returns:
            List of matching webhooks (may be less than count if timeout)

        Example:
            # Wait for 3 webhooks for same merchant
            webhooks = await collector.wait_for_webhooks(
                count=3,
                predicate=lambda w: w.metadata.get("merchant_id") == "merchant_001"
            )
        """
        results = []
        start_time = asyncio.get_event_loop().time()
        deadline = start_time + timeout_seconds

        while len(results) < count and asyncio.get_event_loop().time() < deadline:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                break

            webhook = await self.wait_for_webhook(
                predicate=predicate or (lambda w: True),
                timeout_seconds=remaining
            )

            if webhook and webhook not in results:
                results.append(webhook)
            else:
                break

        return results

    def get_all(self) -> List[WebhookPayload]:
        """Get all collected webhooks (sync)."""
        return self.webhooks.copy()

    def get_for_transaction(self, transaction_id: str) -> List[WebhookPayload]:
        """Get webhooks for specific transaction."""
        return [w for w in self.webhooks if w.transaction_id == transaction_id]

    def get_for_merchant(self, merchant_id: str) -> List[WebhookPayload]:
        """Get webhooks for specific merchant."""
        return [
            w for w in self.webhooks
            if w.metadata.get("merchant_id") == merchant_id
        ]

    def count(self) -> int:
        """Count collected webhooks."""
        return len(self.webhooks)

    def clear(self) -> None:
        """Clear all collected webhooks."""
        self.webhooks.clear()
        self._new_webhook_event.clear()
        logger.debug("Webhook collector cleared")


async def wait_for_webhook(
    collector: WebhookCollector,
    transaction_id: str,
    expected_status: Optional[TransactionStatus] = None,
    timeout_seconds: float = 5.0
) -> WebhookPayload:
    """
    Async assertion helper for webhook delivery.

    Waits for webhook and raises AssertionError with helpful message on timeout.

    Args:
        collector: WebhookCollector instance
        transaction_id: Expected transaction ID
        expected_status: Optional expected status
        timeout_seconds: Maximum wait time

    Returns:
        Webhook payload

    Raises:
        AssertionError: If webhook not received or validation fails

    Example:
        webhook = await wait_for_webhook(
            collector,
            transaction_id="txn_123",
            expected_status=TransactionStatus.AUTHORIZED,
            timeout_seconds=5
        )
    """
    predicate = lambda w: w.transaction_id == transaction_id
    if expected_status:
        predicate = lambda w: (
            w.transaction_id == transaction_id and
            w.status == expected_status
        )

    webhook = await collector.wait_for_webhook(predicate, timeout_seconds)

    if webhook is None:
        # Build helpful error message
        all_webhooks = collector.get_all()
        error_msg = (
            f"Webhook not received for transaction {transaction_id} "
            f"within {timeout_seconds}s.\n"
            f"Total webhooks collected: {len(all_webhooks)}\n"
        )

        if all_webhooks:
            error_msg += "Received webhooks:\n"
            for w in all_webhooks[-5:]:  # Show last 5
                error_msg += f"  - {w.transaction_id}: {w.status}\n"
        else:
            error_msg += "No webhooks received. Check if webhook generation is enabled."

        raise AssertionError(error_msg)

    return webhook


def assert_webhook_payload(
    webhook: WebhookPayload,
    expected_transaction_id: str,
    expected_status: TransactionStatus,
    expected_amount: Decimal,
    expected_currency: CurrencyCode,
    expected_settlement_amount: Optional[Decimal] = None,
    expected_settlement_currency: Optional[CurrencyCode] = None,
    expected_fx_rate: Optional[Decimal] = None,
    context: str = ""
) -> None:
    """
    Validate webhook payload with detailed error messages.

    Args:
        webhook: Webhook payload to validate
        expected_transaction_id: Expected transaction ID
        expected_status: Expected status
        expected_amount: Expected amount
        expected_currency: Expected currency
        expected_settlement_amount: Expected settlement amount (if different)
        expected_settlement_currency: Expected settlement currency (if different)
        expected_fx_rate: Expected FX rate (if conversion occurred)
        context: Additional context for error messages

    Raises:
        AssertionError: If validation fails

    Example:
        assert_webhook_payload(
            webhook,
            expected_transaction_id="txn_123",
            expected_status=TransactionStatus.AUTHORIZED,
            expected_amount=Decimal("52595"),
            expected_currency=CurrencyCode.CLP,
            expected_settlement_amount=Decimal("52595"),
            expected_settlement_currency=CurrencyCode.CLP,
            expected_fx_rate=Decimal("1052.00"),
            context="EUR 49.99 → CLP conversion"
        )
    """
    errors = []

    # Validate transaction ID
    if webhook.transaction_id != expected_transaction_id:
        errors.append(
            f"Transaction ID mismatch: expected {expected_transaction_id}, "
            f"got {webhook.transaction_id}"
        )

    # Validate status
    if webhook.status != expected_status:
        errors.append(
            f"Status mismatch: expected {expected_status}, got {webhook.status}"
        )

    # Validate amount (with currency-appropriate precision)
    from framework.models.currency import get_currency
    currency_config = get_currency(expected_currency)
    rounded_expected = currency_config.round_amount(expected_amount)
    rounded_actual = currency_config.round_amount(webhook.amount)

    if rounded_actual != rounded_expected:
        errors.append(
            f"Amount mismatch: expected {currency_config.format_amount(expected_amount)}, "
            f"got {currency_config.format_amount(webhook.amount)}"
        )

    # Validate currency
    if webhook.currency != expected_currency:
        errors.append(
            f"Currency mismatch: expected {expected_currency}, got {webhook.currency}"
        )

    # Validate settlement amount (if applicable)
    if expected_settlement_amount is not None:
        if webhook.settlement_amount is None:
            errors.append("Settlement amount is None, but expected value was provided")
        else:
            settlement_config = get_currency(expected_settlement_currency)
            rounded_settlement_expected = settlement_config.round_amount(expected_settlement_amount)
            rounded_settlement_actual = settlement_config.round_amount(webhook.settlement_amount)

            if rounded_settlement_actual != rounded_settlement_expected:
                errors.append(
                    f"Settlement amount mismatch: "
                    f"expected {settlement_config.format_amount(expected_settlement_amount)}, "
                    f"got {settlement_config.format_amount(webhook.settlement_amount)}"
                )

    # Validate settlement currency (if applicable)
    if expected_settlement_currency is not None:
        if webhook.settlement_currency != expected_settlement_currency:
            errors.append(
                f"Settlement currency mismatch: "
                f"expected {expected_settlement_currency}, got {webhook.settlement_currency}"
            )

    # Validate FX rate (if applicable)
    if expected_fx_rate is not None:
        fx_rate_str = webhook.metadata.get("fx_rate")
        if fx_rate_str is None:
            errors.append("FX rate not found in webhook metadata")
        else:
            actual_fx_rate = Decimal(fx_rate_str)
            if actual_fx_rate != expected_fx_rate:
                errors.append(
                    f"FX rate mismatch: expected {expected_fx_rate}, got {actual_fx_rate}"
                )

    # Validate conversion metadata exists
    if expected_fx_rate is not None or expected_settlement_currency is not None:
        if "fx_rate" not in webhook.metadata:
            errors.append("Conversion metadata (fx_rate) missing from webhook")

    # Raise assertion if any errors
    if errors:
        error_msg = f"Webhook validation failed"
        if context:
            error_msg += f" ({context})"
        error_msg += ":\n"
        for error in errors:
            error_msg += f"  - {error}\n"

        error_msg += f"\nWebhook payload:\n"
        error_msg += f"  transaction_id: {webhook.transaction_id}\n"
        error_msg += f"  status: {webhook.status}\n"
        error_msg += f"  amount: {webhook.amount} {webhook.currency}\n"
        if webhook.settlement_amount:
            error_msg += f"  settlement: {webhook.settlement_amount} {webhook.settlement_currency}\n"
        error_msg += f"  metadata: {webhook.metadata}\n"

        raise AssertionError(error_msg)


async def create_concurrent_checkouts(
    payment_agent,
    count: int,
    merchant_id: str,
    base_amount: Decimal,
    currency: CurrencyCode,
    settlement_currency: CurrencyCode,
    payment_method
) -> List:
    """
    Create concurrent checkout requests for race condition testing.

    Spawns multiple authorization requests simultaneously to test:
    - FX rate cache consistency
    - Webhook delivery ordering
    - Idempotency key handling
    - Concurrent transaction processing

    Args:
        payment_agent: PaymentAgent instance
        count: Number of concurrent requests
        merchant_id: Merchant ID
        base_amount: Base amount for transactions
        currency: Original currency
        settlement_currency: Settlement currency
        payment_method: Payment method enum

    Returns:
        List of authorization responses

    Example:
        # Test FX rate consistency under load
        responses = await create_concurrent_checkouts(
            payment_agent,
            count=100,
            merchant_id="merchant_001",
            base_amount=Decimal("49.99"),
            currency=CurrencyCode.EUR,
            settlement_currency=CurrencyCode.CLP,
            payment_method=PaymentMethod.CARD
        )

        # Verify all used same FX rate (no race condition)
        fx_rates = [r.fx_rate for r in responses]
        assert len(set(fx_rates)) == 1, "FX rate inconsistency detected"
    """
    from framework.models.transaction import AuthorizationRequest
    import uuid

    async def authorize_async(index: int):
        """Async wrapper for authorization (since PaymentAgent is sync)."""
        request = AuthorizationRequest(
            merchant_id=merchant_id,
            customer_id=f"customer_{index:03d}",
            amount=base_amount,
            currency=currency,
            settlement_currency=settlement_currency,
            payment_method=payment_method,
            idempotency_key=f"concurrent_test_{uuid.uuid4().hex[:8]}_{index}"
        )

        # Run sync authorization in thread pool
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            payment_agent.authorize_payment,
            request
        )
        return response

    # Launch all requests concurrently
    tasks = [authorize_async(i) for i in range(count)]
    responses = await asyncio.gather(*tasks, return_exceptions=True)

    # Separate successes from exceptions
    successful = []
    failed = []
    for i, response in enumerate(responses):
        if isinstance(response, Exception):
            logger.error(f"Concurrent checkout {i} failed: {response}")
            failed.append(response)
        else:
            successful.append(response)

    logger.info(
        f"Concurrent checkouts: {len(successful)} succeeded, {len(failed)} failed"
    )

    return successful


class WebhookServerSimulator:
    """
    Simulates webhook delivery behavior for testing edge cases.

    Supports:
    - Network errors (503, timeout)
    - Retry logic
    - Out-of-order delivery
    - Duplicate webhooks
    """

    def __init__(self):
        """Initialize webhook server simulator."""
        self.delivered_webhooks: List[WebhookPayload] = []
        self.failed_deliveries: List[Dict[str, Any]] = []
        self.retry_count: Dict[str, int] = {}
        self.should_fail = False
        self.failure_rate = 0.0  # 0.0 to 1.0

    def set_failure_mode(self, enabled: bool, rate: float = 1.0) -> None:
        """
        Enable/disable failure mode.

        Args:
            enabled: Whether to simulate failures
            rate: Failure rate (0.0 to 1.0)
        """
        self.should_fail = enabled
        self.failure_rate = rate

    async def deliver_webhook(
        self,
        webhook: WebhookPayload,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> bool:
        """
        Simulate webhook delivery with retry logic.

        Args:
            webhook: Webhook to deliver
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries (seconds)

        Returns:
            True if delivery succeeded, False otherwise
        """
        import random

        attempt = 0
        webhook_id = webhook.transaction_id

        while attempt < max_retries:
            attempt += 1
            self.retry_count[webhook_id] = attempt

            # Simulate network call
            await asyncio.sleep(0.01)  # Simulate latency

            # Determine if this attempt fails
            should_fail_now = (
                self.should_fail and
                random.random() < self.failure_rate
            )

            if should_fail_now:
                logger.warning(
                    f"Webhook delivery failed (attempt {attempt}/{max_retries}): "
                    f"{webhook_id}"
                )
                self.failed_deliveries.append({
                    "webhook": webhook,
                    "attempt": attempt,
                    "error": "503 Service Unavailable"
                })

                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    return False
            else:
                # Success
                self.delivered_webhooks.append(webhook)
                logger.debug(f"Webhook delivered successfully: {webhook_id}")
                return True

        return False

    def get_retry_count(self, transaction_id: str) -> int:
        """Get number of delivery attempts for transaction."""
        return self.retry_count.get(transaction_id, 0)

    def get_delivered_count(self) -> int:
        """Get number of successfully delivered webhooks."""
        return len(self.delivered_webhooks)

    def get_failed_count(self) -> int:
        """Get number of failed delivery attempts."""
        return len(self.failed_deliveries)

    def reset(self) -> None:
        """Reset simulator state."""
        self.delivered_webhooks.clear()
        self.failed_deliveries.clear()
        self.retry_count.clear()
        self.should_fail = False
