# Critical Questions to Challenge the Team
## Devil's Advocate Interrogation for Silent Currency Bug Challenge

**Document Version**: 1.0
**Date**: 2026-02-25
**Purpose**: Probe assumptions, identify blind spots, challenge test coverage
**Target Audience**: QA Team, Backend Engineers, Product Owners

---

## How to Use This Document

These questions are designed to:
1. **Challenge assumptions** about how the system works
2. **Expose edge cases** the team hasn't considered
3. **Test knowledge depth** of currency conversion mechanics
4. **Verify test coverage** is meaningful, not just comprehensive

**For each question**:
- ✅ **Can answer confidently with proof** → Good
- ⚠️ **Can answer but need to verify** → Medium risk
- ❌ **Cannot answer or unsure** → High risk, needs investigation

---

## SECTION 1: CORE LOGIC QUESTIONS

### Q1: Bidirectional Conversion Guarantee
**Question**: If I convert EUR 49.99 → CLP → back to EUR, do I get exactly EUR 49.99?

**Why This Matters**:
```python
# Customer pays EUR 49.99
# System converts: EUR 49.99 * 1052 = CLP 52,614.48 → CLP 52,614
# Customer disputes, wants refund
# System converts back: CLP 52,614 / 1052 = EUR 50.0133... → EUR 50.01

# Customer paid EUR 49.99, refunded EUR 50.01
# Merchant loses EUR 0.02 per transaction
# At 1M refunds/year: EUR 20,000 loss
```

**What You Need to Answer**:
- Does the system guarantee EUR 49.99 → CLP → EUR = EUR 49.99 ± tolerance?
- What's the tolerance? (0.01? 0.001?)
- How do you handle the loss/gain from rounding?
- Who absorbs the cost: merchant, customer, or platform?

**Follow-Up Questions**:
- What if FX rate changed between charge and refund?
- Do you store the original FX rate with the transaction?
- Does the refund use the SAME rate as the original charge?
- Can you prove this with a test?

**Test Coverage Check**:
```python
# Does this test exist?
def test_bidirectional_conversion_roundtrip():
    """Verify EUR → CLP → EUR returns original amount within tolerance."""
    agent = CurrencyAgent()

    original = Decimal("49.99")
    forward, rate = agent.convert_amount(original, "EUR", "CLP")
    backward, _ = agent.convert_amount(forward, "CLP", "EUR")

    # Should be within 1 cent
    assert abs(backward - original) <= Decimal("0.01")
```

---

### Q2: FX Rate Precision Limits
**Question**: What is the minimum and maximum precision for FX rates? Can the system handle rates with 12 decimal places?

**Why This Matters**:
```python
# Some FX providers return high-precision rates:
# Real Stripe API response:
{
  "object": "balance_transaction",
  "exchange_rate": 1052.123456789123456789  # 18 decimals!
}

# Your code uses:
"EUR_CLP": Decimal("1052.00")  # Only 2 decimals

# Difference per transaction:
# EUR 49.99 * 1052.123456 = CLP 52,615.09...
# EUR 49.99 * 1052.00 = CLP 52,614.48...
# Error: CLP 0.61 per transaction

# At 1M transactions/year: CLP 610,000 = EUR 580 variance
```

**What You Need to Answer**:
- What precision do your FX rates have? (2, 4, 6, 12 decimals?)
- Can the system handle variable precision rates?
- What happens if provider returns 18-decimal rate?
- Do you truncate, round, or reject high-precision rates?
- Is rate precision documented in the API contract?

**Follow-Up Questions**:
- Different providers have different precision (Stripe: 12, PayPal: 6, Adyen: 4)
- How do you normalize rates across providers?
- What if rate precision changes over time?
- Can you detect if a rate has suspiciously low precision? (e.g., exactly 1000.0)

**Test Coverage Check**:
```python
# Does this test exist?
def test_fx_rate_high_precision():
    """Verify system handles high-precision rates correctly."""
    agent = CurrencyAgent(fx_rates={
        "EUR_CLP": Decimal("1052.123456789123")  # 12 decimals
    })

    amount, rate = agent.convert_amount(
        Decimal("49.99"), "EUR", "CLP"
    )

    # Verify precision is maintained
    expected = Decimal("49.99") * Decimal("1052.123456789123")
    assert amount == round_to_currency(expected, "CLP")

def test_fx_rate_precision_limits():
    """Verify rate precision limits are documented and enforced."""
    # What's the maximum allowed precision?
    # What happens if exceeded?
    pass
```

---

### Q3: Zero-Amount Authorizations (Card Verification)
**Question**: Can the system authorize $0.00 for card verification? How does this work for zero-decimal currencies?

**Why This Matters**:
```python
# Card verification flow:
# 1. Customer adds card to wallet (no purchase yet)
# 2. System authorizes $0.00 to verify card is valid
# 3. Authorization succeeds, card saved

# But for zero-decimal settlement currencies:
# USD 0.00 → JPY 0 (OK?)
# EUR 0.00 → CLP 0 (OK?)

# Current code:
# validate_amount_for_currency(0, "CLP")
# 0 < min_amount (1) → FAILS

# Customer CANNOT save cards if merchant settles in CLP!
```

**What You Need to Answer**:
- Does the system support zero-dollar authorizations?
- Are they treated differently from regular charges?
- What happens if settlement currency is zero-decimal?
- Do you bypass minimum amount validation for card verification?
- How do you distinguish verification vs real charge?

**Follow-Up Questions**:
- Some payment methods don't support $0 auth (e.g., bank transfers)
- How do you handle "save payment method" for non-card methods?
- What if customer's card currency IS zero-decimal (JPY card)?
- Can you verify a JPY card with ¥0 authorization?

