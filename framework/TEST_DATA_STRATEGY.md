# Test Data Strategy: Silent Currency Bug Prevention

## Executive Summary

This document defines a comprehensive strategy for generating, managing, and isolating test data to achieve thorough coverage of currency conversion scenarios. The strategy prioritizes edge cases that would expose the €2.3M rounding bug and ensures deterministic, reproducible test execution.

**Goal**: Generate test data that covers all critical currency pair combinations, edge case amounts, and FX rate scenarios with minimal manual effort and maximum bug-detection capability.

---

## 1. Test Data Principles

### 1.1 Core Principles

1. **Deterministic**: Same input always produces same output
2. **Isolated**: Tests don't interfere with each other
3. **Comprehensive**: Cover all decimal type combinations
4. **Realistic**: Use actual FX rates and amounts from production
5. **Edge-case focused**: Prioritize bug-revealing scenarios
6. **Maintainable**: Easy to add new currencies and scenarios

### 1.2 Test Data Categories

| Category | Purpose | Examples |
|----------|---------|----------|
| Happy Path | Verify standard conversions work | EUR 100.00 → USD |
| Zero-Decimal Currency | Detect rounding bugs | EUR 49.99 → CLP (THE BUG) |
| Three-Decimal Currency | Verify precision handling | EUR 100.00 → KWD |
| Boundary Amounts | Test min/max limits | 0.01 EUR, 999,999.99 EUR |
| High-Precision Rates | Test >4 decimal FX rates | Rate: 1052.12345 |
| Extreme Rates | Test very large/small rates | 1 JPY → IDR (130.5) |
| Stale Rates | Verify rate freshness checks | Rate older than 5 min |
| Missing Rates | Test error handling | EUR → XYZ (invalid) |

---

## 2. Currency Pair Test Matrix Strategy

### 2.1 Risk-Based Prioritization

Not all currency pairs are equal. Prioritize testing based on:
1. **Historical bugs** (zero-decimal currencies)
2. **Transaction volume** (EUR, USD, GBP most common)
3. **Decimal type combinations** (mixed decimal places)
4. **Regulatory requirements** (certain regions mandate specific currencies)

### 2.2 Prioritized Currency Pairs

#### P0 - Critical (Must Test)
These combinations caused or could cause the €2.3M bug:

| From | To | Risk Factor | Test Priority |
|------|----|-----------|----|
| EUR | CLP | Zero-decimal settlement, high rate | ⚠️ CRITICAL |
| EUR | COP | Zero-decimal settlement, high rate | ⚠️ CRITICAL |
| EUR | JPY | Zero-decimal settlement, medium rate | ⚠️ CRITICAL |
| EUR | KRW | Zero-decimal settlement, high rate | ⚠️ CRITICAL |
| USD | CLP | Zero-decimal settlement, high rate | ⚠️ CRITICAL |
| USD | COP | Zero-decimal settlement, high rate | ⚠️ CRITICAL |
| USD | JPY | Zero-decimal settlement, common pair | ⚠️ CRITICAL |
| GBP | JPY | Zero-decimal settlement, common pair | ⚠️ CRITICAL |

**Why Critical**: Any two-decimal → zero-decimal conversion with rates >100 can exhibit the bug.

#### P1 - High Priority
Important for comprehensive coverage:

| From | To | Risk Factor | Test Priority |
|------|----|-----------|----|
| EUR | USD | Most common pair, standard 2-decimal | HIGH |
| EUR | GBP | Common pair, standard 2-decimal | HIGH |
| EUR | BRL | Emerging market, high rate | HIGH |
| EUR | MXN | Latin America, medium rate | HIGH |
| USD | BRL | Emerging market | HIGH |
| USD | MXN | Latin America | HIGH |
| EUR | KWD | Three-decimal target | HIGH |
| EUR | BHD | Three-decimal target | HIGH |
| EUR | OMR | Three-decimal target | HIGH |

