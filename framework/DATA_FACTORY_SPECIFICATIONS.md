# Data Factory Specifications

## Executive Summary

This document defines reusable data factories for generating test transactions, currency conversions, and FX rate fixtures. These factories enable systematic test data generation, support parallel execution, and ensure deterministic, reproducible tests.

**Design Principles**:
1. **Deterministic**: Same inputs produce same outputs (seedable randomness)
2. **Isolated**: Each test gets independent data (no shared state)
3. **Composable**: Factories can be combined for complex scenarios
4. **Type-safe**: Leverages Pydantic models for validation
5. **Testable**: Factories themselves are unit tested

---

## 1. Factory Architecture Overview

### 1.1 Factory Hierarchy

```
BaseFactory (abstract)
├── CurrencyPairFactory (static methods for pair combinations)
├── AmountFactory (generates test amounts)
├── ExchangeRateFactory (generates FX rate fixtures)
├── TransactionFactory (generates authorization requests)
├── WebhookFactory (generates webhook payloads)
└── TestScenarioFactory (orchestrates all factories)
```

### 1.2 Dependencies

```python
from decimal import Decimal
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import uuid
import random
from pydantic import BaseModel

from framework.models.currency import CurrencyCode, Currency, get_currency
from framework.models.transaction import (
    Transaction,
    AuthorizationRequest,
    AuthorizationResponse,
    WebhookPayload,
    TransactionStatus,
    PaymentMethod
)
from framework.agents.currency_agent import CurrencyAgent
```

---

## 2. Base Factory Class

### 2.1 Abstract Base Factory

```python
from abc import ABC, abstractmethod

class BaseFactory(ABC):
    """
    Abstract base class for all data factories.

    Provides common functionality:
    - Counter management for unique IDs
    - Deterministic randomness (seeding)
    - Metadata tracking
    """

    def __init__(self, seed: int = 42, worker_id: str = "master"):
        """
        Initialize base factory.

        Args:
            seed: Random seed for deterministic generation
            worker_id: Worker ID for parallel execution (from pytest-xdist)
        """
        self.seed = seed
        self.worker_id = worker_id
        self.counter = self._calculate_worker_offset()
        self.metadata: Dict[str, Any] = {}
        random.seed(seed)

    def _calculate_worker_offset(self) -> int:
        """
        Calculate unique counter offset for this worker.

        Ensures no ID collisions in parallel execution.
        """
        if self.worker_id == "master":
            return 0
        # Extract number from 'gw0', 'gw1', etc.
        worker_num = int(self.worker_id.replace("gw", ""))
        return worker_num * 100000  # Each worker gets 100k ID space

    def _next_counter(self) -> int:
        """Get next counter value and increment."""
        self.counter += 1
        return self.counter

    def _generate_uuid(self, prefix: str = "") -> str:
        """
        Generate deterministic UUID based on counter.

        Args:
            prefix: Optional prefix for the ID

        Returns:
            UUID string
        """
        # Use counter + seed for determinism
        deterministic_seed = self.seed + self.counter
        random.seed(deterministic_seed)

        uuid_hex = uuid.UUID(int=random.getrandbits(128)).hex
        random.seed(self.seed)  # Reset seed

        if prefix:
            return f"{prefix}_{uuid_hex[:16]}"
        return uuid_hex[:16]

    def reset(self):
        """Reset factory state (for test isolation)."""
        self.counter = self._calculate_worker_offset()
        random.seed(self.seed)
        self.metadata = {}

    @abstractmethod
    def create(self, **kwargs):
        """Create an instance (implemented by subclasses)."""
        pass
```

---

## 3. Currency Pair Factory

### 3.1 Implementation