**Real-World Behavior**:
- **Stripe**: Supports $0 auth, sends "verify=true" flag
- **Adyen**: Uses 0.01 amount for verification, then voids
- **PayPal**: Doesn't support $0, requires real charge

**Test Coverage Check**:
```python
# Does this test exist?
def test_zero_amount_card_verification():
    """Verify zero-amount authorizations for card verification."""
    agent = PaymentAgent(CurrencyAgent())

    request = AuthorizationRequest(
        amount=Decimal("0.00"),
        currency="USD",
        settlement_currency="CLP",  # Zero-decimal!
        payment_method="CARD",
        metadata={"verify_only": True}
    )

    response = agent.authorize_payment(request)

    # Should succeed with special handling
    assert response.status == "AUTHORIZED"
    assert response.authorized_amount == Decimal("0")

def test_minimum_amount_bypassed_for_verification():
    """Verify min amount check is bypassed for card verification."""
    # EUR 0.00 should be allowed if verify=true
    # But rejected if verify=false
    pass
```

---

### Q4: Negative Amount Handling (Refunds)
**Question**: Are negative amounts explicitly forbidden in authorization, or implicitly handled?

**Why This Matters**:
```python
# Scenario 1: Refund sent to authorization endpoint
malicious_request = {
    "amount": "-100.00",  # Negative
    "currency": "EUR"
}

# What happens?
# A) Explicit rejection: "Amount must be positive" ✅
# B) Implicit handling: Processes as refund ⚠️
# C) Comparison error: -100 < 0.01 min → "Below minimum" ❓
# D) Crashes: Unexpected negative value ❌

# Current code (currency_agent.py line 203):
if amount < config.min_amount:
    return False, "Amount is below minimum"

# -100 < 0.01 → TRUE → Returns "below minimum"
# But error message is misleading!
# Should say "Amount must be positive"
```

**What You Need to Answer**:
- Are negative amounts explicitly validated (> 0 check)?
- Or do they fail implicitly due to min amount check?
- Is there a separate refund endpoint, or can refunds be negative?
- What's the error message for negative amounts?
- Does it clearly say "must be positive" or confusing "below minimum"?

**Follow-Up Questions**:
- What if amount is exactly 0? (Not negative, not positive)
- What if amount is -0.00? (Negative zero is valid in Python)
- What if amount is Decimal("-0")? (Different from 0?)
- Can you test this with property-based testing?

**Test Coverage Check**:
```python
# Does this test exist?
@pytest.mark.parametrize("amount", [
    Decimal("-100.00"),
    Decimal("-0.01"),
    Decimal("-0"),
    Decimal("0"),
    -100.0,  # float negative
    "-100",  # string negative
])
def test_negative_amounts_rejected(amount):
    """Verify negative/zero amounts are explicitly rejected."""
    agent = CurrencyAgent()

    is_valid, error = agent.validate_amount_for_currency(amount, "EUR")

    assert is_valid is False
    assert "positive" in error.lower()  # Not "below minimum"

def test_negative_zero_handling():
    """Verify negative zero is handled correctly."""
    assert Decimal("-0") == Decimal("0")  # Should be equal
    assert str(Decimal("-0")) == "0"  # Should normalize
```

---

### Q5: Rounding Philosophy
**Question**: Should the system favor customer (round down charges, round up refunds) or merchant?

**Why This Matters**:
```python
# Charge: EUR 49.99 → CLP 52,614.48
# Option A: Round down (favor customer) → CLP 52,614
# Option B: Round nearest (neutral) → CLP 52,614
# Option C: Round up (favor merchant) → CLP 52,615

# Refund: CLP 52,614 → EUR 50.0133...
# Option A: Round up (favor customer) → EUR 50.02
# Option B: Round nearest (neutral) → EUR 50.01
# Option C: Round down (favor merchant) → EUR 50.01

# Different philosophies:
# - Consumer protection laws: Always favor customer
# - Fair dealing: Neutral rounding (cancel out over time)
# - Merchant preference: Favor merchant (cover processing costs)

# Current code (currency.py line 69):
return Decimal(int(amount))  # int() rounds DOWN (toward zero)

# For positive amounts: ROUND_DOWN favors customer ✅
# But is this documented? Is this intentional?
```

**What You Need to Answer**:
- Is there a documented rounding philosophy?
- Who decided to use ROUND_DOWN vs ROUND_HALF_UP?
- Are there regulatory requirements? (e.g., consumer protection laws)
- Does rounding philosophy differ by country/currency?
- What about banker's rounding (ROUND_HALF_EVEN)?

**Follow-Up Questions**:
- Should refunds use different rounding than charges?
- What if total rounded errors exceed a threshold? (e.g., €1000/month)
- Do you track cumulative rounding impact?
- Can merchants override rounding mode?
- What about partial captures? (Authorize $100, capture $50)

**Regulatory Context**:
- **EU Consumer Law**: Must not systematically disadvantage consumers
- **US Truth in Lending**: Rounding must be disclosed
- **PCI-DSS**: Rounding logic must be auditable