#### P2 - Medium Priority
Good to have for completeness:

| From | To | Risk Factor | Test Priority |
|------|----|-----------|----|
| GBP | USD | Reverse common pair | MEDIUM |
| GBP | EUR | Reverse common pair | MEDIUM |
| BRL | USD | Reverse emerging market | MEDIUM |
| JPY | USD | Reverse zero-decimal | MEDIUM |
| CLP | EUR | Reverse zero-decimal (small rate) | MEDIUM |
| CNY | USD | Large market | MEDIUM |
| INR | USD | Large market | MEDIUM |

#### P3 - Low Priority (Smoke Tests Only)
Cover with basic scenarios:

- AUD ↔ USD
- CAD ↔ USD
- SGD ↔ USD
- Any same-currency conversion (passthrough)

### 2.3 Decimal Type Combination Matrix

Test all combinations of source/target decimal types:

| Source Type | Target Type | Example Pair | Bug Risk | Test Count |
|-------------|-------------|--------------|----------|------------|
| 2-decimal | 0-decimal | EUR → CLP | ⚠️ HIGH | 20+ tests |
| 2-decimal | 2-decimal | EUR → USD | MEDIUM | 10 tests |
| 2-decimal | 3-decimal | EUR → KWD | MEDIUM | 10 tests |
| 0-decimal | 2-decimal | JPY → EUR | LOW | 5 tests |
| 0-decimal | 0-decimal | JPY → CLP | LOW | 5 tests |
| 3-decimal | 2-decimal | KWD → EUR | LOW | 5 tests |
| 3-decimal | 3-decimal | KWD → BHD | LOW | 3 tests |
| 3-decimal | 0-decimal | KWD → JPY | LOW | 3 tests |
| 0-decimal | 3-decimal | JPY → KWD | LOW | 3 tests |

**Total Minimum Test Cases**: ~64 currency pair scenarios

---

## 3. Edge Case Amount Generation

### 3.1 Amount Categories

For each currency pair, test these amount scenarios:

#### Minimum Amounts
```python
# Two-decimal currencies
EUR: 0.01, 0.05, 0.10, 0.99
USD: 0.01, 0.05, 0.10, 0.99

# Zero-decimal currencies
CLP: 1, 5, 10, 99
JPY: 1, 5, 10, 99
COP: 1, 5, 10, 99

# Three-decimal currencies
KWD: 0.001, 0.005, 0.010, 0.999
BHD: 0.001, 0.005, 0.010, 0.999
```

#### Boundary Amounts
```python
# Just above minimum
EUR: 0.02, 0.11
CLP: 2, 11
KWD: 0.002, 0.011

# Just below maximum
EUR: 999999.98, 999999.99
CLP: 999999998, 999999999
KWD: 999999.998, 999999.999
```

#### Bug-Revealing Amounts (The Critical Ones)
```python
# Amounts that exhibit the bug when rounded prematurely
EUR: 49.99, 99.99, 149.99, 199.99  # Round to whole number loses cents
EUR: 10.01, 20.01, 30.01  # Round loses 1 cent
EUR: 0.99, 1.99, 2.99  # Round loses cents entirely

# Amounts that DON'T exhibit bug (for negative tests)
EUR: 50.00, 100.00, 150.00  # Already whole numbers
EUR: 0.50, 1.00, 2.00  # Round to same value
```

#### Random Amounts (for chaos testing)
```python
# Generate 100 random amounts per currency in realistic ranges
EUR: random between 10.00 and 10000.00
USD: random between 10.00 and 10000.00
CLP: random between 10000 and 10000000
JPY: random between 1000 and 1000000
KWD: random between 10.000 and 10000.000
```

### 3.2 Amount Generation Functions