```python
class CurrencyPairFactory:
    """
    Factory for generating currency pair combinations.

    This factory uses static methods since pairs don't need state.
    """

    @staticmethod
    def create_critical_pairs() -> List[Tuple[CurrencyCode, CurrencyCode]]:
        """
        Generate P0 critical currency pairs (zero-decimal settlement).

        Returns:
            List of (from_currency, to_currency) tuples
        """
        return [
            (CurrencyCode.EUR, CurrencyCode.CLP),
            (CurrencyCode.EUR, CurrencyCode.COP),
            (CurrencyCode.EUR, CurrencyCode.JPY),
            (CurrencyCode.EUR, CurrencyCode.KRW),
            (CurrencyCode.USD, CurrencyCode.CLP),
            (CurrencyCode.USD, CurrencyCode.COP),
            (CurrencyCode.USD, CurrencyCode.JPY),
            (CurrencyCode.USD, CurrencyCode.KRW),
            (CurrencyCode.GBP, CurrencyCode.JPY),
            (CurrencyCode.GBP, CurrencyCode.CLP),
            (CurrencyCode.GBP, CurrencyCode.COP),
        ]

    @staticmethod
    def create_high_priority_pairs() -> List[Tuple[CurrencyCode, CurrencyCode]]:
        """Generate P1 high priority pairs (standard + three-decimal)."""
        return [
            # Standard two-decimal
            (CurrencyCode.EUR, CurrencyCode.USD),
            (CurrencyCode.EUR, CurrencyCode.GBP),
            (CurrencyCode.USD, CurrencyCode.GBP),
            (CurrencyCode.EUR, CurrencyCode.BRL),
            (CurrencyCode.EUR, CurrencyCode.MXN),
            (CurrencyCode.USD, CurrencyCode.BRL),
            (CurrencyCode.USD, CurrencyCode.MXN),
            (CurrencyCode.GBP, CurrencyCode.EUR),

            # Three-decimal
            (CurrencyCode.EUR, CurrencyCode.KWD),
            (CurrencyCode.EUR, CurrencyCode.BHD),
            (CurrencyCode.EUR, CurrencyCode.OMR),
            (CurrencyCode.USD, CurrencyCode.KWD),
            (CurrencyCode.USD, CurrencyCode.BHD),
            (CurrencyCode.USD, CurrencyCode.OMR),
            (CurrencyCode.EUR, CurrencyCode.JOD),
            (CurrencyCode.USD, CurrencyCode.JOD),
        ]

    @staticmethod
    def create_all_decimal_combinations() -> List[Tuple[CurrencyCode, CurrencyCode, str]]:
        """
        Generate pairs covering all decimal type combinations.

        Returns:
            List of (from_currency, to_currency, combination_type) tuples
        """
        return [
            # 2-decimal → 0-decimal (CRITICAL)
            (CurrencyCode.EUR, CurrencyCode.CLP, "2dec_to_0dec"),
            (CurrencyCode.USD, CurrencyCode.JPY, "2dec_to_0dec"),
            (CurrencyCode.GBP, CurrencyCode.COP, "2dec_to_0dec"),

            # 2-decimal → 2-decimal (STANDARD)
            (CurrencyCode.EUR, CurrencyCode.USD, "2dec_to_2dec"),
            (CurrencyCode.EUR, CurrencyCode.GBP, "2dec_to_2dec"),

            # 2-decimal → 3-decimal
            (CurrencyCode.EUR, CurrencyCode.KWD, "2dec_to_3dec"),
            (CurrencyCode.USD, CurrencyCode.BHD, "2dec_to_3dec"),

            # 0-decimal → 2-decimal
            (CurrencyCode.JPY, CurrencyCode.EUR, "0dec_to_2dec"),
            (CurrencyCode.CLP, CurrencyCode.USD, "0dec_to_2dec"),

            # 0-decimal → 0-decimal
            (CurrencyCode.JPY, CurrencyCode.CLP, "0dec_to_0dec"),

            # 0-decimal → 3-decimal
            (CurrencyCode.JPY, CurrencyCode.KWD, "0dec_to_3dec"),

            # 3-decimal → 2-decimal
            (CurrencyCode.KWD, CurrencyCode.EUR, "3dec_to_2dec"),
            (CurrencyCode.BHD, CurrencyCode.USD, "3dec_to_2dec"),

            # 3-decimal → 0-decimal
            (CurrencyCode.KWD, CurrencyCode.JPY, "3dec_to_0dec"),

            # 3-decimal → 3-decimal
            (CurrencyCode.KWD, CurrencyCode.BHD, "3dec_to_3dec"),
        ]

    @staticmethod
    def get_pairs_by_priority(priority: str) -> List[Tuple[CurrencyCode, CurrencyCode]]:
        """
        Get currency pairs by priority tier.

        Args:
            priority: One of 'P0', 'P1', 'P2', 'P3'

        Returns:
            List of currency pairs
        """
        if priority == "P0":
            return CurrencyPairFactory.create_critical_pairs()
        elif priority == "P1":
            return CurrencyPairFactory.create_high_priority_pairs()
        elif priority == "P2":
            return [
                # Reverse zero-decimal
                (CurrencyCode.JPY, CurrencyCode.EUR),
                (CurrencyCode.JPY, CurrencyCode.USD),
                (CurrencyCode.CLP, CurrencyCode.EUR),
                (CurrencyCode.CLP, CurrencyCode.USD),
                (CurrencyCode.KRW, CurrencyCode.USD),
                (CurrencyCode.COP, CurrencyCode.EUR),

                # Emerging markets (added in P2)
                # Add more as needed
            ]
        else:  # P3
            return [
                # Same-currency pairs
                (CurrencyCode.EUR, CurrencyCode.EUR),
                (CurrencyCode.USD, CurrencyCode.USD),
                (CurrencyCode.JPY, CurrencyCode.JPY),
                (CurrencyCode.KWD, CurrencyCode.KWD),
            ]

    @staticmethod
    def get_pairs_by_decimal_type(
        from_decimals: int,
        to_decimals: int
    ) -> List[Tuple[CurrencyCode, CurrencyCode]]:
        """
        Get currency pairs by decimal type combination.

        Args:
            from_decimals: Source currency decimal places (0, 2, or 3)
            to_decimals: Target currency decimal places (0, 2, or 3)

        Returns:
            List of matching currency pairs
        """
        all_combos = CurrencyPairFactory.create_all_decimal_combinations()
        return [
            (from_curr, to_curr)
            for from_curr, to_curr, _ in all_combos
            if get_currency(from_curr).decimal_places == from_decimals
            and get_currency(to_curr).decimal_places == to_decimals
        ]
```