**Test Coverage Check**:
```python
# Does this test exist?
def test_rounding_philosophy_documented():
    """Verify rounding philosophy is consistent and documented."""
    # Charge: Always rounds in favor of customer?
    # Refund: Always rounds in favor of customer?

    agent = CurrencyAgent()

    # Test many amounts, verify bias
    results = []
    for i in range(100):
        amount = Decimal(f"49.9{i}")  # EUR 49.90 to 49.999
        converted, _ = agent.convert_amount(amount, "EUR", "CLP")
        raw = amount * Decimal("1052")
        rounding_direction = "up" if converted > raw else "down"
        results.append(rounding_direction)

    # Verify consistent direction
    assert all(r == "down" for r in results)  # Always round down?

def test_cumulative_rounding_impact():
    """Verify cumulative rounding doesn't exceed thresholds."""
    # 1000 transactions
    # Total rounding error should be < 0.5% of total volume
    pass
```

---

## SECTION 2: SCALE AND PERFORMANCE QUESTIONS

### Q6: Currency Expansion Roadmap
**Question**: Next quarter adds Turkish Lira (TRY), Vietnamese Dong (VND), Nigerian Naira (NGN). How does the test suite adapt?

**Why This Matters**:
```python
# Current: 15 currencies
# Q2: +3 currencies = 18 total
# Q3: +5 currencies = 23 total
# Q4: +10 currencies = 33 total
# End of year: 33 currencies

# Test combinations:
# - Currency pairs: 33 * 32 = 1,056 pairs
# - Test cases per pair: 10 (various amounts)
# - Total tests: 10,560

# At 100ms per test: 1,056 seconds = 17.6 minutes
# At 500ms per test: 5,280 seconds = 88 minutes

# Challenge 1: Test suite becomes too slow
# Challenge 2: New currencies have unique properties
#   - TRY: Extremely volatile (5-10% daily)
#   - VND: Very high rates (1 USD = 25,000 VND)
#   - NGN: Subject to capital controls

# Challenge 3: Maintenance burden
# - 33 currency configs to maintain
# - 1,056 FX rates to mock
# - New edge cases per currency
```

**What You Need to Answer**:
- Is there a currency expansion roadmap?
- How many currencies by end of 2026?
- What's the test performance budget? (Max suite runtime?)
- How do you prioritize which currency pairs to test?
- Is there a sampling strategy? (Test 10% of pairs? Critical pairs only?)

**Follow-Up Questions**:
- How do you handle exotic currencies? (MRU, VEF, etc.)
- What about currencies that redenominate? (TRY removed 6 zeros in 2005)
- How do you test historically volatile currencies?
- Can tests adapt dynamically to new currencies?
- Is currency config generated or hardcoded?

**Scalability Strategies**:

**Option A: Exhaustive Testing (Slow)**
```python
# Test ALL currency pairs (1,056 pairs)
# Runtime: 88 minutes
# When: Nightly CI only
# Risk: Developers skip slow tests
```

**Option B: Critical Path Testing (Fast)**
```python
# Test only critical pairs:
CRITICAL_PAIRS = [
    ("EUR", "CLP"),  # The bug
    ("USD", "JPY"),  # High volume
    ("GBP", "COP"),  # Zero-decimal
    ("EUR", "KWD"),  # Three-decimal
    ("BRL", "MXN"),  # Latam regional
]

# Runtime: 5 seconds
# When: Every commit
# Risk: Miss edge cases in untested pairs
```

**Option C: Sampling Strategy (Balanced)**
```python
# Test coverage:
# - 100% of zero-decimal pairs (critical)
# - 100% of three-decimal pairs (complex)
# - 20% sample of two-decimal pairs (representative)
# - Rotate sampled pairs daily (different each day)

# Runtime: 10-15 minutes
# When: Pre-merge CI
# Risk: Probabilistic coverage
```

**Test Coverage Check**:
```python
# Does this test exist?
def test_currency_expansion_scalability():
    """Verify test suite scales to 64+ currencies."""
    # Can we add TRY without modifying 100 test files?
    # Is currency config data-driven?

    new_currency = CurrencyCode.TRY
    add_currency_config(new_currency, decimal_places=2)

    # All existing tests should still pass
    # New currency automatically included in parameterized tests

def test_dynamic_currency_pair_generation():
    """Verify currency pairs are generated dynamically."""
    currencies = list(CurrencyCode)
    pairs = generate_all_pairs(currencies)

    assert len(pairs) == len(currencies) * (len(currencies) - 1)

    # Verify each pair has default FX rate (even if mocked)
    for from_curr, to_curr in pairs:
        rate = get_fx_rate(from_curr, to_curr)
        assert rate > 0
```

---

### Q7: Test Suite Performance Budget
**Question**: At what point does the test suite become so slow that developers disable it?

**Why This Matters**:
```python
# Developer behavior:
# Suite < 1 minute: Runs on every file save ✅
# Suite 1-5 minutes: Runs before commit ✅
# Suite 5-15 minutes: Runs before push ⚠️
# Suite 15-30 minutes: Runs in CI only ⚠️
# Suite > 30 minutes: Developers skip ❌

# Current risk:
# - 15 currencies, 210 pairs, 10 tests each = 2,100 tests
# - At 100ms each = 210 seconds = 3.5 minutes (OK)
# - But 64 currencies = 40,320 tests = 67 minutes (BAD)

# When tests are too slow:
# 1. Developers run subset only (miss bugs)
# 2. Developers disable slow tests (miss bugs)
# 3. Tests only run in CI (slow feedback)
# 4. Tests become flaky due to timeouts
# 5. Team loses trust in tests
```

**What You Need to Answer**:
- What's the performance budget for the test suite?
- What's the current runtime? (Full suite, critical path)
- How often do developers run tests? (Every save? Before commit?)
- Are there different test tiers? (Fast, medium, slow)
- Can tests run in parallel? (pytest-xdist configured?)
- What's the slowest test? Can it be optimized?

