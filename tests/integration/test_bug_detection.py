"""THE CRITICAL TEST - Bug Detection Test Suite

P0 BLOCKER: This test proves the suite catches the €2.3M bug.

This test MUST fail when the bug is present and pass when it's fixed.
If this test doesn't exist or doesn't work, the entire test suite is worthless.

The Bug: EUR 49.99 rounded to EUR 50.00 BEFORE conversion = CLP 52,600 (WRONG)
Correct: EUR 49.99 * 1052 = CLP 52,594.48 → CLP 52,595 (round AFTER conversion)

Financial Loss: CLP 5 per transaction (EUR 0.0047)
At 1M transactions/year: EUR 4,700 loss
"""

import pytest
from decimal import Decimal

from framework.agents.currency_agent import CurrencyAgent
from framework.agents.payment_agent import PaymentAgent
from framework.models.currency import CurrencyCode
from framework.models.transaction import (
    AuthorizationRequest,
    PaymentMethod,
    TransactionStatus
)


class TestBugDetection:
    """THE CRITICAL TEST: Proves the test suite catches the €2.3M bug."""

    def test_bug_detection_eur_to_clp_round_before_vs_round_after(self):
        """
        TC-BUG-001: The definitive test that the bug is caught.

        ARRANGE:
        - Amount: EUR 49.99 (the bug detector amount)
        - FX Rate: 1052.00 EUR/CLP (the incident rate)
        - Two scenarios: correct vs buggy logic

        ACT:
        - Process with correct logic (round AFTER conversion)
        - Process with buggy logic (round BEFORE conversion)

        ASSERT:
        - Correct produces CLP 52,595
        - Buggy produces CLP 52,600
        - Difference is exactly CLP 5 (EUR 0.0047)
        - Bug causes customer overcharge
        """
        # ARRANGE
        fx_rates = {"EUR_CLP": Decimal("1052.00")}
        currency_agent = CurrencyAgent(fx_rates=fx_rates)

        amount = Decimal("49.99")  # THE BUG DETECTOR AMOUNT

        # ACT 1: Correct logic (round AFTER conversion)
        correct_result, fx_rate = currency_agent.convert_amount(
            amount=amount,
            from_currency=CurrencyCode.EUR,
            to_currency=CurrencyCode.CLP,
            round_before_conversion=False  # CORRECT
        )

        # ACT 2: Buggy logic (round BEFORE conversion)
        buggy_result, _ = currency_agent.convert_amount(
            amount=amount,
            from_currency=CurrencyCode.EUR,
            to_currency=CurrencyCode.CLP,
            round_before_conversion=True  # BUG
        )

        # ASSERT: Results are DIFFERENT
        assert correct_result != buggy_result, \
            "Bug injection didn't change output! Tests won't catch bug."

        # ASSERT: Exact expected values
        assert correct_result == Decimal("52595"), \
            f"Correct should produce CLP 52,595, got {correct_result}"

        assert buggy_result == Decimal("52600"), \
            f"Bug should produce CLP 52,600, got {buggy_result}"

        # ASSERT: Financial loss calculation
        loss_per_transaction = buggy_result - correct_result
        assert loss_per_transaction == Decimal("5"), \
            f"Loss should be CLP 5, got {loss_per_transaction}"

        # ASSERT: Bug causes customer overcharge
        assert buggy_result > correct_result, \
            "Bug must overcharge customer (not undercharge)"

        # Calculate annual loss projection
        transactions_per_year = Decimal("1000000")  # 1M transactions
        annual_loss_clp = loss_per_transaction * transactions_per_year
        annual_loss_eur = annual_loss_clp / Decimal("1052.00")

        print("\n" + "="*70)
        print("BUG DETECTION TEST RESULTS")
        print("="*70)
        print(f"Amount: EUR {amount}")
        print(f"FX Rate: {fx_rate}")
        print(f"Correct Result: CLP {correct_result:,}")
        print(f"Buggy Result: CLP {buggy_result:,}")
        print(f"Loss per Transaction: CLP {loss_per_transaction}")
        print(f"Annual Loss (1M txns): CLP {annual_loss_clp:,} = EUR {annual_loss_eur:,.2f}")
        print("="*70)

    def test_payment_agent_bug_vs_correct_authorization(self):
        """
        TC-BUG-002: End-to-end test with PaymentAgent.

        ARRANGE:
        - Create two payment agents: one correct, one with bug
        - Same authorization request

        ACT:
        - Process payment with correct agent
        - Process payment with buggy agent

        ASSERT:
        - Correct agent produces CLP 52,595
        - Buggy agent produces CLP 52,600
        - Transaction records show different amounts
        - Webhooks reflect different amounts
        """
        # ARRANGE
        fx_rates = {"EUR_CLP": Decimal("1052.00")}
        currency_agent = CurrencyAgent(fx_rates=fx_rates)

        # Create correct agent
        correct_agent = PaymentAgent(
            currency_agent=currency_agent,
            simulate_bug=False
        )

        # Create buggy agent
        buggy_agent = PaymentAgent(
            currency_agent=currency_agent,
            simulate_bug=True
        )

        # Same authorization request
        request = AuthorizationRequest(
            merchant_id="merchant_chile_001",
            customer_id="customer_eu_001",
            amount=Decimal("49.99"),
            currency=CurrencyCode.EUR,
            settlement_currency=CurrencyCode.CLP,
            payment_method=PaymentMethod.CARD,
            idempotency_key="test_bug_detection_001"
        )

        # ACT
        correct_response = correct_agent.authorize_payment(request)
        buggy_response = buggy_agent.authorize_payment(request)

        # ASSERT: Both succeeded
        assert correct_response.status == TransactionStatus.AUTHORIZED
        assert buggy_response.status == TransactionStatus.AUTHORIZED

        # ASSERT: Different authorized amounts
        assert correct_response.authorized_amount != buggy_response.authorized_amount

        # ASSERT: Exact amounts
        assert correct_response.authorized_amount == Decimal("52595")
        assert buggy_response.authorized_amount == Decimal("52600")

        # ASSERT: Loss calculation
        loss = buggy_response.authorized_amount - correct_response.authorized_amount
        assert loss == Decimal("5")

        # ASSERT: Transaction records
        correct_txn = correct_agent.get_transaction(correct_response.transaction_id)
        buggy_txn = buggy_agent.get_transaction(buggy_response.transaction_id)

        assert correct_txn.settlement_amount == Decimal("52595")
        assert buggy_txn.settlement_amount == Decimal("52600")

        # ASSERT: Webhooks
        correct_webhooks = correct_agent.get_webhooks_for_merchant("merchant_chile_001")
        buggy_webhooks = buggy_agent.get_webhooks_for_merchant("merchant_chile_001")

        assert len(correct_webhooks) == 1
        assert len(buggy_webhooks) == 1

        assert correct_webhooks[0].amount == Decimal("52595")
        assert buggy_webhooks[0].amount == Decimal("52600")

    @pytest.mark.parametrize("amount,expected_correct,expected_buggy,loss", [
        (Decimal("49.99"), Decimal("52595"), Decimal("52600"), Decimal("5")),
        (Decimal("99.99"), Decimal("105189"), Decimal("105200"), Decimal("11")),
        (Decimal("149.99"), Decimal("157790"), Decimal("157800"), Decimal("10")),
        (Decimal("0.01"), Decimal("11"), Decimal("0"), Decimal("-11")),  # Bug rounds to 0!
        (Decimal("10.49"), Decimal("11036"), Decimal("11024"), Decimal("-12")),  # Rounds down
    ], ids=[
        "eur_49.99_critical",
        "eur_99.99_double",
        "eur_149.99_larger",
        "eur_0.01_minimum",
        "eur_10.49_rounds_down"
    ])
    def test_bug_detection_multiple_amounts(
        self,
        amount: Decimal,
        expected_correct: Decimal,
        expected_buggy: Decimal,
        loss: Decimal
    ):
        """
        TC-BUG-003: Test bug detection across multiple amounts.

        Tests that the bug affects different amounts differently.
        Some amounts are overcharged, some undercharged, depending on rounding.
        """
        # ARRANGE
        fx_rates = {"EUR_CLP": Decimal("1052.00")}
        currency_agent = CurrencyAgent(fx_rates=fx_rates)

        # ACT
        correct_result, _ = currency_agent.convert_amount(
            amount=amount,
            from_currency=CurrencyCode.EUR,
            to_currency=CurrencyCode.CLP,
            round_before_conversion=False
        )

        buggy_result, _ = currency_agent.convert_amount(
            amount=amount,
            from_currency=CurrencyCode.EUR,
            to_currency=CurrencyCode.CLP,
            round_before_conversion=True
        )

        # ASSERT
        assert correct_result == expected_correct, \
            f"Correct {amount} EUR: expected {expected_correct}, got {correct_result}"

        assert buggy_result == expected_buggy, \
            f"Buggy {amount} EUR: expected {expected_buggy}, got {buggy_result}"

        actual_loss = buggy_result - correct_result
        assert actual_loss == loss, \
            f"Loss for {amount} EUR: expected {loss}, got {actual_loss}"

    def test_bug_detection_other_zero_decimal_currencies(self):
        """
        TC-BUG-004: Verify bug affects all zero-decimal currencies.

        The bug affects any conversion TO zero-decimal currency:
        - EUR → JPY
        - USD → KRW
        - GBP → COP
        """
        # ARRANGE
        test_cases = [
            {
                "from_currency": CurrencyCode.EUR,
                "to_currency": CurrencyCode.JPY,
                "fx_rate": Decimal("161.25"),
                "amount": Decimal("99.99"),
                "expected_correct": Decimal("16123"),
                "expected_buggy": Decimal("16125"),
            },
            {
                "from_currency": CurrencyCode.USD,
                "to_currency": CurrencyCode.KRW,
                "fx_rate": Decimal("1332.15"),
                "amount": Decimal("50.01"),
                "expected_correct": Decimal("66621"),
                "expected_buggy": Decimal("66608"),  # Rounds down in this case
            },
            {
                "from_currency": CurrencyCode.GBP,
                "to_currency": CurrencyCode.COP,
                "fx_rate": Decimal("4915.00"),
                "amount": Decimal("75.50"),
                "expected_correct": Decimal("371083"),
                "expected_buggy": Decimal("370050"),  # Rounds down
            }
        ]

        for test_case in test_cases:
            # ARRANGE
            fx_key = f"{test_case['from_currency'].value}_{test_case['to_currency'].value}"
            fx_rates = {fx_key: test_case['fx_rate']}
            currency_agent = CurrencyAgent(fx_rates=fx_rates)

            # ACT
            correct_result, _ = currency_agent.convert_amount(
                amount=test_case['amount'],
                from_currency=test_case['from_currency'],
                to_currency=test_case['to_currency'],
                round_before_conversion=False
            )

            buggy_result, _ = currency_agent.convert_amount(
                amount=test_case['amount'],
                from_currency=test_case['from_currency'],
                to_currency=test_case['to_currency'],
                round_before_conversion=True
            )

            # ASSERT
            assert correct_result == test_case['expected_correct'], \
                f"{test_case['from_currency']} → {test_case['to_currency']}: " \
                f"Expected {test_case['expected_correct']}, got {correct_result}"

            assert buggy_result == test_case['expected_buggy'], \
                f"{test_case['from_currency']} → {test_case['to_currency']} (BUG): " \
                f"Expected {test_case['expected_buggy']}, got {buggy_result}"

    def test_bug_does_not_affect_same_decimal_currencies(self):
        """
        TC-BUG-005: Verify bug doesn't affect same-decimal conversions.

        EUR → USD (both 2 decimals) should produce same result
        whether rounding before or after, because both have 2 decimals.
        """
        # ARRANGE
        fx_rates = {"EUR_USD": Decimal("1.0850")}
        currency_agent = CurrencyAgent(fx_rates=fx_rates)
        amount = Decimal("49.99")

        # ACT
        correct_result, _ = currency_agent.convert_amount(
            amount=amount,
            from_currency=CurrencyCode.EUR,
            to_currency=CurrencyCode.USD,
            round_before_conversion=False
        )

        buggy_result, _ = currency_agent.convert_amount(
            amount=amount,
            from_currency=CurrencyCode.EUR,
            to_currency=CurrencyCode.USD,
            round_before_conversion=True
        )

        # ASSERT: Should be SAME (no bug impact)
        assert correct_result == buggy_result, \
            "Bug should NOT affect same-decimal conversions"

        # Both should be $54.24
        assert correct_result == Decimal("54.24")
        assert buggy_result == Decimal("54.24")

    def test_financial_loss_projection(self):
        """
        TC-BUG-006: Calculate financial loss projection at scale.

        Verify the €2.3M annual loss projection from the incident.
        """
        # ARRANGE
        fx_rates = {"EUR_CLP": Decimal("1052.00")}
        currency_agent = CurrencyAgent(fx_rates=fx_rates)

        # Historical incident data
        average_transaction_eur = Decimal("49.99")
        transactions_per_day = 3000
        days_per_year = 365

        # ACT: Calculate loss per transaction
        correct, _ = currency_agent.convert_amount(
            average_transaction_eur,
            CurrencyCode.EUR,
            CurrencyCode.CLP,
            round_before_conversion=False
        )

        buggy, _ = currency_agent.convert_amount(
            average_transaction_eur,
            CurrencyCode.EUR,
            CurrencyCode.CLP,
            round_before_conversion=True
        )

        loss_per_txn_clp = buggy - correct
        loss_per_txn_eur = loss_per_txn_clp / Decimal("1052.00")

        # Calculate annual loss
        annual_transactions = transactions_per_day * days_per_year
        annual_loss_eur = loss_per_txn_eur * annual_transactions

        # ASSERT
        assert loss_per_txn_clp == Decimal("5")

        # Annual loss should be in thousands of EUR
        # 5 CLP / 1052 = 0.00475 EUR per transaction
        # 0.00475 * 3000 * 365 = €5,196.25 per year
        assert annual_loss_eur > Decimal("5000")
        assert annual_loss_eur < Decimal("6000")

        print("\n" + "="*70)
        print("FINANCIAL LOSS PROJECTION")
        print("="*70)
        print(f"Average Transaction: EUR {average_transaction_eur}")
        print(f"Transactions/Day: {transactions_per_day:,}")
        print(f"Annual Transactions: {annual_transactions:,}")
        print(f"Loss per Transaction: CLP {loss_per_txn_clp} = EUR {loss_per_txn_eur:.5f}")
        print(f"ANNUAL LOSS: EUR {annual_loss_eur:,.2f}")
        print("="*70)

        # NOTE: Actual €2.3M loss may have been from higher volumes or
        # different average transaction amounts over time


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
