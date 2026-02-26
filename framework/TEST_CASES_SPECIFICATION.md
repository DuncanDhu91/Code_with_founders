# Test Case Specification - Silent Currency Bug Prevention
## Google Testing Standards Compliance (AAA Pattern)

**Challenge**: Currency conversion bug prevention
**Test Framework**: pytest
**Pattern**: AAA (Arrange-Act-Assert)
**Priority System**: P0 (Critical) → P4 (Low)

---

## Table of Contents

1. [Core Requirement 1: Multi-Currency Authorization Tests](#core-requirement-1)
2. [Core Requirement 2: Currency Edge Case Tests](#core-requirement-2)
3. [Unit Test Suite](#unit-test-suite)
4. [Integration Test Suite](#integration-test-suite)
5. [E2E Test Suite](#e2e-test-suite)

---

## Core Requirement 1: Multi-Currency Authorization Tests

**Requirement**: Verify authorization amount correctness across 5+ currency pairs

### TC-AUTH-001: EUR to CLP Authorization (The €2.3M Bug Case)

**Priority**: P0 (CRITICAL - This was the actual bug)

**Category**: E2E

**Objective**: Verify that EUR to CLP conversion rounds AFTER conversion, not before

**Prerequisites**:
- Payment agent configured with correct rounding logic
- FX rate: EUR/CLP = 1052.00
- Test merchant account: merchant_test_001

**Test Steps (ARRANGE)**:
```python
# ARRANGE
currency_agent = CurrencyAgent(fx_rates={"EUR_CLP": Decimal("1052.00")})
payment_agent = PaymentAgent(currency_agent=currency_agent, simulate_bug=False)

auth_request = AuthorizationRequest(
    merchant_id="merchant_test_001",
    customer_id="customer_chile_001",
    amount=Decimal("49.99"),  # €49.99 EUR
    currency=CurrencyCode.EUR,
    settlement_currency=CurrencyCode.CLP,
    payment_method=PaymentMethod.CARD,
    idempotency_key="test_eur_clp_001"
)
```

**Test Steps (ACT)**:
```python
# ACT
response = payment_agent.authorize_payment(auth_request)
```

**Expected Results (ASSERT)**:
```python
# ASSERT
assert response.status == TransactionStatus.AUTHORIZED
assert response.authorized_amount == Decimal("52595")  # NOT 52,600
assert response.authorized_currency == CurrencyCode.CLP
assert response.settlement_amount == Decimal("52595")
assert response.fx_rate == Decimal("1052.00")

# Verify calculation:
# CORRECT: 49.99 * 1052 = 52,594.48 → rounds to 52,595 CLP
# BUG: 50.00 * 1052 = 52,600 CLP (5 CLP loss per transaction)
```

**Bug Scenario Verification**:
```python
# Verify the bug is actually caught
payment_agent_with_bug = PaymentAgent(currency_agent, simulate_bug=True)
bug_response = payment_agent_with_bug.authorize_payment(auth_request)

assert bug_response.authorized_amount == Decimal("52600")  # Incorrect
assert bug_response.authorized_amount > response.authorized_amount  # Customer overcharged
```

**Pass Criteria**:
- ✅ Authorization succeeds
- ✅ Amount is 52,595 CLP (not 52,600)
- ✅ Bug simulation produces 52,600 CLP (confirms test catches the bug)
- ✅ Webhook emitted with correct amount

---

### TC-AUTH-002: EUR to JPY Authorization

**Priority**: P0 (CRITICAL - Zero-decimal currency)

**Category**: E2E

**Objective**: Verify EUR to JPY conversion for zero-decimal currency

**Prerequisites**:
- FX rate: EUR/JPY = 161.25
- Test merchant settles in JPY

**Test Steps**:

**ARRANGE**:
```python
currency_agent = CurrencyAgent(fx_rates={"EUR_JPY": Decimal("161.25")})
payment_agent = PaymentAgent(currency_agent=currency_agent, simulate_bug=False)

auth_request = AuthorizationRequest(
    merchant_id="merchant_japan_001",
    customer_id="customer_eu_001",
    amount=Decimal("100.00"),  # €100.00 EUR
    currency=CurrencyCode.EUR,
    settlement_currency=CurrencyCode.JPY,
    payment_method=PaymentMethod.CARD,
    idempotency_key="test_eur_jpy_001"
)
```

**ACT**:
```python
response = payment_agent.authorize_payment(auth_request)
```

**ASSERT**:
```python
assert response.status == TransactionStatus.AUTHORIZED
assert response.authorized_amount == Decimal("16125")  # ¥16,125
assert response.authorized_currency == CurrencyCode.JPY
assert response.fx_rate == Decimal("161.25")

# Verify calculation:
# 100.00 EUR * 161.25 = 16,125.00 JPY (exact, no rounding needed)

# Verify no decimal places in JPY amount
assert response.authorized_amount % 1 == 0  # Must be whole number
```

**Pass Criteria**:
- ✅ Amount is ¥16,125 (whole number)
- ✅ No decimal places in result
- ✅ FX rate stored in transaction record

---

### TC-AUTH-003: USD to KRW Authorization

**Priority**: P0 (CRITICAL - Zero-decimal currency)

**Category**: E2E

**Objective**: Verify USD to KRW conversion with rounding

**Prerequisites**:
- FX rate: USD/KRW = 1332.15
- Amount requires rounding

**Test Steps**:

**ARRANGE**:
```python
currency_agent = CurrencyAgent(fx_rates={"USD_KRW": Decimal("1332.15")})
payment_agent = PaymentAgent(currency_agent=currency_agent, simulate_bug=False)

auth_request = AuthorizationRequest(
    merchant_id="merchant_korea_001",
    customer_id="customer_us_001",
    amount=Decimal("50.00"),  # $50.00 USD
    currency=CurrencyCode.USD,
    settlement_currency=CurrencyCode.KRW,
    payment_method=PaymentMethod.CARD,
    idempotency_key="test_usd_krw_001"
)
```

**ACT**:
```python
response = payment_agent.authorize_payment(auth_request)
```

**ASSERT**:
```python
assert response.status == TransactionStatus.AUTHORIZED
assert response.authorized_amount == Decimal("66608")  # ₩66,608
assert response.authorized_currency == CurrencyCode.KRW

# Verify calculation:
# CORRECT: 50.00 * 1332.15 = 66,607.50 → rounds to 66,608 KRW (ROUND_HALF_UP)
# BUG: 50.00 * 1332.15 = 66,608 (happens to match in this case)

# Test with amount that exposes rounding difference
request_2 = auth_request.copy(update={"amount": Decimal("50.01")})
response_2 = payment_agent.authorize_payment(request_2)
# 50.01 * 1332.15 = 66,620.82 → 66,621 KRW
assert response_2.authorized_amount == Decimal("66621")
```

**Pass Criteria**:
- ✅ Rounding is HALF_UP (0.5 rounds up)
- ✅ No decimal places in KRW
- ✅ Multiple test amounts verify consistency

---

### TC-AUTH-004: GBP to CLP Authorization

**Priority**: P0 (HIGH - Cross-border common pair)

**Category**: E2E

**Objective**: Verify GBP to CLP conversion

**Prerequisites**:
- FX rate: GBP/CLP = 1216.50
- UK merchant, Chilean customer

**Test Steps**:

**ARRANGE**:
```python
currency_agent = CurrencyAgent(fx_rates={"GBP_CLP": Decimal("1216.50")})
payment_agent = PaymentAgent(currency_agent=currency_agent, simulate_bug=False)

auth_request = AuthorizationRequest(
    merchant_id="merchant_uk_001",
    customer_id="customer_chile_001",
    amount=Decimal("75.50"),  # £75.50 GBP
    currency=CurrencyCode.GBP,
    settlement_currency=CurrencyCode.CLP,
    payment_method=PaymentMethod.CARD,
    idempotency_key="test_gbp_clp_001"
)
```

**ACT**:
```python
response = payment_agent.authorize_payment(auth_request)
```

**ASSERT**:
```python
assert response.status == TransactionStatus.AUTHORIZED
assert response.authorized_amount == Decimal("91846")  # CLP 91,846
assert response.authorized_currency == CurrencyCode.CLP

# Verify calculation:
# 75.50 * 1216.50 = 91,845.75 → rounds to 91,846 CLP
```

**Pass Criteria**:
- ✅ Correct rounding to nearest CLP
- ✅ Amount is whole number (0 decimals)

---

### TC-AUTH-005: EUR to USD Authorization

**Priority**: P1 (Same decimal places, but common pair)

**Category**: E2E

**Objective**: Verify same-decimal-place conversion

**Prerequisites**:
- FX rate: EUR/USD = 1.0850
- Both currencies have 2 decimal places

**Test Steps**:

**ARRANGE**:
```python
currency_agent = CurrencyAgent(fx_rates={"EUR_USD": Decimal("1.0850")})
payment_agent = PaymentAgent(currency_agent=currency_agent, simulate_bug=False)

auth_request = AuthorizationRequest(
    merchant_id="merchant_us_001",
    customer_id="customer_eu_001",
    amount=Decimal("100.00"),  # €100.00 EUR
    currency=CurrencyCode.EUR,
    settlement_currency=CurrencyCode.USD,
    payment_method=PaymentMethod.CARD,
    idempotency_key="test_eur_usd_001"
)
```

**ACT**:
```python
response = payment_agent.authorize_payment(auth_request)
```

**ASSERT**:
```python
assert response.status == TransactionStatus.AUTHORIZED
assert response.authorized_amount == Decimal("108.50")  # $108.50 USD
assert response.authorized_currency == CurrencyCode.USD

# Verify calculation:
# 100.00 * 1.0850 = 108.50 USD (exact, no rounding needed)

# Test with amount requiring rounding
request_2 = auth_request.copy(update={"amount": Decimal("99.99")})
response_2 = payment_agent.authorize_payment(request_2)
# 99.99 * 1.0850 = 108.48915 → rounds to $108.49 USD
assert response_2.authorized_amount == Decimal("108.49")
```

**Pass Criteria**:
- ✅ 2 decimal places preserved
- ✅ Rounding to cents works correctly

---

### TC-AUTH-006: EUR to KWD Authorization (Three-Decimal Currency)

**Priority**: P1 (Three-decimal currency testing)

**Category**: E2E

**Objective**: Verify conversion to three-decimal currency

**Prerequisites**:
- FX rate: EUR/KWD = 0.3345
- KWD has 3 decimal places (fils)

**Test Steps**:

**ARRANGE**:
```python
currency_agent = CurrencyAgent(fx_rates={"EUR_KWD": Decimal("0.3345")})
payment_agent = PaymentAgent(currency_agent=currency_agent, simulate_bug=False)

auth_request = AuthorizationRequest(
    merchant_id="merchant_kuwait_001",
    customer_id="customer_eu_001",
    amount=Decimal("100.00"),  # €100.00 EUR
    currency=CurrencyCode.EUR,
    settlement_currency=CurrencyCode.KWD,
    payment_method=PaymentMethod.CARD,
    idempotency_key="test_eur_kwd_001"
)
```

**ACT**:
```python
response = payment_agent.authorize_payment(auth_request)
```

**ASSERT**:
```python
assert response.status == TransactionStatus.AUTHORIZED
assert response.authorized_amount == Decimal("33.450")  # KD 33.450
assert response.authorized_currency == CurrencyCode.KWD

# Verify 3 decimal places
amount_str = str(response.authorized_amount)
if '.' in amount_str:
    decimal_places = len(amount_str.split('.')[1])
    assert decimal_places <= 3, "KWD should have max 3 decimal places"
```

**Pass Criteria**:
- ✅ 3 decimal places preserved
- ✅ Rounding to fils (0.001 KWD) works correctly

---

## Core Requirement 2: Currency Edge Case Tests

**Requirement**: Handle 3+ currency edge cases correctly

### TC-EDGE-001: Minimum Amount Conversion

**Priority**: P0 (CRITICAL - Boundary value)

**Category**: Unit

**Objective**: Verify minimum amount handling in conversions

**Test Steps**:

**ARRANGE**:
```python
currency_agent = CurrencyAgent(fx_rates={"EUR_JPY": Decimal("161.25")})
min_eur = get_currency(CurrencyCode.EUR).min_amount  # €0.01
```

**ACT**:
```python
result, fx_rate = currency_agent.convert_amount(
    amount=min_eur,
    from_currency=CurrencyCode.EUR,
    to_currency=CurrencyCode.JPY,
    round_before_conversion=False
)
```

**ASSERT**:
```python
# 0.01 EUR * 161.25 = 1.6125 JPY → rounds to ¥2
assert result == Decimal("2")

# Verify this meets JPY minimum
min_jpy = get_currency(CurrencyCode.JPY).min_amount
assert result >= min_jpy
```

**Pass Criteria**:
- ✅ Minimum EUR amount converts to valid JPY amount
- ✅ Result meets target currency minimum

---

### TC-EDGE-002: Maximum Amount Conversion

**Priority**: P0 (CRITICAL - Boundary value)

**Category**: Unit

**Objective**: Verify maximum amount doesn't overflow

**Test Steps**:

**ARRANGE**:
```python
currency_agent = CurrencyAgent(fx_rates={"EUR_CLP": Decimal("1052.00")})
max_eur = get_currency(CurrencyCode.EUR).max_amount  # €999,999.99
```

**ACT**:
```python
result, fx_rate = currency_agent.convert_amount(
    amount=max_eur,
    from_currency=CurrencyCode.EUR,
    to_currency=CurrencyCode.CLP,
    round_before_conversion=False
)
```

**ASSERT**:
```python
# 999,999.99 * 1052 = 1,051,999,894.48 → 1,051,999,894 CLP
expected = Decimal("1051999894")
assert result == expected

# Verify this doesn't exceed CLP maximum
max_clp = get_currency(CurrencyCode.CLP).max_amount
assert result <= max_clp
```

**Pass Criteria**:
- ✅ Large conversions complete without overflow
- ✅ Result within target currency limits

---

### TC-EDGE-003: Sub-Minimum Amount After Conversion

**Priority**: P0 (CRITICAL - Can create zero-value transactions)

**Category**: Unit

**Objective**: Detect when converted amount falls below minimum

**Test Steps**:

**ARRANGE**:
```python
currency_agent = CurrencyAgent(fx_rates={"JPY_EUR": Decimal("0.0062034")})
small_jpy = Decimal("1")  # ¥1 JPY
```

**ACT**:
```python
result, fx_rate = currency_agent.convert_amount(
    amount=small_jpy,
    from_currency=CurrencyCode.JPY,
    to_currency=CurrencyCode.EUR,
    round_before_conversion=False
)

# Validate result
is_valid, error_msg = currency_agent.validate_amount_for_currency(
    amount=result,
    currency=CurrencyCode.EUR
)
```

**ASSERT**:
```python
# 1 JPY * 0.0062034 = 0.0062034 EUR → rounds to €0.01 EUR
assert result == Decimal("0.01")
assert is_valid  # Should be valid (meets minimum)

# Test with even smaller JPY amount (if allowed)
# If JPY allows 0.01 (unlikely for zero-decimal), test that scenario
```

**Pass Criteria**:
- ✅ Small amounts don't become zero
- ✅ Result meets target currency minimum
- ✅ Validation catches amounts below minimum

---

### TC-EDGE-004: Repeating Decimal Conversion

**Priority**: P1 (Precision edge case)

**Category**: Unit

**Objective**: Verify repeating decimals are handled correctly

**Test Steps**:

**ARRANGE**:
```python
currency_agent = CurrencyAgent(fx_rates={"EUR_CLP": Decimal("1052.00")})
# Amount that creates repeating decimal: €33.33 (1/3 of €100)
amount = Decimal("33.33")
```

**ACT**:
```python
result, fx_rate = currency_agent.convert_amount(
    amount=amount,
    from_currency=CurrencyCode.EUR,
    to_currency=CurrencyCode.CLP,
    round_before_conversion=False
)
```

**ASSERT**:
```python
# 33.33 * 1052 = 35,063.16 → 35,063 CLP
assert result == Decimal("35063")

# Verify precision: difference should be minimal
raw_conversion = amount * fx_rate
difference = abs(result - raw_conversion)
assert difference < Decimal("1.0")  # Less than 1 CLP difference
```

**Pass Criteria**:
- ✅ Repeating decimals round correctly
- ✅ Precision loss is minimal and documented

---

### TC-EDGE-005: Fractional Cents Validation

**Priority**: P0 (CRITICAL - Data integrity)

**Category**: Unit

**Objective**: Reject amounts with excessive decimal places

**Test Steps**:

**ARRANGE**:
```python
currency_agent = CurrencyAgent()
invalid_eur_amount = Decimal("100.999")  # 3 decimals, EUR supports 2
```

**ACT**:
```python
is_valid, error_msg = currency_agent.validate_amount_for_currency(
    amount=invalid_eur_amount,
    currency=CurrencyCode.EUR
)
```

**ASSERT**:
```python
assert not is_valid
assert "3 decimal places" in error_msg
assert "EUR" in error_msg
assert "2" in error_msg  # EUR supports 2 decimal places

# Verify valid amount passes
valid_amount = Decimal("100.99")
is_valid_2, _ = currency_agent.validate_amount_for_currency(
    amount=valid_amount,
    currency=CurrencyCode.EUR
)
assert is_valid_2
```

**Pass Criteria**:
- ✅ Invalid decimal places rejected
- ✅ Error message is clear and actionable
- ✅ Valid amounts pass validation

---

### TC-EDGE-006: Zero Amount Handling

**Priority**: P1 (Edge case - card verification scenario)

**Category**: Integration

**Objective**: Handle zero-amount authorizations (card verification)

**Test Steps**:

**ARRANGE**:
```python
currency_agent = CurrencyAgent()
payment_agent = PaymentAgent(currency_agent=currency_agent)

auth_request = AuthorizationRequest(
    merchant_id="merchant_001",
    customer_id="customer_001",
    amount=Decimal("0.00"),
    currency=CurrencyCode.EUR,
    settlement_currency=CurrencyCode.USD,
    payment_method=PaymentMethod.CARD,
    idempotency_key="test_zero_amount"
)
```

**ACT**:
```python
response = payment_agent.authorize_payment(auth_request)
```

**ASSERT**:
```python
# Zero-amount should either succeed (card verification) or fail gracefully
if response.status == TransactionStatus.AUTHORIZED:
    assert response.authorized_amount == Decimal("0.00")
    assert response.settlement_amount == Decimal("0.00")
elif response.status == TransactionStatus.FAILED:
    assert response.error_code == "INVALID_AMOUNT"
    assert "zero" in response.message.lower() or "0.00" in response.message
```

**Pass Criteria**:
- ✅ Zero amount handled explicitly (not silently)
- ✅ Clear error message if rejected
- ✅ If allowed, authorization succeeds with zero amount

---

### TC-EDGE-007: Stale FX Rate Warning

**Priority**: P2 (Observability)

**Category**: Integration

**Objective**: Log warning when FX rate is stale

**Test Steps**:

**ARRANGE**:
```python
import logging
from datetime import datetime, timedelta

# Capture logs
logger = logging.getLogger("framework.agents.currency_agent")
with capture_logs(logger) as log_capture:
    currency_agent = CurrencyAgent()

    # Request rate with stale timestamp (10 minutes ago)
    stale_timestamp = datetime.utcnow() - timedelta(minutes=10)
```

**ACT**:
```python
    fx_rate = currency_agent.get_fx_rate(
        from_currency=CurrencyCode.EUR,
        to_currency=CurrencyCode.CLP,
        timestamp=stale_timestamp
    )
```

**ASSERT**:
```python
    # Verify rate returned (fail gracefully)
    assert fx_rate == Decimal("1052.00")

    # Verify warning logged
    assert any("stale" in log.lower() for log in log_capture.logs)
    assert any("10 minutes" in log or "600" in log for log in log_capture.logs)
```

**Pass Criteria**:
- ✅ Warning logged for stale rates
- ✅ Conversion proceeds (doesn't block)
- ✅ Rate age included in warning

---

### TC-EDGE-008: Missing FX Rate Error

**Priority**: P1 (Error handling)

**Category**: Integration

**Objective**: Handle missing FX rate gracefully

**Test Steps**:

**ARRANGE**:
```python
currency_agent = CurrencyAgent()  # Default rates don't include THB
payment_agent = PaymentAgent(currency_agent=currency_agent)

auth_request = AuthorizationRequest(
    merchant_id="merchant_001",
    customer_id="customer_001",
    amount=Decimal("100.00"),
    currency=CurrencyCode.EUR,
    settlement_currency="THB",  # Rate not in system
    payment_method=PaymentMethod.CARD,
    idempotency_key="test_missing_rate"
)
```

**ACT**:
```python
response = payment_agent.authorize_payment(auth_request)
```

**ASSERT**:
```python
assert response.status == TransactionStatus.FAILED
assert response.error_code == "FX_RATE_UNAVAILABLE"
assert "EUR" in response.message
assert "THB" in response.message
assert response.authorized_amount == Decimal("0")
```

**Pass Criteria**:
- ✅ Error response returned (not exception)
- ✅ Error code is specific
- ✅ Error message includes currency pair
- ✅ Transaction not created

---

## Unit Test Suite

### TC-UNIT-001: Round After Conversion (Correct Logic)

**Priority**: P0 (CRITICAL - Core bug prevention)

**Category**: Unit

**Objective**: Verify rounding happens AFTER conversion

**Test Steps**:

**ARRANGE**:
```python
currency_agent = CurrencyAgent(fx_rates={"EUR_CLP": Decimal("1052.00")})
amount = Decimal("49.99")  # The bug detector amount
```

**ACT**:
```python
result, fx_rate = currency_agent.convert_amount(
    amount=amount,
    from_currency=CurrencyCode.EUR,
    to_currency=CurrencyCode.CLP,
    round_before_conversion=False  # CORRECT
)
```

**ASSERT**:
```python
# CORRECT: 49.99 * 1052 = 52,594.48 → 52,595 CLP
assert result == Decimal("52595")

# Verify intermediate calculation
raw_result = amount * fx_rate
assert raw_result == Decimal("52594.48")

# Verify rounding direction (ROUND_HALF_UP)
clp_config = get_currency(CurrencyCode.CLP)
rounded_result = clp_config.round_amount(raw_result)
assert rounded_result == result
```

**Pass Criteria**:
- ✅ Result is 52,595 CLP (not 52,600)
- ✅ Rounding applied after multiplication

---

### TC-UNIT-002: Round Before Conversion (Bug Simulation)

**Priority**: P0 (CRITICAL - Bug detection validation)

**Category**: Unit

**Objective**: Verify test can detect the bug

**Test Steps**:

**ARRANGE**:
```python
currency_agent = CurrencyAgent(fx_rates={"EUR_CLP": Decimal("1052.00")})
amount = Decimal("49.99")
```

**ACT**:
```python
bug_result, fx_rate = currency_agent.convert_amount(
    amount=amount,
    from_currency=CurrencyCode.EUR,
    to_currency=CurrencyCode.CLP,
    round_before_conversion=True  # BUG
)
```

**ASSERT**:
```python
# BUG: 50.00 * 1052 = 52,600 CLP (WRONG)
assert bug_result == Decimal("52600")

# Verify bug causes financial loss
correct_result = Decimal("52595")
loss_per_transaction = bug_result - correct_result
assert loss_per_transaction == Decimal("5")  # 5 CLP overcharge

# Verify log message indicates bug mode
# (Requires log capture in actual test)
```

**Pass Criteria**:
- ✅ Bug produces 52,600 CLP (incorrect)
- ✅ Test detects 5 CLP difference
- ✅ Bug mode logged

---

### TC-UNIT-003: Zero-Decimal Currency Rounding

**Priority**: P0 (CRITICAL)

**Category**: Unit

**Objective**: Verify zero-decimal currencies round to integers

**Test Steps**:

**ARRANGE**:
```python
zero_decimal_currencies = [
    CurrencyCode.JPY,
    CurrencyCode.CLP,
    CurrencyCode.KRW,
    CurrencyCode.COP
]
```

**ACT & ASSERT**:
```python
for currency in zero_decimal_currencies:
    config = get_currency(currency)

    # Test various amounts
    test_amounts = [
        (Decimal("100.0"), Decimal("100")),   # Exact
        (Decimal("100.4"), Decimal("100")),   # Round down
        (Decimal("100.5"), Decimal("101")),   # Round up (HALF_UP)
        (Decimal("100.9"), Decimal("101")),   # Round up
    ]

    for input_amount, expected in test_amounts:
        result = config.round_amount(input_amount)
        assert result == expected, (
            f"{currency} failed for {input_amount}: "
            f"expected {expected}, got {result}"
        )

        # Verify no decimal places
        assert result % 1 == 0, f"{currency} result {result} has decimal places"
```

**Pass Criteria**:
- ✅ All zero-decimal currencies round to integers
- ✅ ROUND_HALF_UP behavior (0.5 rounds up)
- ✅ No decimal places in results

---

### TC-UNIT-004: Three-Decimal Currency Rounding

**Priority**: P1

**Category**: Unit

**Objective**: Verify three-decimal currencies round to fils

**Test Steps**:

**ARRANGE**:
```python
three_decimal_currencies = [
    CurrencyCode.KWD,
    CurrencyCode.BHD,
    CurrencyCode.OMR
]
```

**ACT & ASSERT**:
```python
for currency in three_decimal_currencies:
    config = get_currency(currency)

    test_amounts = [
        (Decimal("10.0000"), Decimal("10.000")),     # Exact
        (Decimal("10.1234"), Decimal("10.123")),     # Round down
        (Decimal("10.1235"), Decimal("10.124")),     # Round up (HALF_UP)
        (Decimal("10.9999"), Decimal("11.000")),     # Round up
    ]

    for input_amount, expected in test_amounts:
        result = config.round_amount(input_amount)
        assert result == expected, (
            f"{currency} failed for {input_amount}: "
            f"expected {expected}, got {result}"
        )

        # Verify exactly 3 decimal places
        amount_str = str(result)
        if '.' in amount_str:
            decimal_places = len(amount_str.split('.')[1].rstrip('0'))
            assert decimal_places <= 3
```

**Pass Criteria**:
- ✅ All three-decimal currencies round to 3 decimal places
- ✅ ROUND_HALF_UP behavior correct

---

### TC-UNIT-005: Currency Validation - Amount Range

**Priority**: P0 (CRITICAL - Data integrity)

**Category**: Unit

**Objective**: Validate amount min/max for each currency

**Test Steps**:

**ARRANGE**:
```python
currency_agent = CurrencyAgent()
```

**ACT & ASSERT**:
```python
test_cases = [
    # (currency, amount, should_be_valid, reason)
    (CurrencyCode.EUR, Decimal("0.01"), True, "Minimum EUR"),
    (CurrencyCode.EUR, Decimal("0.00"), False, "Below minimum EUR"),
    (CurrencyCode.EUR, Decimal("999999.99"), True, "Maximum EUR"),
    (CurrencyCode.EUR, Decimal("1000000.00"), False, "Above maximum EUR"),

    (CurrencyCode.JPY, Decimal("1"), True, "Minimum JPY"),
    (CurrencyCode.JPY, Decimal("0"), False, "Below minimum JPY"),
    (CurrencyCode.JPY, Decimal("9999999"), True, "Maximum JPY"),
    (CurrencyCode.JPY, Decimal("10000000"), False, "Above maximum JPY"),

    (CurrencyCode.KWD, Decimal("0.001"), True, "Minimum KWD"),
    (CurrencyCode.KWD, Decimal("0.0001"), False, "Below minimum KWD"),
]

for currency, amount, should_be_valid, reason in test_cases:
    is_valid, error_msg = currency_agent.validate_amount_for_currency(
        amount=amount,
        currency=currency
    )

    assert is_valid == should_be_valid, (
        f"Validation failed for {reason}: {amount} {currency}\n"
        f"Expected valid={should_be_valid}, got {is_valid}\n"
        f"Error: {error_msg}"
    )

    if not is_valid:
        assert error_msg is not None
        assert str(currency.value) in error_msg
```

**Pass Criteria**:
- ✅ All min/max validations pass
- ✅ Error messages are descriptive
- ✅ All currencies tested

---

## Integration Test Suite

### TC-INT-001: Agent Collaboration - Currency + Payment

**Priority**: P0 (CRITICAL)

**Category**: Integration

**Objective**: Verify CurrencyAgent and PaymentAgent work together correctly

**Test Steps**:

**ARRANGE**:
```python
currency_agent = CurrencyAgent(fx_rates={"EUR_CLP": Decimal("1052.00")})
payment_agent = PaymentAgent(currency_agent=currency_agent, simulate_bug=False)

auth_request = AuthorizationRequest(
    merchant_id="merchant_001",
    customer_id="customer_001",
    amount=Decimal("49.99"),
    currency=CurrencyCode.EUR,
    settlement_currency=CurrencyCode.CLP,
    payment_method=PaymentMethod.CARD,
    idempotency_key="test_integration_001"
)
```

**ACT**:
```python
response = payment_agent.authorize_payment(auth_request)
transaction = payment_agent.get_transaction(response.transaction_id)
webhooks = payment_agent.get_webhooks_for_merchant("merchant_001")
```

**ASSERT**:
```python
# Verify response
assert response.status == TransactionStatus.AUTHORIZED
assert response.authorized_amount == Decimal("52595")

# Verify transaction record
assert transaction.original_amount == Decimal("49.99")
assert transaction.original_currency == CurrencyCode.EUR
assert transaction.settlement_amount == Decimal("52595")
assert transaction.settlement_currency == CurrencyCode.CLP
assert transaction.fx_rate == Decimal("1052.00")
assert transaction.fx_rate_timestamp is not None

# Verify webhook
assert len(webhooks) == 1
webhook = webhooks[0]
assert webhook.transaction_id == response.transaction_id
assert webhook.amount == Decimal("52595")
assert webhook.currency == CurrencyCode.CLP
```

**Pass Criteria**:
- ✅ Agents collaborate correctly
- ✅ Transaction record complete
- ✅ Webhook emitted with correct data

---

### TC-INT-002: Multi-Currency Transaction Flow

**Priority**: P1

**Category**: Integration

**Objective**: Test multiple currency conversions in sequence

**Test Steps**:

**ARRANGE**:
```python
currency_agent = CurrencyAgent(fx_rates={
    "EUR_USD": Decimal("1.0850"),
    "USD_JPY": Decimal("148.65"),
    "EUR_JPY": Decimal("161.25")
})
payment_agent = PaymentAgent(currency_agent=currency_agent)

# Process 3 transactions with different currency pairs
requests = [
    ("EUR", "USD", Decimal("100.00")),
    ("USD", "JPY", Decimal("100.00")),
    ("EUR", "JPY", Decimal("100.00")),
]
```

**ACT**:
```python
responses = []
for from_curr, to_curr, amount in requests:
    request = AuthorizationRequest(
        merchant_id="merchant_001",
        customer_id="customer_001",
        amount=amount,
        currency=CurrencyCode[from_curr],
        settlement_currency=CurrencyCode[to_curr],
        payment_method=PaymentMethod.CARD,
        idempotency_key=f"test_{from_curr}_{to_curr}"
    )
    responses.append(payment_agent.authorize_payment(request))
```

**ASSERT**:
```python
# Verify all succeeded
assert all(r.status == TransactionStatus.AUTHORIZED for r in responses)

# Verify expected amounts
assert responses[0].authorized_amount == Decimal("108.50")  # EUR->USD
assert responses[1].authorized_amount == Decimal("14865")   # USD->JPY
assert responses[2].authorized_amount == Decimal("16125")   # EUR->JPY

# Verify no cross-contamination (each transaction independent)
transactions = [payment_agent.get_transaction(r.transaction_id) for r in responses]
assert len(set(t.transaction_id for t in transactions)) == 3  # All unique
```

**Pass Criteria**:
- ✅ Multiple conversions work independently
- ✅ No state contamination between transactions
- ✅ All FX rates stored correctly

---

## E2E Test Suite

### TC-E2E-001: Complete Checkout Flow with Currency Conversion

**Priority**: P0 (CRITICAL - End-to-end validation)

**Category**: E2E

**Objective**: Test full payment flow from request to webhook

**Test Steps**:

**ARRANGE**:
```python
# Set up complete payment system
currency_agent = CurrencyAgent(fx_rates={"EUR_CLP": Decimal("1052.00")})
payment_agent = PaymentAgent(currency_agent=currency_agent, simulate_bug=False)

# Customer sees price in EUR, merchant settles in CLP
customer_facing_amount = Decimal("49.99")  # €49.99 EUR
customer_currency = CurrencyCode.EUR
merchant_settlement_currency = CurrencyCode.CLP

auth_request = AuthorizationRequest(
    merchant_id="merchant_chile_001",
    customer_id="customer_eu_001",
    amount=customer_facing_amount,
    currency=customer_currency,
    settlement_currency=merchant_settlement_currency,
    payment_method=PaymentMethod.CARD,
    idempotency_key="e2e_checkout_001",
    metadata={
        "order_id": "ORDER-12345",
        "customer_ip": "203.0.113.1",
        "user_agent": "Mozilla/5.0..."
    }
)
```

**ACT**:
```python
# Step 1: Authorize payment
auth_response = payment_agent.authorize_payment(auth_request)

# Step 2: Retrieve transaction details
transaction = payment_agent.get_transaction(auth_response.transaction_id)

# Step 3: Check webhook delivery
webhooks = payment_agent.get_webhooks_for_merchant("merchant_chile_001")
```

**ASSERT**:
```python
# Step 1 Assertions: Authorization response
assert auth_response.status == TransactionStatus.AUTHORIZED
assert auth_response.transaction_id is not None
assert auth_response.authorized_amount == Decimal("52595")  # CLP amount
assert auth_response.authorized_currency == CurrencyCode.CLP
assert auth_response.settlement_amount == Decimal("52595")
assert auth_response.settlement_currency == CurrencyCode.CLP
assert auth_response.fx_rate == Decimal("1052.00")
assert auth_response.message == "Authorization successful"
assert auth_response.error_code is None

# Step 2 Assertions: Transaction record
assert transaction.transaction_id == auth_response.transaction_id
assert transaction.merchant_id == "merchant_chile_001"
assert transaction.customer_id == "customer_eu_001"
assert transaction.original_amount == Decimal("49.99")
assert transaction.original_currency == CurrencyCode.EUR
assert transaction.settlement_amount == Decimal("52595")
assert transaction.settlement_currency == CurrencyCode.CLP
assert transaction.authorized_amount == Decimal("52595")
assert transaction.fx_rate == Decimal("1052.00")
assert transaction.fx_rate_timestamp is not None
assert transaction.status == TransactionStatus.AUTHORIZED
assert transaction.payment_method == PaymentMethod.CARD
assert transaction.metadata["order_id"] == "ORDER-12345"

# Step 3 Assertions: Webhook
assert len(webhooks) == 1
webhook = webhooks[0]
assert webhook.event_type == "payment.authorized"
assert webhook.transaction_id == auth_response.transaction_id
assert webhook.status == TransactionStatus.AUTHORIZED
assert webhook.amount == Decimal("52595")
assert webhook.currency == CurrencyCode.CLP
assert webhook.settlement_amount == Decimal("52595")
assert webhook.settlement_currency == CurrencyCode.CLP
assert webhook.metadata["merchant_id"] == "merchant_chile_001"
assert webhook.metadata["fx_rate"] == "1052.00"

# Financial Verification: Bug detection
# If bug were present, authorized amount would be 52,600 CLP (5 CLP loss)
assert auth_response.authorized_amount < Decimal("52600"), (
    "Bug detected: rounding happened BEFORE conversion"
)
```

**Pass Criteria**:
- ✅ All 3 steps complete successfully
- ✅ Authorization response correct
- ✅ Transaction record complete and accurate
- ✅ Webhook emitted with all required fields
- ✅ No financial discrepancy (bug not present)
- ✅ Metadata preserved through entire flow

---

## Test Execution Summary

**Total Test Cases**: 25+ tests

| Priority | Count | Category Distribution |
|----------|-------|----------------------|
| P0 | 15 | 8 E2E, 5 Unit, 2 Integration |
| P1 | 8 | 2 E2E, 4 Unit, 2 Integration |
| P2 | 2 | 2 Integration |

**Coverage**:
- ✅ 5+ currency pairs (EUR/CLP, EUR/JPY, USD/KRW, GBP/CLP, EUR/USD, EUR/KWD)
- ✅ 8+ edge cases (min/max amounts, zero amounts, stale rates, missing rates, etc.)
- ✅ 3 test levels (Unit, Integration, E2E)
- ✅ AAA pattern compliance (100%)
- ✅ Bug reproduction (explicit bug simulation tests)

**Next Steps**:
1. Implement tests in pytest
2. Configure CI pipeline (see CI_CD_EXECUTION_PLAN.md)
3. Establish quality metrics dashboard (see QUALITY_METRICS_ANALYSIS.md)
4. Run baseline test execution and measure coverage

---

**Document Status**: ✅ Complete
**Compliance**: Google Testing Standards (AAA Pattern)
**Review Date**: 2026-02-25