**Follow-Up Questions**:
- Are tests I/O bound (DB, network) or CPU bound?
- Can slow tests be mocked? (FX API calls)
- Do tests share fixtures or create fresh state each time?
- Are there unnecessary waits? (time.sleep())
- Can tests be parallelized across multiple machines?

**Performance Optimization Strategies**:

```python
# Strategy 1: Parallel Execution
# pytest.ini already has pytest-xdist
# Run: pytest -n auto  # Use all CPU cores

# From: 3.5 minutes (single core)
# To: 1 minute (4 cores)

# ---

# Strategy 2: Test Tiering
# pytest.ini markers:
@pytest.mark.unit  # <1s each, run always
@pytest.mark.integration  # 1-5s each, run pre-commit
@pytest.mark.e2e  # 10-30s each, run in CI

# Run critical tests only:
# pytest -m "unit or integration"  # Skip slow e2e

# ---

# Strategy 3: Fixture Optimization
# Reuse expensive fixtures across tests

@pytest.fixture(scope="session")  # Create once per session
def currency_agent():
    return CurrencyAgent()

@pytest.fixture(scope="module")  # Create once per file
def payment_agent(currency_agent):
    return PaymentAgent(currency_agent)

# From: 100ms per test (create fresh agent)
# To: 10ms per test (reuse agent)

# ---

# Strategy 4: Mocking External Dependencies
# Don't call real FX APIs in tests

# SLOW:
def test_fx_rate_from_api():
    rate = requests.get("https://api.exchangerate.com/EUR_CLP")  # 500ms
    # ...

# FAST:
@responses.activate
def test_fx_rate_mocked():
    responses.add(
        responses.GET,
        "https://api.exchangerate.com/EUR_CLP",
        json={"rate": "1052.00"},
        status=200
    )
    # ... 5ms
```

**Test Coverage Check**:
```python
# Does this test exist?
def test_suite_performance_budget():
    """Verify test suite meets performance budget."""
    import time

    start = time.time()

    # Run critical path tests
    exit_code = pytest.main([
        "-m", "critical",  # Only critical tests
        "--tb=no",  # No traceback (faster)
        "--quiet"
    ])

    duration = time.time() - start

    # Budget: Critical tests must complete in <60 seconds
    assert duration < 60, f"Critical tests took {duration:.1f}s, budget is 60s"

    # Budget: Full suite must complete in <10 minutes
    # (Run in separate test, not on every commit)
```

---

### Q8: Test Determinism and Flakiness
**Question**: Are tests deterministic, or can they fail due to Decimal precision differences across environments?

**Why This Matters**:
```python
# Flaky test scenario:

def test_conversion_exact():
    """Test EUR to CLP conversion."""
    agent = CurrencyAgent()
    amount, _ = agent.convert_amount(
        Decimal("49.99"), "EUR", "CLP"
    )

    assert amount == Decimal("52614")  # Exact match

# This test could be flaky if:
# 1. Python version differs (Decimal behavior changed in 3.9)
# 2. OS differs (Windows vs Linux float representation)
# 3. Decimal context differs (precision settings)
# 4. Parallel execution (shared state contamination)

# Example flaky failure:
# Expected: Decimal("52614")
# Actual: Decimal("52614.000000000001")

# Why?
# - Different rounding mode in getcontext()
# - Float contamination from somewhere
# - Precision loss in intermediate calculation

# Impact:
# - Test fails randomly (not every time)
# - Developers lose trust ("tests are broken")
# - CI becomes unreliable
# - Real bugs masked by flaky tests
```

**What You Need to Answer**:
- Are tests deterministic? (Same input → same output, always)
- Have you tested on different OS? (Linux, macOS, Windows)
- Have you tested on different Python versions? (3.9, 3.10, 3.11, 3.12)
- Do you set explicit Decimal context? (precision, rounding mode)
- Are there any random elements? (UUIDs, timestamps, random amounts)
- Can tests run in any order? (No dependencies between tests)
- Can tests run in parallel safely? (No shared mutable state)

**Follow-Up Questions**:
- What if two tests modify the same global state?
- What if tests depend on current time? (FX rate staleness checks)
- What if tests depend on external services? (FX API calls)
- How do you reproduce a flaky test failure?
- Do you track flaky test rate? (% of test runs that fail sporadically)

**Determinism Techniques**:

```python
# Technique 1: Explicit Decimal Context
from decimal import getcontext, ROUND_HALF_UP

@pytest.fixture(scope="session", autouse=True)
def set_decimal_context():
    """Set consistent Decimal context for all tests."""
    ctx = getcontext()
    ctx.prec = 28  # Precision
    ctx.rounding = ROUND_HALF_UP  # Rounding mode
    return ctx

# ---

# Technique 2: Freeze Time
from freezegun import freeze_time

@freeze_time("2026-02-25 12:00:00")
def test_fx_rate_staleness():
    """Test with frozen time (deterministic)."""
    agent = CurrencyAgent()
    # Time is now always 2026-02-25 12:00:00
    # No flakiness from "current time"

# ---

# Technique 3: Tolerance-Based Assertions
def assert_decimal_equal(actual, expected, tolerance=Decimal("0.01")):
    """Assert Decimals are equal within tolerance."""
    diff = abs(actual - expected)
    assert diff <= tolerance, f"{actual} != {expected}, diff={diff}"

# Instead of:
assert amount == Decimal("52614")  # Exact (flaky)

# Use:
assert_decimal_equal(amount, Decimal("52614"), Decimal("0.01"))  # Tolerant

# ---

# Technique 4: Isolation
@pytest.fixture(autouse=True)
def isolate_tests(monkeypatch):
    """Isolate each test (no shared state)."""
    # Reset any global state
    # Clear caches
    # Restore default config
    yield
    # Cleanup after test

# ---

# Technique 5: Deterministic Test Data
# Don't use random amounts
BAD:
amount = Decimal(str(random.uniform(1, 100)))  # Random!

GOOD:
@pytest.fixture
def test_amounts():
    """Deterministic test amounts."""
    return [
        Decimal("49.99"),
        Decimal("0.01"),
        Decimal("999999.99"),
        # ... known values
    ]
```