---

## 4. Amount Factory

### 4.1 Implementation

```python
class AmountFactory(BaseFactory):
    """Factory for generating test amounts."""

    def create_minimum_amount(self, currency: CurrencyCode) -> Decimal:
        """Get minimum valid amount for currency."""
        config = get_currency(currency)
        return config.min_amount

    def create_maximum_amount(self, currency: CurrencyCode) -> Decimal:
        """Get maximum valid amount for currency."""
        config = get_currency(currency)
        return config.max_amount

    def create_bug_revealing_amounts(
        self,
        currency: CurrencyCode
    ) -> List[Decimal]:
        """
        Generate amounts that reveal the rounding bug.

        These amounts have fractional parts that get lost if rounded prematurely.
        """
        config = get_currency(currency)

        if config.decimal_places == 2:
            return [
                Decimal("49.99"),  # THE INCIDENT AMOUNT
                Decimal("99.99"),
                Decimal("149.99"),
                Decimal("199.99"),
                Decimal("10.01"),
                Decimal("20.01"),
                Decimal("30.01"),
                Decimal("0.99"),
                Decimal("1.99"),
                Decimal("2.99"),
            ]
        elif config.decimal_places == 3:
            return [
                Decimal("49.999"),
                Decimal("99.999"),
                Decimal("10.001"),
                Decimal("20.001"),
                Decimal("0.999"),
            ]
        else:
            # Zero-decimal currencies don't have fractional parts
            return []

    def create_safe_amounts(self, currency: CurrencyCode) -> List[Decimal]:
        """
        Generate amounts that DON'T reveal the bug (negative tests).

        These amounts are already rounded.
        """
        config = get_currency(currency)

        if config.decimal_places == 2:
            return [
                Decimal("50.00"),
                Decimal("100.00"),
                Decimal("150.00"),
                Decimal("200.00"),
                Decimal("0.50"),
                Decimal("1.00"),
                Decimal("10.00"),
            ]
        elif config.decimal_places == 3:
            return [
                Decimal("50.000"),
                Decimal("100.000"),
                Decimal("1.000"),
            ]
        else:
            return [
                Decimal("50"),
                Decimal("100"),
                Decimal("1000"),
            ]

    def create_boundary_amounts(
        self,
        currency: CurrencyCode
    ) -> List[Decimal]:
        """
        Generate boundary value amounts.

        Returns amounts near min/max limits.
        """
        config = get_currency(currency)
        min_amt = config.min_amount
        max_amt = config.max_amount

        amounts = [min_amt]

        # Just above minimum
        if config.decimal_places == 0:
            amounts.append(min_amt + Decimal("1"))
            amounts.append(min_amt + Decimal("10"))
        else:
            amounts.append(min_amt + min_amt)
            amounts.append(min_amt * Decimal("10"))

        # Just below maximum
        if max_amt < Decimal("1000000"):  # Don't exceed reasonable limits
            amounts.append(max_amt - min_amt)
            amounts.append(max_amt - min_amt * Decimal("10"))

        return amounts

    def create_random_amounts(
        self,
        currency: CurrencyCode,
        count: int = 20,
        min_value: Optional[Decimal] = None,
        max_value: Optional[Decimal] = None,
    ) -> List[Decimal]:
        """
        Generate random realistic amounts (seeded for determinism).

        Args:
            currency: Currency code
            count: Number of amounts to generate
            min_value: Minimum value (defaults to currency min * 10)
            max_value: Maximum value (defaults to currency max / 10)

        Returns:
            List of random amounts
        """
        config = get_currency(currency)

        # Default ranges
        if min_value is None:
            min_value = config.min_amount * 10
        if max_value is None:
            max_value = min(config.max_amount / 10, Decimal("10000"))

        amounts = []
        for i in range(count):
            # Use counter + i for determinism
            deterministic_seed = self.seed + self.counter + i
            random.seed(deterministic_seed)

            # Generate random float in range
            random_float = random.uniform(float(min_value), float(max_value))

            # Convert to Decimal with appropriate precision
            amount_str = f"{random_float:.{config.decimal_places}f}"
            amounts.append(Decimal(amount_str))

        # Reset seed
        random.seed(self.seed)
        self._next_counter()

        return amounts

    def create(
        self,
        currency: CurrencyCode,
        amount_type: str = "bug_revealing"
    ) -> List[Decimal]:
        """
        Factory create method (implements BaseFactory.create).

        Args:
            currency: Currency code
            amount_type: Type of amounts ('bug_revealing', 'safe', 'boundary', 'random')

        Returns:
            List of amounts
        """
        if amount_type == "bug_revealing":
            return self.create_bug_revealing_amounts(currency)
        elif amount_type == "safe":
            return self.create_safe_amounts(currency)
        elif amount_type == "boundary":
            return self.create_boundary_amounts(currency)
        elif amount_type == "random":
            return self.create_random_amounts(currency)
        else:
            raise ValueError(f"Unknown amount_type: {amount_type}")
```

