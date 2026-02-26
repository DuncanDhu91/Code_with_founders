"""Pytest configuration and shared fixtures for currency conversion tests."""

import pytest
import logging
from decimal import getcontext, ROUND_HALF_UP

from framework.agents.currency_agent import CurrencyAgent
from framework.agents.payment_agent import PaymentAgent


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest environment."""
    # Set decimal context for consistent rounding
    ctx = getcontext()
    ctx.prec = 28  # High precision for financial calculations
    ctx.rounding = ROUND_HALF_UP  # Standard rounding mode

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


# ============================================================================
# Shared Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def decimal_context():
    """
    Provide decimal context for all tests.

    This ensures consistent rounding behavior across all tests.
    """
    return getcontext()


@pytest.fixture
def currency_agent():
    """
    Provide a fresh CurrencyAgent instance for each test.

    Uses default test FX rates.
    """
    return CurrencyAgent()


@pytest.fixture
def currency_agent_with_bug():
    """
    Provide CurrencyAgent configured to use in bug simulation.

    Note: The bug is controlled via convert_amount() parameter,
    this fixture is for consistency.
    """
    return CurrencyAgent()


@pytest.fixture
def payment_agent(currency_agent):
    """
    Provide a PaymentAgent with correct logic (no bug).

    Args:
        currency_agent: Injected CurrencyAgent fixture

    Yields:
        PaymentAgent instance
    """
    agent = PaymentAgent(
        currency_agent=currency_agent,
        simulate_bug=False
    )
    yield agent
    # Cleanup: Reset agent state after test
    agent.reset()


@pytest.fixture
def payment_agent_with_bug(currency_agent):
    """
    Provide a PaymentAgent with bug simulation enabled.

    Args:
        currency_agent: Injected CurrencyAgent fixture

    Yields:
        PaymentAgent instance with bug
    """
    agent = PaymentAgent(
        currency_agent=currency_agent,
        simulate_bug=True
    )
    yield agent
    # Cleanup: Reset agent state after test
    agent.reset()


# ============================================================================
# Test Markers
# ============================================================================

def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers",
        "bug_detection: Tests that verify the bug is caught"
    )
    config.addinivalue_line(
        "markers",
        "critical: Critical tests that must pass (P0)"
    )
    config.addinivalue_line(
        "markers",
        "edge_case: Edge case tests"
    )
    config.addinivalue_line(
        "markers",
        "multi_currency: Multi-currency conversion tests"
    )
    config.addinivalue_line(
        "markers",
        "slow: Slow-running tests (>1 second)"
    )


# ============================================================================
# Hooks for Test Reporting
# ============================================================================

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Make test results available to fixtures.

    This allows fixtures to know if a test failed.
    """
    outcome = yield
    rep = outcome.get_result()

    # Store test result for use in fixtures
    setattr(item, f"rep_{rep.when}", rep)


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def bug_detector_amounts():
    """
    Provide amounts that expose the rounding bug.

    Returns:
        List of Decimal amounts
    """
    from decimal import Decimal
    return [
        Decimal("49.99"),  # Rounds to 50.00
        Decimal("99.99"),  # Rounds to 100.00
        Decimal("149.99"), # Rounds to 150.00
        Decimal("0.01"),   # Minimum amount edge case
        Decimal("10.49"),  # Rounds down to 10.00
    ]


@pytest.fixture
def critical_currency_pairs():
    """
    Provide critical currency pairs for testing.

    Returns:
        List of (from_currency, to_currency) tuples
    """
    from framework.models.currency import CurrencyCode
    return [
        (CurrencyCode.EUR, CurrencyCode.CLP),  # The incident
        (CurrencyCode.EUR, CurrencyCode.JPY),  # High volume
        (CurrencyCode.USD, CurrencyCode.KRW),  # Common pair
        (CurrencyCode.GBP, CurrencyCode.COP),  # Zero-decimal
        (CurrencyCode.EUR, CurrencyCode.KWD),  # Three-decimal
    ]


@pytest.fixture
def test_fx_rates():
    """
    Provide test FX rates.

    Returns:
        Dict of FX rates
    """
    from decimal import Decimal
    return {
        "EUR_CLP": Decimal("1052.00"),
        "EUR_JPY": Decimal("161.25"),
        "USD_KRW": Decimal("1332.15"),
        "EUR_USD": Decimal("1.0850"),
        "EUR_KWD": Decimal("0.3345"),
    }


# ============================================================================
# Performance Monitoring
# ============================================================================

@pytest.fixture(autouse=True)
def track_test_performance(request):
    """
    Track test execution time.

    Warns if a test takes longer than expected.
    """
    import time

    start_time = time.time()
    yield
    duration = time.time() - start_time

    # Warn if test is slow (>1 second)
    if duration > 1.0:
        logging.warning(
            f"Test {request.node.nodeid} took {duration:.2f} seconds "
            f"(expected <1.0s)"
        )


# ============================================================================
# Logging Configuration
# ============================================================================

@pytest.fixture
def caplog_info(caplog):
    """
    Capture INFO level logs.

    Args:
        caplog: pytest's built-in log capture fixture

    Returns:
        caplog configured for INFO level
    """
    caplog.set_level(logging.INFO)
    return caplog


@pytest.fixture
def caplog_debug(caplog):
    """
    Capture DEBUG level logs.

    Args:
        caplog: pytest's built-in log capture fixture

    Returns:
        caplog configured for DEBUG level
    """
    caplog.set_level(logging.DEBUG)
    return caplog