**Test Coverage Check**:
```python
# Does this test exist?
def test_decimal_context_is_consistent():
    """Verify Decimal context is set correctly."""
    from decimal import getcontext

    ctx = getcontext()

    assert ctx.prec == 28
    assert ctx.rounding == ROUND_HALF_UP  # Or whatever you choose

def test_no_shared_state_between_tests():
    """Verify tests don't contaminate each other."""
    # Run test A, modify some state
    # Run test B, verify state is clean

def test_parallel_execution_safety():
    """Verify tests can run in parallel without conflicts."""
    # pytest -n 4 should produce same results as pytest
    pass

def test_cross_platform_consistency():
    """Verify tests pass on Linux, macOS, Windows."""
    # Run in CI matrix
    # os: [ubuntu-latest, macos-latest, windows-latest]
```

---

## SECTION 3: PRODUCTION READINESS QUESTIONS

### Q9: Bug Injection Testing
**Question**: Can you add the actual bug to the code (round_before_conversion=True) and verify tests catch it?

**Why This Matters**:
```python
# The ULTIMATE test of test suite quality:
# 1. Inject the real bug
# 2. Run tests
# 3. Do tests fail? (They should!)

# If tests DON'T fail:
# - Tests are testing the wrong thing
# - Tests are too lenient (big tolerances)
# - Tests don't cover the bug scenario

# This is called MUTATION TESTING:
# - Introduce bugs systematically
# - Verify tests catch them
# - Measure "mutation score" (% of bugs caught)

# Example:
# Original: round_before_conversion=False (correct)
# Mutation: round_before_conversion=True (bug)
# Expected: Tests fail with error about wrong amount

# What if tests PASS with the bug?
# - Test suite is USELESS for this bug
# - Would not have prevented the €2.3M incident
```

**What You Need to Answer**:
- Have you tried injecting the bug?
- Which tests fail when bug is present?
- How quickly do tests fail? (First test? Last test?)
- Is the error message clear? ("Expected 52614, got 51500")
- Can you automate bug injection? (Mutation testing framework)

**Follow-Up Questions**:
- What other bugs can you inject?
  - Wrong rounding mode (ROUND_UP instead of ROUND_DOWN)
  - Wrong conversion order (convert rate instead of amount)
  - Float contamination (use float instead of Decimal)
  - Off-by-one errors (amount + 1)
- How many mutations can tests catch? (Mutation score)
- Are there bugs tests CAN'T catch? (Why not?)

**Bug Injection Test**:

```python
# Does this test exist?
def test_bug_injection_round_before_conversion():
    """
    Verify tests catch the €2.3M bug if reintroduced.

    This is the CRITICAL test: If this passes, your test suite
    would have prevented the production incident.
    """
    # Create buggy agent
    buggy_agent = CurrencyAgent()

    # Process payment with BUG
    buggy_amount, _ = buggy_agent.convert_amount(
        amount=Decimal("49.99"),
        from_currency="EUR",
        to_currency="CLP",
        round_before_conversion=True  # ← THE BUG
    )

    # Create correct agent
    correct_agent = CurrencyAgent()

    # Process payment CORRECTLY
    correct_amount, _ = correct_agent.convert_amount(
        amount=Decimal("49.99"),
        from_currency="EUR",
        to_currency="CLP",
        round_before_conversion=False  # ← CORRECT
    )

    # Verify they're DIFFERENT
    assert buggy_amount != correct_amount, \
        "Bug injection didn't change output! Tests won't catch bug."

    # Verify the EXACT bug impact
    assert buggy_amount == Decimal("51500"), \
        f"Bug should produce CLP 51,500, got {buggy_amount}"
    assert correct_amount == Decimal("52614"), \
        f"Correct should produce CLP 52,614, got {correct_amount}"

    # Verify loss amount
    loss = correct_amount - buggy_amount
    assert loss == Decimal("1114"), \
        f"Loss per transaction should be CLP 1,114, got {loss}"

    print(f"✓ Bug injection test passed!")
    print(f"  Buggy: {buggy_amount} CLP")
    print(f"  Correct: {correct_amount} CLP")
    print(f"  Loss: {loss} CLP")

# ---

# Mutation testing with pytest-mutagen or mutmut:
# pip install mutmut

# Run mutation testing:
# mutmut run --paths-to-mutate=framework/agents/

# Example mutations:
# - Change + to -
# - Change * to /
# - Change < to <=
# - Change and to or
# - Remove function calls
# - Change constant values

# Measure mutation score:
# mutation_score = killed_mutants / total_mutants
# Target: >80% mutation score
```

---

### Q10: False Positive Rate
**Question**: How often do tests fail when the code is correct?

**Why This Matters**:
```python
# False positive: Test fails, but code is correct

# Causes:
# 1. Flaky tests (timing, environment differences)
# 2. Overly strict assertions (exact match instead of tolerance)
# 3. Hardcoded test data (breaks when data changes)
# 4. Environment dependencies (timezone, locale)

# Impact:
# - Developers ignore test failures ("it's flaky, just rerun")
# - Real bugs masked by false positives
# - Loss of trust in test suite
# - Wasted time investigating non-bugs

# Acceptable false positive rate:
# - <0.1%: Excellent (1 false positive per 1000 runs)
# - 0.1-1%: Good (1 per 100 runs)
# - 1-5%: Concerning (1 per 20 runs)
# - >5%: Unacceptable (1 per 20 runs, developers will ignore)
```