---

## 5. Exchange Rate Factory

### 5.1 Implementation

```python
class ExchangeRateFactory(BaseFactory):
    """Factory for generating FX rate fixtures."""

    def __init__(self, seed: int = 42, worker_id: str = "master"):
        super().__init__(seed, worker_id)
        self.base_rates = self._load_base_rates()

    def _load_base_rates(self) -> Dict[str, Decimal]:
        """
        Load base FX rates (same as CurrencyAgent defaults).

        Returns:
            Dict of "FROM_TO" -> rate
        """
        return {
            # EUR conversions
            "EUR_USD": Decimal("1.0850"),
            "EUR_GBP": Decimal("0.8650"),
            "EUR_BRL": Decimal("5.3750"),
            "EUR_CLP": Decimal("1052.00"),  # THE CRITICAL RATE
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

            # Reverse rates
            "CLP_EUR": Decimal("0.0009506"),
            "JPY_EUR": Decimal("0.0062034"),
            "COP_EUR": Decimal("0.0002353"),
            "JPY_USD": Decimal("0.00672654"),
            "CLP_USD": Decimal("0.00103150"),
            "KRW_USD": Decimal("0.00075089"),

            # Zero to zero
            "JPY_CLP": Decimal("6.5200"),

            # Three to three
            "KWD_BHD": Decimal("1.2210"),
        }

    def get_base_rate(
        self,
        from_currency: CurrencyCode,
        to_currency: CurrencyCode
    ) -> Decimal:
        """Get base FX rate for currency pair."""
        if from_currency == to_currency:
            return Decimal("1.0")

        rate_key = f"{from_currency.value}_{to_currency.value}"
        if rate_key not in self.base_rates:
            raise ValueError(f"Base rate not defined for {rate_key}")

        return self.base_rates[rate_key]

    def create_rate_with_high_precision(
        self,
        from_currency: CurrencyCode,
        to_currency: CurrencyCode
    ) -> Decimal:
        """
        Create rate with >4 decimal places (edge case).

        Example: 1052.00 -> 1052.12345
        """
        base_rate = self.get_base_rate(from_currency, to_currency)
        # Add small random precision
        precision_adjustment = Decimal(str(random.random() * 0.2)).quantize(
            Decimal("0.00001")
        )
        return base_rate + precision_adjustment

    def create_rate_scenarios(
        self,
        from_currency: CurrencyCode,
        to_currency: CurrencyCode
    ) -> Dict[str, Decimal]:
        """
        Create multiple rate scenarios for testing.

        Returns:
            Dict of scenario_name -> rate
        """
        base_rate = self.get_base_rate(from_currency, to_currency)

        return {
            "normal": base_rate,
            "high_precision": self.create_rate_with_high_precision(from_currency, to_currency),
            "slightly_higher": base_rate * Decimal("1.02"),
            "slightly_lower": base_rate * Decimal("0.98"),
            "extreme_high": base_rate * Decimal("1.50"),
            "extreme_low": base_rate * Decimal("0.50"),
        }

    def create_stale_rate_scenarios(
        self,
        from_currency: CurrencyCode,
        to_currency: CurrencyCode
    ) -> List[Tuple[Decimal, datetime]]:
        """
        Create rates with different timestamps for staleness testing.

        Returns:
            List of (rate, timestamp) tuples
        """
        base_rate = self.get_base_rate(from_currency, to_currency)
        now = datetime.utcnow()

        return [
            (base_rate, now),  # Fresh (0 sec old)
            (base_rate, now - timedelta(minutes=1)),  # 1 min old
            (base_rate, now - timedelta(minutes=5)),  # 5 min old (stale)
            (base_rate, now - timedelta(minutes=30)),  # 30 min old (very stale)
            (base_rate, now - timedelta(hours=1)),  # 1 hour old (expired)
        ]

    def create(
        self,
        from_currency: CurrencyCode,
        to_currency: CurrencyCode,
        scenario: str = "normal"
    ) -> Decimal:
        """
        Factory create method (implements BaseFactory.create).

        Args:
            from_currency: Source currency
            to_currency: Target currency
            scenario: Rate scenario type

        Returns:
            FX rate
        """
        if scenario == "normal":
            return self.get_base_rate(from_currency, to_currency)
        elif scenario == "high_precision":
            return self.create_rate_with_high_precision(from_currency, to_currency)
        else:
            scenarios = self.create_rate_scenarios(from_currency, to_currency)
            if scenario not in scenarios:
                raise ValueError(f"Unknown scenario: {scenario}")
            return scenarios[scenario]
```