```python
from decimal import Decimal
from typing import List, Tuple
import random

def generate_minimum_amounts(currency: CurrencyCode) -> List[Decimal]:
    """Generate minimum amount test cases."""
    config = get_currency(currency)
    min_amount = config.min_amount

    if config.decimal_places == 0:
        return [Decimal("1"), Decimal("5"), Decimal("10"), Decimal("99")]
    elif config.decimal_places == 2:
        return [Decimal("0.01"), Decimal("0.05"), Decimal("0.10"), Decimal("0.99")]
    elif config.decimal_places == 3:
        return [Decimal("0.001"), Decimal("0.005"), Decimal("0.010"), Decimal("0.999")]

def generate_bug_revealing_amounts(currency: CurrencyCode) -> List[Decimal]:
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
            Decimal("0.99"),
            Decimal("1.99"),
            Decimal("2.99"),
        ]
    elif config.decimal_places == 3:
        return [
            Decimal("49.999"),
            Decimal("99.999"),
            Decimal("10.001"),
            Decimal("0.999"),
        ]
    else:
        # Zero-decimal currencies don't have fractional parts
        return []

def generate_safe_amounts(currency: CurrencyCode) -> List[Decimal]:
    """
    Generate amounts that DON'T reveal the bug (for negative tests).

    These amounts are already rounded, so premature rounding doesn't matter.
    """
    config = get_currency(currency)

    if config.decimal_places == 2:
        return [
            Decimal("50.00"),
            Decimal("100.00"),
            Decimal("150.00"),
            Decimal("0.50"),
            Decimal("1.00"),
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

def generate_random_amounts(
    currency: CurrencyCode,
    count: int = 20,
    min_value: Decimal = None,
    max_value: Decimal = None,
    seed: int = 42
) -> List[Decimal]:
    """
    Generate random realistic amounts for chaos testing.

    Args:
        currency: Currency code
        count: Number of random amounts to generate
        min_value: Minimum value (defaults to currency min * 10)
        max_value: Maximum value (defaults to currency max / 10)
        seed: Random seed for reproducibility

    Returns:
        List of random amounts
    """
    random.seed(seed)
    config = get_currency(currency)

    # Default ranges
    if min_value is None:
        min_value = config.min_amount * 10
    if max_value is None:
        max_value = min(config.max_amount / 10, Decimal("10000"))

    amounts = []
    for _ in range(count):
        # Generate random float in range
        random_float = random.uniform(float(min_value), float(max_value))

        # Convert to Decimal with appropriate precision
        amount_str = f"{random_float:.{config.decimal_places}f}"
        amounts.append(Decimal(amount_str))

    return amounts
```

---

## 4. Exchange Rate Scenarios

### 4.1 Rate Categories

| Category | Description | Example | Purpose |
|----------|-------------|---------|---------|
| Normal Rates | Standard market rates | EUR/USD: 1.0850 | Happy path |
| High Rates | Large conversion multipliers | EUR/CLP: 1052.00 | Bug amplification |
| Low Rates | Small conversion multipliers | JPY/EUR: 0.0062 | Precision loss |
| High-Precision | >4 decimal places | EUR/CLP: 1052.12345 | Precision handling |
| Extreme High | Very large rates | IDR/JPY: >100000 | Overflow protection |
| Extreme Low | Very small rates | <0.0001 | Underflow protection |
| Stale Rates | Old timestamps | Rate from 1 hour ago | Freshness validation |
| Volatile Rates | Rapidly changing | Multiple rates in 1 min | Race condition detection |

### 4.2 Rate Generation Functions