**What You Need to Answer**:
- Have you measured false positive rate?
- How many times have tests failed spuriously?
- Do you track flaky tests? (Which tests, how often)
- Do you have retry logic? (pytest-retry configured)
- How do you distinguish real failure vs flaky failure?

**Follow-Up Questions**:
- What causes most false positives?
- Do tests have time-based assertions? (FX rate staleness)
- Do tests depend on external services? (Network flakiness)
- Do tests have race conditions? (Concurrent execution)
- Can you reproduce false positives consistently?

**False Positive Reduction**:

```python
# Technique 1: Measure Flaky Test Rate
# pytest-json-report generates test result JSON

import json
from collections import Counter

def analyze_test_flakiness(test_report_dir):
    """Analyze test flakiness from historical reports."""
    test_results = []

    for report_file in glob(f"{test_report_dir}/test_report_*.json"):
        with open(report_file) as f:
            data = json.load(f)
            for test in data["tests"]:
                test_results.append({
                    "name": test["nodeid"],
                    "outcome": test["outcome"],  # passed, failed, skipped
                    "timestamp": test["call"]["duration"]
                })

    # Find tests that sometimes pass, sometimes fail
    test_outcomes = {}
    for result in test_results:
        name = result["name"]
        if name not in test_outcomes:
            test_outcomes[name] = []
        test_outcomes[name].append(result["outcome"])

    # Identify flaky tests
    flaky_tests = {}
    for name, outcomes in test_outcomes.items():
        outcome_counts = Counter(outcomes)
        if len(outcome_counts) > 1:  # Multiple different outcomes
            pass_rate = outcome_counts["passed"] / len(outcomes)
            flaky_tests[name] = {
                "total_runs": len(outcomes),
                "passes": outcome_counts["passed"],
                "failures": outcome_counts.get("failed", 0),
                "pass_rate": pass_rate,
                "flakiness": 1 - pass_rate if pass_rate > 0.5 else pass_rate
            }

    # Report flakiest tests
    for name, stats in sorted(
        flaky_tests.items(),
        key=lambda x: x[1]["flakiness"],
        reverse=True
    )[:10]:
        print(f"Flaky: {name}")
        print(f"  Pass rate: {stats['pass_rate']:.1%}")
        print(f"  {stats['passes']} passes, {stats['failures']} failures")

# ---

# Technique 2: Automatic Retry for Flaky Tests
# pytest.ini already has pytest-retry

@pytest.mark.flaky(reruns=3, reruns_delay=1)
def test_potentially_flaky():
    """This test will retry up to 3 times if it fails."""
    # ...

# ---

# Technique 3: Quarantine Flaky Tests
# pytest.ini markers:

@pytest.mark.quarantine  # Known flaky, don't run by default
def test_known_flaky():
    # ...

# Run stable tests only:
# pytest -m "not quarantine"

# Run quarantined tests separately:
# pytest -m "quarantine" --maxfail=999  # Allow many failures
```

---

### Q11: Code Coverage vs Bug Coverage
**Question**: If you achieve 100% code coverage, does that guarantee 100% bug coverage?

**Why This Matters**:
```python
# Code coverage measures: "Did tests execute this line?"
# Bug coverage measures: "Did tests catch bugs in this line?"

# These are NOT the same!

# Example:
def convert_amount(amount, rate):
    return amount * rate  # ← 100% code coverage

# Test:
def test_convert():
    result = convert_amount(Decimal("10"), Decimal("2"))
    assert result == Decimal("20")  # PASSES, 100% coverage

# But this test does NOT catch:
# - Float contamination (amount=10.0)
# - Negative amounts (amount=-10)
# - Zero amounts (amount=0)
# - Overflow (amount=MAX_INT)
# - Wrong rate (rate=0, rate=negative)
# - Precision loss (rate=1.123456789)

# 100% code coverage, <10% bug coverage!

# Code coverage is necessary but not sufficient
```

**What You Need to Answer**:
- What's the current code coverage? (lines, branches)
- What's the estimated bug coverage? (mutation score)
- Are there critical paths with low coverage?
- Do tests cover edge cases, or just happy path?
- Can you measure "meaningful coverage"?

**Follow-Up Questions**:
- What if code is covered but with weak assertions? (assert True)
- What if code is covered but with wrong test data?
- What if code is covered but error paths are not?
- How do you know tests are testing the RIGHT thing?

**Coverage Analysis**:

```python
# Technique 1: Branch Coverage (Better than Line Coverage)
# pytest-cov can measure branch coverage

# pytest --cov=framework --cov-report=term-missing --cov-branch

# Example:
def validate_amount(amount):
    if amount < 0:  # ← Branch 1
        raise ValueError("Negative")
    if amount > MAX:  # ← Branch 2
        raise ValueError("Too large")
    return True  # ← Branch 3

# Line coverage: 100% if any test calls this function
# Branch coverage: Need tests for:
#   - amount < 0 (branch 1)
#   - amount > MAX (branch 2)
#   - Valid amount (branch 3)

# ---

# Technique 2: Mutation Testing (Bug Coverage)
# mutmut or pytest-mutagen

# Measures: "If I introduce a bug, do tests catch it?"

# Example mutation:
# Original: if amount < 0:
# Mutated: if amount <= 0:

# If tests still pass → weak test
# If tests fail → good test

# ---

# Technique 3: Property-Based Testing (Comprehensive Coverage)
# hypothesis library

from hypothesis import given, strategies as st

@given(
    amount=st.decimals(min_value=-1000, max_value=1000),
    rate=st.decimals(min_value=-100, max_value=100)
)
def test_conversion_properties(amount, rate):
    """Test conversion with random inputs (property-based)."""
    # Property 1: Converting and converting back = original
    if amount > 0 and rate > 0:
        converted = convert_amount(amount, rate)
        back = convert_amount(converted, Decimal("1") / rate)
        assert abs(back - amount) < Decimal("0.01")

    # Property 2: Converting by 1 = same amount
    assert convert_amount(amount, Decimal("1")) == amount

    # Property 3: Order matters
    # amount * rate * inverse = amount
    # (tested above)

# Hypothesis generates 1000s of random test cases
# Finds edge cases you didn't think of
```

**Test Coverage Check**:
```python
# Does this test exist?
def test_coverage_is_meaningful():
    """Verify coverage measures meaningful tests, not just execution."""
    # Can't really test this, but document:
    # - Code coverage: 95%+ (current: ?)
    # - Branch coverage: 90%+ (current: ?)
    # - Mutation score: 80%+ (current: ?)

def test_critical_paths_are_covered():
    """Verify all critical paths have tests."""
    critical_paths = [
        "currency_agent.convert_amount",
        "currency_agent.validate_amount_for_currency",
        "payment_agent.authorize_payment",
        "currency.round_amount",
    ]

    coverage_data = get_coverage_data()

    for path in critical_paths:
        assert coverage_data[path]["coverage"] == 100, \
            f"Critical path {path} only has {coverage_data[path]['coverage']}% coverage"
```

---

### Q12: Integration with Real Providers
**Question**: Tests mock the FX service. What if the real service returns different precision or format?

**Why This Matters**:
```python
# Your tests:
def test_conversion():
    agent = CurrencyAgent(fx_rates={
        "EUR_CLP": Decimal("1052.00")  # Mocked, 2 decimals
    })
    # ...

# Real Stripe API:
{
  "conversion_rate": "1052.123456",  # 6 decimals!
  "converted_amount": 5261400,  # In "minor units" (CLP 52,614.00)
  "fees": [{
    "amount": 15900,  # CLP 159
    "type": "currency_conversion"
  }]
}

# Your code expects:
# - Rate as Decimal (✓)
# - Amount in standard units (✗ Stripe uses minor units)
# - No fees (✗ Stripe includes fees)

# When you integrate:
# - Rate precision mismatch (2 vs 6 decimals)
# - Amount format mismatch (52614 vs 5261400)
# - Unexpected fields (fees, metadata)
# - Different error codes

# Result: Integration fails in production, even though tests pass
```

**What You Need to Answer**:
- Have you tested with real provider APIs? (Sandbox mode)
- Do you have integration tests (not just unit tests)?
- Do mocks match real provider behavior exactly?
- Do you validate mock data against API schema?
- Have you tested with multiple providers? (Stripe, Adyen, PayPal)

**Follow-Up Questions**:
- What if provider API changes? (New fields, deprecations)
- How do you keep mocks in sync with real APIs?
- Do you test against provider sandbox regularly?
- Can you replay real API responses in tests?
- What's your strategy for provider-specific quirks?

**Integration Testing Strategies**:

```python
# Strategy 1: Contract Testing (Pact)
# Define API contract, verify both sides

# provider_contract.json:
{
  "request": {
    "method": "GET",
    "path": "/v1/rates/EUR/CLP"
  },
  "response": {
    "status": 200,
    "body": {
      "rate": "1052.123456",  # ← Documented precision
      "timestamp": "2026-02-25T12:00:00Z"
    }
  }
}

# Test verifies mock matches contract
# Provider verifies API matches contract

# ---

# Strategy 2: Record/Replay (VCR.py)
# Record real API responses, replay in tests

import vcr

@vcr.use_cassette('fixtures/vcr/fx_rate_eur_clp.yaml')
def test_real_api_response():
    """Test with recorded real API response."""
    response = requests.get("https://api.stripe.com/v1/rates/EUR/CLP")
    # First run: Records response to cassette
    # Subsequent runs: Replays from cassette (no network)

    assert response.json()["rate"] == "1052.123456"

# ---

# Strategy 3: Provider Sandbox Testing
# Run tests against real sandbox APIs (daily)

@pytest.mark.requires_external  # Skip in CI, run nightly
def test_stripe_sandbox_integration():
    """Test against real Stripe sandbox API."""
    stripe.api_key = os.getenv("STRIPE_SANDBOX_KEY")

    response = stripe.BalanceTransaction.create(
        amount=4999,  # EUR 49.99
        currency="eur",
        settlement_currency="clp"
    )

    # Verify real API behavior
    assert response.settlement_currency == "clp"
    assert response.conversion_rate  # Has rate
    assert len(response.conversion_rate) > 4  # High precision

# ---

# Strategy 4: Schema Validation
# Validate mock responses match provider schema

from jsonschema import validate

stripe_response_schema = {
    "type": "object",
    "properties": {
        "conversion_rate": {"type": "string", "pattern": "^\\d+\\.\\d{6}$"},
        "converted_amount": {"type": "integer"},
        "fees": {"type": "array"}
    },
    "required": ["conversion_rate", "converted_amount"]
}

def test_mock_matches_schema():
    """Verify mock responses match real API schema."""
    mock_response = {
        "conversion_rate": "1052.123456",
        "converted_amount": 5261400
    }

    # Should not raise exception
    validate(instance=mock_response, schema=stripe_response_schema)
```