---

## 6. Transaction Factory

### 6.1 Implementation

```python
class TransactionFactory(BaseFactory):
    """Factory for generating test transactions."""

    def __init__(
        self,
        currency_agent: CurrencyAgent,
        seed: int = 42,
        worker_id: str = "master"
    ):
        super().__init__(seed, worker_id)
        self.currency_agent = currency_agent

    def create_authorization_request(
        self,
        amount: Decimal,
        currency: CurrencyCode,
        settlement_currency: Optional[CurrencyCode] = None,
        merchant_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        payment_method: PaymentMethod = PaymentMethod.CARD,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuthorizationRequest:
        """
        Create a single authorization request.

        Args:
            amount: Transaction amount
            currency: Original currency
            settlement_currency: Optional settlement currency
            merchant_id: Optional merchant ID (auto-generated if None)
            customer_id: Optional customer ID (auto-generated if None)
            payment_method: Payment method type
            metadata: Optional metadata dict

        Returns:
            Authorization request
        """
        counter = self._next_counter()

        return AuthorizationRequest(
            merchant_id=merchant_id or f"merchant_{self.worker_id}_{counter:08d}",
            customer_id=customer_id or f"customer_{self.worker_id}_{counter:08d}",
            amount=amount,
            currency=currency,
            settlement_currency=settlement_currency,
            payment_method=payment_method,
            idempotency_key=f"idempotency_{self.worker_id}_{counter:016d}",
            metadata=metadata or {"test_id": counter, "worker": self.worker_id}
        )

    def create_bug_revealing_transaction(
        self,
        from_currency: CurrencyCode = CurrencyCode.EUR,
        to_currency: CurrencyCode = CurrencyCode.CLP,
        amount: Decimal = Decimal("49.99"),
    ) -> AuthorizationRequest:
        """
        Create the exact transaction that reveals the €2.3M bug.

        Default: €49.99 → CLP at rate 1052.00

        Args:
            from_currency: Source currency (default EUR)
            to_currency: Target currency (default CLP)
            amount: Amount (default 49.99)

        Returns:
            Authorization request
        """
        return self.create_authorization_request(
            amount=amount,
            currency=from_currency,
            settlement_currency=to_currency,
            merchant_id="merchant_bug_reproduction",
            customer_id="customer_bug_reproduction",
            metadata={
                "test_type": "bug_reproduction",
                "incident": "2.3M_euro_rounding_bug",
            }
        )

    def create_batch(
        self,
        currency_pairs: List[Tuple[CurrencyCode, CurrencyCode]],
        amounts: List[Decimal],
    ) -> List[AuthorizationRequest]:
        """
        Create a batch of transactions for all combinations.

        Args:
            currency_pairs: List of (from, to) currency pairs
            amounts: List of amounts to test

        Returns:
            List of authorization requests
        """
        transactions = []
        for from_curr, to_curr in currency_pairs:
            for amount in amounts:
                # Skip if amount invalid for source currency
                config = get_currency(from_curr)
                if amount < config.min_amount or amount > config.max_amount:
                    continue

                transactions.append(
                    self.create_authorization_request(
                        amount=amount,
                        currency=from_curr,
                        settlement_currency=to_curr if from_curr != to_curr else None,
                    )
                )
        return transactions

    def create_for_decimal_combination(
        self,
        from_decimals: int,
        to_decimals: int,
        amount_factory: AmountFactory,
    ) -> List[AuthorizationRequest]:
        """
        Create transactions for a specific decimal type combination.

        Args:
            from_decimals: Source currency decimal places
            to_decimals: Target currency decimal places
            amount_factory: Amount factory instance

        Returns:
            List of authorization requests
        """
        pairs = CurrencyPairFactory.get_pairs_by_decimal_type(from_decimals, to_decimals)
        transactions = []

        for from_curr, to_curr in pairs:
            # Generate appropriate amounts based on source currency decimals
            if from_decimals == 2:
                amounts = amount_factory.create_bug_revealing_amounts(from_curr)
            elif from_decimals == 0:
                amounts = [Decimal("1000"), Decimal("10000"), Decimal("100000")]
            else:  # 3 decimals
                amounts = amount_factory.create_bug_revealing_amounts(from_curr)

            for amount in amounts:
                transactions.append(
                    self.create_authorization_request(
                        amount=amount,
                        currency=from_curr,
                        settlement_currency=to_curr if from_curr != to_curr else None,
                    )
                )

        return transactions

    def create(self, **kwargs) -> AuthorizationRequest:
        """
        Factory create method (implements BaseFactory.create).

        Delegates to create_authorization_request.
        """
        return self.create_authorization_request(**kwargs)
```