```python
def generate_fx_rates_for_pair(
    from_currency: CurrencyCode,
    to_currency: CurrencyCode,
    base_rate: Decimal
) -> Dict[str, Decimal]:
    """
    Generate multiple rate scenarios for a currency pair.

    Args:
        from_currency: Source currency
        to_currency: Target currency
        base_rate: Standard market rate

    Returns:
        Dict of scenario name to rate
    """
    return {
        "normal": base_rate,
        "high_precision": base_rate * Decimal("1.00001234"),  # Add precision
        "slightly_higher": base_rate * Decimal("1.02"),
        "slightly_lower": base_rate * Decimal("0.98"),
        "extreme_high": base_rate * Decimal("1.50"),
        "extreme_low": base_rate * Decimal("0.50"),
    }

def generate_stale_rate_scenarios() -> List[Tuple[Decimal, datetime]]:
    """
    Generate rates with different timestamps for staleness testing.

    Returns:
        List of (rate, timestamp) tuples
    """
    now = datetime.utcnow()
    return [
        (Decimal("1052.00"), now),  # Fresh (0 sec old)
        (Decimal("1052.00"), now - timedelta(minutes=1)),  # 1 min old
        (Decimal("1052.00"), now - timedelta(minutes=5)),  # 5 min old (stale)
        (Decimal("1052.00"), now - timedelta(minutes=30)),  # 30 min old (very stale)
        (Decimal("1052.00"), now - timedelta(hours=1)),  # 1 hour old (expired)
    ]
```

---

## 5. Test Data Factories

### 5.1 Factory Design Patterns

Use factories to generate consistent, isolated test data:

```python
class CurrencyPairFactory:
    """Factory for generating currency pair test scenarios."""

    @staticmethod
    def create_critical_pairs() -> List[Tuple[CurrencyCode, CurrencyCode]]:
        """Generate P0 critical currency pairs."""
        return [
            (CurrencyCode.EUR, CurrencyCode.CLP),
            (CurrencyCode.EUR, CurrencyCode.COP),
            (CurrencyCode.EUR, CurrencyCode.JPY),
            (CurrencyCode.EUR, CurrencyCode.KRW),
            (CurrencyCode.USD, CurrencyCode.CLP),
            (CurrencyCode.USD, CurrencyCode.COP),
            (CurrencyCode.USD, CurrencyCode.JPY),
            (CurrencyCode.GBP, CurrencyCode.JPY),
        ]

    @staticmethod
    def create_all_decimal_combinations() -> List[Tuple[CurrencyCode, CurrencyCode, str]]:
        """Generate all source/target decimal type combinations."""
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

            # 3-decimal → 2-decimal
            (CurrencyCode.KWD, CurrencyCode.EUR, "3dec_to_2dec"),
            (CurrencyCode.BHD, CurrencyCode.USD, "3dec_to_2dec"),
        ]


class TransactionFactory:
    """Factory for generating test transactions."""

    def __init__(self, currency_agent: CurrencyAgent):
        self.currency_agent = currency_agent
        self.transaction_counter = 0

    def create_transaction(
        self,
        amount: Decimal,
        currency: CurrencyCode,
        settlement_currency: CurrencyCode = None,
        merchant_id: str = None,
        customer_id: str = None,
    ) -> AuthorizationRequest:
        """
        Create a test transaction with deterministic IDs.

        Args:
            amount: Transaction amount
            currency: Original currency
            settlement_currency: Optional settlement currency
            merchant_id: Optional merchant ID (auto-generated if None)
            customer_id: Optional customer ID (auto-generated if None)

        Returns:
            Authorization request
        """
        self.transaction_counter += 1

        return AuthorizationRequest(
            merchant_id=merchant_id or f"merchant_{self.transaction_counter:04d}",
            customer_id=customer_id or f"customer_{self.transaction_counter:04d}",
            amount=amount,
            currency=currency,
            settlement_currency=settlement_currency,
            payment_method=PaymentMethod.CARD,
            idempotency_key=f"test_idempotency_{self.transaction_counter:08d}",
            metadata={"test_id": self.transaction_counter}
        )

    def create_bug_revealing_transaction(
        self,
        from_currency: CurrencyCode = CurrencyCode.EUR,
        to_currency: CurrencyCode = CurrencyCode.CLP,
    ) -> AuthorizationRequest:
        """
        Create the exact transaction that reveals the €2.3M bug.

        Default: €49.99 → CLP at rate 1052.00
        """
        return self.create_transaction(
            amount=Decimal("49.99"),  # THE INCIDENT AMOUNT
            currency=from_currency,
            settlement_currency=to_currency,
            merchant_id="merchant_incident_reproduction",
            customer_id="customer_incident_reproduction",
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
                transactions.append(
                    self.create_transaction(
                        amount=amount,
                        currency=from_curr,
                        settlement_currency=to_curr,
                    )
                )
        return transactions
```