---

## SECTION 4: COMPLIANCE AND DOCUMENTATION QUESTIONS

### Q13: Regulatory Compliance
**Question**: What country-specific transaction limits must be enforced? How do you test compliance?

**Why This Matters**:
```python
# Different countries have different limits:

REGULATORY_LIMITS = {
    "BR": {  # Brazil
        "max_transaction": Decimal("5000"),  # BRL 5K (AML)
        "max_daily": Decimal("20000"),  # BRL 20K (Central Bank)
        "requires_kyc_above": Decimal("5000")
    },
    "IN": {  # India
        "max_transaction": Decimal("200000"),  # INR 200K (RBI)
        "max_yearly": Decimal("700000"),  # INR 700K (FEMA)
        "requires_pan_above": Decimal("50000")
    },
    "EU": {  # European Union
        "max_no_kyc": Decimal("10000"),  # EUR 10K (PSD2)
        "max_cash_equivalent": Decimal("1000")  # EUR 1K
    },
    "US": {  # United States
        "report_irs_above": Decimal("10000"),  # USD 10K (FinCEN)
        "aggregate_reporting": True  # Multiple < 10K = report
    }
}

# Your code:
# No regulatory limit checks!
# Max amount is arbitrary (EUR 999,999.99)

# Risk:
# - Process illegal transactions
# - Fail compliance audits
# - Regulatory fines (up to 4% of revenue)
# - License revocation
```

**What You Need to Answer**:
- Are regulatory limits enforced?
- Are limits country-specific or global?
- Do limits apply to single transaction, daily, monthly, yearly?
- How do you handle aggregate limits? (Multiple small transactions)
- Are limits currency-specific? (EUR 10K = different in local currency)

**Follow-Up Questions**:
- What if customer is from country A, merchant from country B, settling in currency C?
- What if limits change? (Regulatory updates)
- Do you have approval workflow for near-limit transactions?
- How do you test compliance without real transactions?
- Do you generate compliance reports?

---

### Q14: Accounting Standards
**Question**: Does the system comply with GAAP or IFRS rounding requirements? How is this tested?

**Why This Matters**:
```python
# Different accounting standards require different rounding:

# GAAP (US Generally Accepted Accounting Principles):
# - Round to nearest cent
# - Use ROUND_HALF_UP (0.5 rounds to 1)
# - All calculations must be auditable

# IFRS (International Financial Reporting Standards):
# - Round to nearest cent
# - Use ROUND_HALF_EVEN (banker's rounding)
# - FX gains/losses must be reported separately

# Current code:
# return Decimal(int(amount))  # ROUND_DOWN (toward zero)

# Neither GAAP nor IFRS compliant!

# Impact:
# - Failed audits
# - Financial restatements
# - Public company: SEC violations
# - Investor lawsuits
```

**What You Need to Answer**:
- Which accounting standard does your system follow?
- Is rounding mode documented and consistent?
- Can auditors trace every rounding decision?
- Are FX gains/losses tracked separately?
- How do you test accounting compliance?

---

## SUMMARY SCORECARD

Use this scorecard to assess your readiness:

| Question | Answer | Status | Risk |
|----------|--------|--------|------|
| Q1: Bidirectional conversion guarantee | ☐ Yes ☐ No ☐ Unknown | | |
| Q2: FX rate precision limits | ☐ Yes ☐ No ☐ Unknown | | |
| Q3: Zero-amount authorizations | ☐ Yes ☐ No ☐ Unknown | | |
| Q4: Negative amount handling | ☐ Yes ☐ No ☐ Unknown | | |
| Q5: Rounding philosophy | ☐ Yes ☐ No ☐ Unknown | | |
| Q6: Currency expansion roadmap | ☐ Yes ☐ No ☐ Unknown | | |
| Q7: Test suite performance budget | ☐ Yes ☐ No ☐ Unknown | | |
| Q8: Test determinism | ☐ Yes ☐ No ☐ Unknown | | |
| Q9: Bug injection testing | ☐ Yes ☐ No ☐ Unknown | | |
| Q10: False positive rate | ☐ Yes ☐ No ☐ Unknown | | |
| Q11: Bug coverage (not just code coverage) | ☐ Yes ☐ No ☐ Unknown | | |
| Q12: Integration with real providers | ☐ Yes ☐ No ☐ Unknown | | |
| Q13: Regulatory compliance | ☐ Yes ☐ No ☐ Unknown | | |
| Q14: Accounting standards | ☐ Yes ☐ No ☐ Unknown | | |

**Scoring**:
- ✅ 12-14 "Yes": Excellent, production-ready
- ⚠️ 8-11 "Yes": Good, needs some work
- ❌ <8 "Yes": High risk, significant gaps

**Recommended Actions**:
1. Any "Unknown" → Investigate immediately (blocking issue)
2. Any "No" for Q1, Q4, Q5, Q9 → P0 (would not catch €2.3M bug)
3. Any "No" for Q7, Q8, Q10 → P1 (test suite quality issues)
4. Any "No" for Q13, Q14 → P2 (compliance risk)

---

## FINAL CHALLENGE

**The Ultimate Test**: Can you answer this question confidently?

> "If a developer introduces the exact bug that caused the €2.3M incident (rounding before conversion instead of after), will your test suite catch it before it reaches production?"

If your answer is anything other than **"YES, ABSOLUTELY, HERE'S THE TEST THAT WOULD FAIL"**, then your test suite is not production-ready.

**Prove it.**