---

## 7. Webhook Factory

### 7.1 Implementation

```python
class WebhookFactory(BaseFactory):
    """Factory for generating webhook payloads."""

    def create_webhook_payload(
        self,
        transaction: Transaction,
        event_type: str = "payment.authorized",
    ) -> WebhookPayload:
        """
        Create webhook payload from transaction.

        Args:
            transaction: Transaction object
            event_type: Webhook event type

        Returns:
            Webhook payload
        """
        return WebhookPayload(
            event_type=event_type,
            transaction_id=transaction.transaction_id,
            status=transaction.status,
            amount=transaction.authorized_amount,
            currency=transaction.settlement_currency or transaction.original_currency,
            settlement_amount=transaction.settlement_amount,
            settlement_currency=transaction.settlement_currency,
            metadata={
                "merchant_id": transaction.merchant_id,
                "customer_id": transaction.customer_id,
                "fx_rate": str(transaction.fx_rate) if transaction.fx_rate else None,
            }
        )

    def create(self, transaction: Transaction, **kwargs) -> WebhookPayload:
        """Factory create method (implements BaseFactory.create)."""
        return self.create_webhook_payload(transaction, **kwargs)
```

---

## 8. Test Scenario Factory (Orchestrator)

### 8.1 Implementation

```python
class TestScenarioFactory(BaseFactory):
    """
    Orchestrator factory that coordinates all other factories.

    Use this for complex test scenarios that need multiple factories.
    """

    def __init__(
        self,
        currency_agent: CurrencyAgent,
        seed: int = 42,
        worker_id: str = "master"
    ):
        super().__init__(seed, worker_id)
        self.currency_agent = currency_agent
        self.amount_factory = AmountFactory(seed, worker_id)
        self.rate_factory = ExchangeRateFactory(seed, worker_id)
        self.transaction_factory = TransactionFactory(currency_agent, seed, worker_id)

    def create_critical_test_suite(self) -> List[AuthorizationRequest]:
        """
        Create complete test suite for P0 critical scenarios.

        Returns:
            List of authorization requests covering all critical pairs
        """
        critical_pairs = CurrencyPairFactory.create_critical_pairs()
        transactions = []

        for from_curr, to_curr in critical_pairs:
            # Get bug-revealing amounts for this currency
            amounts = self.amount_factory.create_bug_revealing_amounts(from_curr)

            for amount in amounts:
                transactions.append(
                    self.transaction_factory.create_authorization_request(
                        amount=amount,
                        currency=from_curr,
                        settlement_currency=to_curr,
                    )
                )

        return transactions

    def create_decimal_combination_suite(self) -> List[AuthorizationRequest]:
        """
        Create test suite covering all decimal type combinations.

        Returns:
            List of authorization requests for all 9 decimal combinations
        """
        all_combos = CurrencyPairFactory.create_all_decimal_combinations()
        transactions = []

        for from_curr, to_curr, combo_type in all_combos:
            # Choose amount based on combination type
            if "0dec" in combo_type:
                if "to_0dec" in combo_type:
                    # Two-decimal to zero-decimal (CRITICAL)
                    amounts = self.amount_factory.create_bug_revealing_amounts(from_curr)
                else:
                    # From zero-decimal
                    amounts = [Decimal("1000"), Decimal("10000")]
            else:
                amounts = self.amount_factory.create_bug_revealing_amounts(from_curr)

            for amount in amounts:
                transactions.append(
                    self.transaction_factory.create_authorization_request(
                        amount=amount,
                        currency=from_curr,
                        settlement_currency=to_curr if from_curr != to_curr else None,
                        metadata={"decimal_combination": combo_type}
                    )
                )

        return transactions

    def create_boundary_test_suite(
        self,
        currency_pairs: Optional[List[Tuple[CurrencyCode, CurrencyCode]]] = None
    ) -> List[AuthorizationRequest]:
        """
        Create test suite for boundary values.

        Args:
            currency_pairs: Optional list of pairs (defaults to critical pairs)

        Returns:
            List of authorization requests with boundary amounts
        """
        pairs = currency_pairs or CurrencyPairFactory.create_critical_pairs()
        transactions = []

        for from_curr, to_curr in pairs:
            boundary_amounts = self.amount_factory.create_boundary_amounts(from_curr)

            for amount in boundary_amounts:
                transactions.append(
                    self.transaction_factory.create_authorization_request(
                        amount=amount,
                        currency=from_curr,
                        settlement_currency=to_curr if from_curr != to_curr else None,
                        metadata={"test_type": "boundary"}
                    )
                )

        return transactions

    def create_chaos_test_suite(
        self,
        count: int = 100,
        currency_pairs: Optional[List[Tuple[CurrencyCode, CurrencyCode]]] = None
    ) -> List[AuthorizationRequest]:
        """
        Create chaos test suite with random amounts (seeded).

        Args:
            count: Number of random tests to generate
            currency_pairs: Optional list of pairs (defaults to all priority pairs)

        Returns:
            List of authorization requests with random amounts
        """
        pairs = currency_pairs or (
            CurrencyPairFactory.create_critical_pairs() +
            CurrencyPairFactory.create_high_priority_pairs()
        )

        transactions = []
        tests_per_pair = max(1, count // len(pairs))

        for from_curr, to_curr in pairs:
            random_amounts = self.amount_factory.create_random_amounts(
                from_curr,
                count=tests_per_pair
            )

            for amount in random_amounts:
                transactions.append(
                    self.transaction_factory.create_authorization_request(
                        amount=amount,
                        currency=from_curr,
                        settlement_currency=to_curr if from_curr != to_curr else None,
                        metadata={"test_type": "chaos"}
                    )
                )

        return transactions

    def create(self, scenario_type: str = "critical", **kwargs) -> List[AuthorizationRequest]:
        """
        Factory create method (implements BaseFactory.create).

        Args:
            scenario_type: Type of scenario ('critical', 'decimal_combos', 'boundary', 'chaos')

        Returns:
            List of authorization requests
        """
        if scenario_type == "critical":
            return self.create_critical_test_suite()
        elif scenario_type == "decimal_combos":
            return self.create_decimal_combination_suite()
        elif scenario_type == "boundary":
            return self.create_boundary_test_suite(**kwargs)
        elif scenario_type == "chaos":
            return self.create_chaos_test_suite(**kwargs)
        else:
            raise ValueError(f"Unknown scenario_type: {scenario_type}")
```