### 5.2 Fixture Management

```python
# conftest.py - Pytest fixtures for test data

import pytest
from framework.agents.currency_agent import CurrencyAgent
from framework.agents.payment_agent import PaymentAgent

@pytest.fixture(scope="session")
def currency_agent():
    """Session-scoped currency agent with test FX rates."""
    return CurrencyAgent()

@pytest.fixture(scope="function")
def payment_agent(currency_agent):
    """Function-scoped payment agent (isolated per test)."""
    return PaymentAgent(currency_agent=currency_agent, simulate_bug=False)

@pytest.fixture(scope="function")
def payment_agent_with_bug(currency_agent):
    """Function-scoped payment agent simulating the bug."""
    return PaymentAgent(currency_agent=currency_agent, simulate_bug=True)

@pytest.fixture(scope="function")
def transaction_factory(currency_agent):
    """Function-scoped transaction factory."""
    return TransactionFactory(currency_agent=currency_agent)

@pytest.fixture(scope="session")
def critical_currency_pairs():
    """Critical currency pairs for P0 testing."""
    return CurrencyPairFactory.create_critical_pairs()

@pytest.fixture(scope="session")
def bug_revealing_amounts():
    """Amounts that reveal the rounding bug."""
    return [
        Decimal("49.99"),
        Decimal("99.99"),
        Decimal("149.99"),
        Decimal("10.01"),
        Decimal("0.99"),
    ]
```

---

## 6. Test Data Isolation Strategy

### 6.1 Parallel Test Execution

To enable parallel execution without data conflicts:

```python
class IsolatedTestData:
    """Provide isolated test data for parallel execution."""

    def __init__(self, worker_id: str):
        """
        Initialize with worker ID for parallel execution.

        Args:
            worker_id: Pytest-xdist worker ID (e.g., 'gw0', 'gw1')
        """
        self.worker_id = worker_id
        self.base_counter = self._get_worker_offset()

    def _get_worker_offset(self) -> int:
        """Calculate unique offset for this worker."""
        if self.worker_id == "master":
            return 0
        # Extract number from 'gw0', 'gw1', etc.
        worker_num = int(self.worker_id.replace("gw", ""))
        return worker_num * 10000  # Each worker gets 10k ID space

    def generate_merchant_id(self, test_name: str, counter: int) -> str:
        """Generate unique merchant ID for this worker."""
        return f"merchant_{self.worker_id}_{test_name}_{self.base_counter + counter}"

    def generate_customer_id(self, test_name: str, counter: int) -> str:
        """Generate unique customer ID for this worker."""
        return f"customer_{self.worker_id}_{test_name}_{self.base_counter + counter}"

    def generate_idempotency_key(self, test_name: str, counter: int) -> str:
        """Generate unique idempotency key for this worker."""
        return f"idempotency_{self.worker_id}_{test_name}_{self.base_counter + counter}"


# Usage in conftest.py
@pytest.fixture(scope="session")
def worker_id(request):
    """Get pytest-xdist worker ID."""
    if hasattr(request.config, 'workerinput'):
        return request.config.workerinput['workerid']
    return "master"

@pytest.fixture(scope="function")
def isolated_test_data(worker_id):
    """Provide isolated test data for this worker."""
    return IsolatedTestData(worker_id)
```

### 6.2 Test Database Strategy

For tests requiring database:

```python
# Database per worker strategy
def create_test_database(worker_id: str) -> str:
    """
    Create isolated test database for worker.

    Returns:
        Database connection string
    """
    db_name = f"test_currency_bug_{worker_id}"

    # Create database
    subprocess.run([
        "createdb", db_name
    ], check=True)

    # Run migrations
    subprocess.run([
        "psql", db_name, "-f", "migrations/001_initial_schema.sql"
    ], check=True)

    return f"postgresql://localhost/{db_name}"

@pytest.fixture(scope="session")
def test_database(worker_id):
    """Create and cleanup test database."""
    db_url = create_test_database(worker_id)
    yield db_url

    # Cleanup
    db_name = db_url.split("/")[-1]
    subprocess.run(["dropdb", db_name], check=False)
```

---

## 7. Test Data Coverage Metrics

### 7.1 Coverage Checklist

Track coverage across dimensions:

```python
class TestCoverageTracker:
    """Track test data coverage across dimensions."""

    def __init__(self):
        self.coverage = {
            "currency_pairs": set(),
            "amount_ranges": set(),
            "decimal_combinations": set(),
            "fx_rate_scenarios": set(),
        }

    def record_test(
        self,
        from_currency: CurrencyCode,
        to_currency: CurrencyCode,
        amount: Decimal,
        fx_rate: Decimal,
    ):
        """Record a test execution."""
        # Track currency pair
        self.coverage["currency_pairs"].add((from_currency, to_currency))

        # Track amount range
        if amount < Decimal("1"):
            self.coverage["amount_ranges"].add("sub_unit")
        elif amount < Decimal("100"):
            self.coverage["amount_ranges"].add("small")
        elif amount < Decimal("1000"):
            self.coverage["amount_ranges"].add("medium")
        else:
            self.coverage["amount_ranges"].add("large")

        # Track decimal combination
        from_decimals = get_currency(from_currency).decimal_places
        to_decimals = get_currency(to_currency).decimal_places
        self.coverage["decimal_combinations"].add((from_decimals, to_decimals))

        # Track FX rate scenario
        if fx_rate > Decimal("100"):
            self.coverage["fx_rate_scenarios"].add("high_rate")
        elif fx_rate < Decimal("0.01"):
            self.coverage["fx_rate_scenarios"].add("low_rate")
        else:
            self.coverage["fx_rate_scenarios"].add("normal_rate")

    def report(self) -> dict:
        """Generate coverage report."""
        return {
            "currency_pairs_covered": len(self.coverage["currency_pairs"]),
            "amount_ranges_covered": len(self.coverage["amount_ranges"]),
            "decimal_combinations_covered": len(self.coverage["decimal_combinations"]),
            "fx_rate_scenarios_covered": len(self.coverage["fx_rate_scenarios"]),
        }

    def get_missing_critical_pairs(self) -> List[Tuple[CurrencyCode, CurrencyCode]]:
        """Identify critical pairs not yet tested."""
        critical_pairs = CurrencyPairFactory.create_critical_pairs()
        tested_pairs = self.coverage["currency_pairs"]
        return [pair for pair in critical_pairs if pair not in tested_pairs]
```

### 7.2 Minimum Coverage Requirements

Before deployment, ensure:

- [ ] All 8 P0 critical pairs tested (EUR/USD/GBP → CLP/COP/JPY/KRW)
- [ ] All 9 decimal type combinations tested (0→0, 0→2, 0→3, 2→0, 2→2, 2→3, 3→0, 3→2, 3→3)
- [ ] Bug-revealing amounts tested for all P0 pairs (49.99, 99.99, etc.)
- [ ] High-precision FX rates tested (>4 decimals)
- [ ] Minimum and maximum amounts tested per currency
- [ ] Stale rate handling tested
- [ ] Missing rate error handling tested
- [ ] Same-currency passthrough tested

**Target**: 64+ unique test scenarios covering all combinations

---

## 8. Test Data Maintenance

### 8.1 Adding New Currencies

When adding a new currency to the system:

1. Add to `currency_configs` table (or `CURRENCY_CONFIGS` dict)
2. Add FX rates for new currency in `exchange_rates` table
3. Determine priority level (P0/P1/P2/P3) based on:
   - Transaction volume
   - Decimal places (0 or 3 = higher priority)
   - Regulatory requirements