---

## 9. Pytest Fixtures for Factories

### 9.1 conftest.py Integration

```python
# tests/conftest.py

import pytest
from framework.agents.currency_agent import CurrencyAgent
from framework.factories import (
    AmountFactory,
    ExchangeRateFactory,
    TransactionFactory,
    TestScenarioFactory,
)

@pytest.fixture(scope="session")
def currency_agent():
    """Session-scoped currency agent."""
    return CurrencyAgent()

@pytest.fixture(scope="session")
def worker_id(request):
    """Get pytest-xdist worker ID."""
    if hasattr(request.config, 'workerinput'):
        return request.config.workerinput['workerid']
    return "master"

@pytest.fixture(scope="function")
def amount_factory(worker_id):
    """Function-scoped amount factory (isolated per test)."""
    return AmountFactory(seed=42, worker_id=worker_id)

@pytest.fixture(scope="function")
def rate_factory(worker_id):
    """Function-scoped exchange rate factory."""
    return ExchangeRateFactory(seed=42, worker_id=worker_id)

@pytest.fixture(scope="function")
def transaction_factory(currency_agent, worker_id):
    """Function-scoped transaction factory."""
    return TransactionFactory(
        currency_agent=currency_agent,
        seed=42,
        worker_id=worker_id
    )

@pytest.fixture(scope="function")
def scenario_factory(currency_agent, worker_id):
    """Function-scoped test scenario factory (orchestrator)."""
    return TestScenarioFactory(
        currency_agent=currency_agent,
        seed=42,
        worker_id=worker_id
    )

# Pre-built test data fixtures
@pytest.fixture(scope="session")
def critical_currency_pairs():
    """Critical currency pairs for P0 testing."""
    from framework.factories import CurrencyPairFactory
    return CurrencyPairFactory.create_critical_pairs()

@pytest.fixture(scope="session")
def bug_revealing_amount():
    """The exact amount from the €2.3M incident."""
    from decimal import Decimal
    return Decimal("49.99")
```

---

## 10. Usage Examples

### 10.1 Basic Usage

```python
# Test using individual factories
def test_euro_to_clp_conversion(transaction_factory, currency_agent):
    # Create bug-revealing transaction
    request = transaction_factory.create_bug_revealing_transaction()

    # Execute
    from framework.agents.payment_agent import PaymentAgent
    payment_agent = PaymentAgent(currency_agent, simulate_bug=False)
    response = payment_agent.authorize_payment(request)

    # Assert correct conversion
    assert response.status == TransactionStatus.AUTHORIZED
    assert response.authorized_amount == Decimal("52594")  # Correct value
```

### 10.2 Orchestrated Scenarios

```python
# Test using scenario factory
def test_all_critical_pairs(scenario_factory):
    # Generate complete P0 test suite
    critical_tests = scenario_factory.create_critical_test_suite()

    assert len(critical_tests) > 0
    # Execute all tests...

def test_decimal_combinations(scenario_factory):
    # Generate all decimal combination tests
    combo_tests = scenario_factory.create_decimal_combination_suite()

    # Verify all 9 combinations present
    combo_types = {test.metadata.get("decimal_combination") for test in combo_tests}
    assert "2dec_to_0dec" in combo_types
    assert "2dec_to_2dec" in combo_types
    assert "2dec_to_3dec" in combo_types
    # ... etc
```

### 10.3 Parallel Execution

```python
# Run with pytest-xdist
# pytest -n auto tests/

def test_isolated_transaction(transaction_factory, worker_id):
    # Each worker gets unique IDs automatically
    request = transaction_factory.create_authorization_request(
        amount=Decimal("100.00"),
        currency=CurrencyCode.EUR,
        settlement_currency=CurrencyCode.USD,
    )

    # IDs will be unique per worker (e.g., merchant_gw0_00000001)
    assert worker_id in request.merchant_id
    assert worker_id in request.customer_id
```

---

## 11. Factory Testing

### 11.1 Unit Tests for Factories

```python
# tests/unit/test_factories.py

def test_amount_factory_determinism():
    """Verify amount factory produces deterministic results."""
    factory1 = AmountFactory(seed=42, worker_id="test")
    factory2 = AmountFactory(seed=42, worker_id="test")

    amounts1 = factory1.create_random_amounts(CurrencyCode.EUR, count=10)
    amounts2 = factory2.create_random_amounts(CurrencyCode.EUR, count=10)

    assert amounts1 == amounts2  # Same seed = same results

def test_transaction_factory_unique_ids():
    """Verify transaction factory generates unique IDs."""
    factory = TransactionFactory(currency_agent, seed=42, worker_id="test")

    request1 = factory.create_authorization_request(
        amount=Decimal("100.00"),
        currency=CurrencyCode.EUR,
    )
    request2 = factory.create_authorization_request(
        amount=Decimal("200.00"),
        currency=CurrencyCode.EUR,
    )

    assert request1.merchant_id != request2.merchant_id
    assert request1.customer_id != request2.customer_id
    assert request1.idempotency_key != request2.idempotency_key

def test_scenario_factory_coverage():
    """Verify scenario factory covers all critical pairs."""
    factory = TestScenarioFactory(currency_agent, seed=42, worker_id="test")

    critical_tests = factory.create_critical_test_suite()

    # Extract unique currency pairs
    pairs = {
        (test.currency, test.settlement_currency)
        for test in critical_tests
    }

    # Verify all P0 pairs present
    expected_pairs = CurrencyPairFactory.create_critical_pairs()
    assert len(pairs) == len(expected_pairs)
```

---

## 12. Performance Considerations

### 12.1 Factory Performance

| Factory | Creation Time (1 object) | Batch Creation (100 objects) |
|---------|-------------------------|------------------------------|
| AmountFactory | <1ms | <10ms |
| ExchangeRateFactory | <1ms | <5ms |
| TransactionFactory | <2ms | <50ms |
| TestScenarioFactory | <5ms | <200ms (full suite) |

### 12.2 Optimization Tips

1. **Reuse factories**: Create once per test, reuse for multiple objects
2. **Batch operations**: Use `create_batch()` instead of loops
3. **Session-scoped fixtures**: Use for immutable data (currency pairs, base rates)
4. **Function-scoped factories**: Use for mutable state (counters, transactions)
5. **Lazy loading**: Load base rates only when needed

---

## Summary

This factory architecture provides:

- **Deterministic test data** (seeded randomness)
- **Isolated parallel execution** (worker-specific IDs)
- **Comprehensive coverage** (all currency pairs + decimals)
- **Type-safe generation** (Pydantic models)
- **Composable patterns** (factories can be combined)
- **Easy maintenance** (add new currencies by extending base rates)

**Key Factories**:
1. `CurrencyPairFactory` - Currency pair combinations
2. `AmountFactory` - Test amounts (bug-revealing, safe, boundary, random)
3. `ExchangeRateFactory` - FX rate fixtures (normal, high-precision, stale)
4. `TransactionFactory` - Authorization requests
5. `TestScenarioFactory` - Orchestrated test suites

---

**Document Version**: 1.0
**Last Updated**: 2026-02-25
**Owner**: Data Architect (Principal)
**Review Cycle**: Quarterly or when adding new factories