4. Generate test scenarios using factories
5. Update coverage metrics

### 8.2 Updating FX Rates

Test data should use realistic rates but remain deterministic:

```python
def update_test_fx_rates(source: str = "ECB"):
    """
    Update test FX rates from live source while maintaining determinism.

    Args:
        source: Rate source ('ECB', 'OANDA', etc.)
    """
    # Fetch live rates
    live_rates = fetch_live_rates(source)

    # Round to 8 decimals for determinism
    test_rates = {
        pair: Decimal(str(rate)).quantize(Decimal("0.00000001"))
        for pair, rate in live_rates.items()
    }

    # Update test fixture file
    with open("tests/fixtures/fx_rates.json", "w") as f:
        json.dump({k: str(v) for k, v in test_rates.items()}, f, indent=2)

    print(f"Updated {len(test_rates)} test FX rates from {source}")
```

---

## 9. Test Data Anti-Patterns to Avoid

### 9.1 Common Mistakes

| Anti-Pattern | Why It's Bad | Solution |
|-------------|-------------|----------|
| Using `float` for amounts | Precision loss, non-deterministic | Always use `Decimal` |
| Hardcoding amounts in tests | Not reusable, miss edge cases | Use factories and fixtures |
| Random data without seeds | Non-reproducible failures | Always set `random.seed()` |
| Shared IDs across tests | Race conditions, flaky tests | Use isolated data per test |
| Testing only happy path | Miss bugs like the €2.3M incident | Prioritize edge cases |
| Skipping zero-decimal currencies | Miss the critical bug category | Always test CLP, COP, JPY, KRW |
| Using stale FX rates | Unrealistic scenarios | Update rates quarterly |
| Ignoring three-decimal currencies | Incomplete coverage | Test KWD, BHD, OMR |

---

## 10. Summary: Test Data Pyramid

```
                    /\
                   /  \
                  /    \
                 /Random\        20 tests
                / Chaos  \       (seed-based)
               /  Testing \
              /____________\
             /              \
            /   Edge Cases   \   50 tests
           /  (Bug-Revealing) \  (critical scenarios)
          /____________________\
         /                      \
        /    Boundary Values     \   30 tests
       /     (Min/Max Amounts)    \  (limits testing)
      /__________________________\
     /                            \
    /     Standard Scenarios       \  20 tests
   /    (Happy Path Conversions)    \ (smoke tests)
  /________________________________\

Total: ~120 core test scenarios
```

**Allocation**:
- **Standard scenarios** (20): Common pairs, normal amounts, happy path
- **Boundary values** (30): Min/max amounts, currency limits
- **Edge cases** (50): Bug-revealing amounts, zero-decimal, three-decimal
- **Chaos testing** (20): Random but deterministic amounts

---

## Appendix: Quick Start Guide

### Generate Test Data for a New Test

```python
# 1. Import factories
from framework.test_factories import CurrencyPairFactory, TransactionFactory

# 2. Create factory instances
transaction_factory = TransactionFactory(currency_agent)

# 3. Generate critical test case
bug_test = transaction_factory.create_bug_revealing_transaction(
    from_currency=CurrencyCode.EUR,
    to_currency=CurrencyCode.CLP
)

# 4. Generate batch of tests
critical_pairs = CurrencyPairFactory.create_critical_pairs()
bug_amounts = generate_bug_revealing_amounts(CurrencyCode.EUR)
all_tests = transaction_factory.create_batch(critical_pairs, bug_amounts)

# 5. Execute tests
for test_request in all_tests:
    response = payment_agent.authorize_payment(test_request)
    assert_correct_conversion(test_request, response)
```

---

**Document Version**: 1.0
**Last Updated**: 2026-02-25
**Owner**: Data Architect (Principal)
**Review Cycle**: Quarterly or when new currencies added
