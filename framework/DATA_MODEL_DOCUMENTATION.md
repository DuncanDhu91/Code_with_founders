# Data Model Documentation: Silent Currency Bug Prevention

## Executive Summary

This document defines the data architecture foundation for preventing currency conversion bugs that could result in significant financial losses. It establishes precise requirements for currency amount storage, exchange rate handling, and transaction records with database-level constraints that enforce correct rounding behavior.

**Core Principle**: Precision loss prevention through correct decimal types, rounding order enforcement, and currency-aware validation constraints.

---

## 1. Currency Amount Storage Schema

### 1.1 Precision and Scale Requirements

Currency amounts must be stored with sufficient precision to prevent loss during conversion and rounding operations.

#### Database Column Specifications

```sql
-- PostgreSQL/MySQL DECIMAL type specifications
CREATE TABLE transactions (
    transaction_id UUID PRIMARY KEY,

    -- Original amounts (customer-facing)
    original_amount DECIMAL(19, 4) NOT NULL,  -- Up to 999,999,999,999,999.9999
    original_currency CHAR(3) NOT NULL,

    -- Converted amounts (settlement)
    settlement_amount DECIMAL(19, 4),          -- Same precision for conversions
    settlement_currency CHAR(3),

    -- Authorized amount (final rounded value)
    authorized_amount DECIMAL(19, 4) NOT NULL,
    authorized_currency CHAR(3) NOT NULL,

    -- Exchange rate (must support high precision)
    fx_rate DECIMAL(19, 8),                    -- Up to 8 decimal places for extreme rates
    fx_rate_timestamp TIMESTAMP,

    -- Metadata
    merchant_id VARCHAR(64) NOT NULL,
    customer_id VARCHAR(64) NOT NULL,
    payment_method VARCHAR(32) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,

    -- Constraints (detailed in section 1.4)
    CONSTRAINT chk_original_amount_positive CHECK (original_amount > 0),
    CONSTRAINT chk_settlement_amount_positive CHECK (settlement_amount IS NULL OR settlement_amount > 0),
    CONSTRAINT chk_authorized_amount_positive CHECK (authorized_amount > 0),
    CONSTRAINT chk_fx_rate_positive CHECK (fx_rate IS NULL OR fx_rate > 0),
    CONSTRAINT chk_currencies_valid CHECK (
        original_currency ~ '^[A-Z]{3}$' AND
        (settlement_currency IS NULL OR settlement_currency ~ '^[A-Z]{3}$') AND
        authorized_currency ~ '^[A-Z]{3}$'
    )
);

-- Indexes for query performance
CREATE INDEX idx_transactions_merchant_created ON transactions(merchant_id, created_at DESC);
CREATE INDEX idx_transactions_customer_created ON transactions(customer_id, created_at DESC);
CREATE INDEX idx_transactions_status ON transactions(status);
CREATE INDEX idx_transactions_currencies ON transactions(original_currency, settlement_currency);
```

#### Rationale: DECIMAL(19, 4)

- **19 total digits**: Supports large transaction amounts (up to 15 digits before decimal)
- **4 decimal places**: Exceeds the maximum 3 decimal places used by any currency (KWD, BHD, OMR)
- **Prevents precision loss**: Intermediate calculations maintain precision before rounding to target currency
- **Storage efficient**: Balances precision needs with database storage and index efficiency

### 1.2 Currency Configuration Schema

Define metadata for each supported currency to enable validation and proper rounding.

```sql
CREATE TABLE currency_configs (
    currency_code CHAR(3) PRIMARY KEY,
    decimal_places SMALLINT NOT NULL,
    min_amount DECIMAL(19, 4) NOT NULL,
    max_amount DECIMAL(19, 4) NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    currency_name VARCHAR(50) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,

    -- Constraints
    CONSTRAINT chk_decimal_places_valid CHECK (decimal_places IN (0, 2, 3)),
    CONSTRAINT chk_min_max_valid CHECK (min_amount < max_amount),

    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- Seed data for critical currencies
INSERT INTO currency_configs (currency_code, decimal_places, min_amount, max_amount, symbol, currency_name) VALUES
    -- Zero-decimal currencies (CRITICAL for bug prevention)
    ('CLP', 0, 1, 999999999, 'CLP$', 'Chilean Peso'),
    ('COP', 0, 1, 999999999, 'COL$', 'Colombian Peso'),
    ('JPY', 0, 1, 9999999, '¥', 'Japanese Yen'),
    ('KRW', 0, 1, 999999999, '₩', 'Korean Won'),
    ('VND', 0, 1, 999999999, '₫', 'Vietnamese Dong'),
    ('IDR', 0, 1, 999999999, 'Rp', 'Indonesian Rupiah'),
    ('ISK', 0, 1, 999999999, 'kr', 'Icelandic Krona'),
    ('TWD', 0, 1, 999999999, 'NT$', 'Taiwan Dollar'),

    -- Two-decimal currencies (most common)
    ('EUR', 2, 0.01, 999999.99, '€', 'Euro'),
    ('USD', 2, 0.01, 999999.99, '$', 'US Dollar'),
    ('GBP', 2, 0.01, 999999.99, '£', 'British Pound'),
    ('BRL', 2, 0.01, 999999.99, 'R$', 'Brazilian Real'),
    ('MXN', 2, 0.01, 999999.99, 'MX$', 'Mexican Peso'),
    ('CAD', 2, 0.01, 999999.99, 'C$', 'Canadian Dollar'),
    ('AUD', 2, 0.01, 999999.99, 'A$', 'Australian Dollar'),
    ('CNY', 2, 0.01, 999999.99, '¥', 'Chinese Yuan'),
    ('INR', 2, 0.01, 999999.99, '₹', 'Indian Rupee'),
    ('SGD', 2, 0.01, 999999.99, 'S$', 'Singapore Dollar'),

    -- Three-decimal currencies (Middle East)
    ('KWD', 3, 0.001, 999999.999, 'KD', 'Kuwaiti Dinar'),
    ('BHD', 3, 0.001, 999999.999, 'BD', 'Bahraini Dinar'),
    ('OMR', 3, 0.001, 999999.999, 'OMR', 'Omani Rial'),
    ('JOD', 3, 0.001, 999999.999, 'JD', 'Jordanian Dinar'),
    ('TND', 3, 0.001, 999999.999, 'DT', 'Tunisian Dinar');
```

### 1.3 Exchange Rate Storage

Exchange rates require high precision (up to 8 decimal places) to handle extreme rates and minimize compounding errors.

```sql
CREATE TABLE exchange_rates (
    rate_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_currency CHAR(3) NOT NULL,
    to_currency CHAR(3) NOT NULL,
    rate DECIMAL(19, 8) NOT NULL,              -- 8 decimals for precision
    valid_from TIMESTAMP NOT NULL,
    valid_until TIMESTAMP,
    rate_source VARCHAR(50) NOT NULL,          -- e.g., 'ECB', 'OANDA', 'TEST_FIXTURE'
    is_active BOOLEAN NOT NULL DEFAULT true,

    -- Constraints
    CONSTRAINT chk_rate_positive CHECK (rate > 0),
    CONSTRAINT chk_different_currencies CHECK (from_currency != to_currency),
    CONSTRAINT chk_valid_date_range CHECK (valid_until IS NULL OR valid_until > valid_from),

    -- Prevent duplicate rates for same time period
    CONSTRAINT uq_rate_period UNIQUE (from_currency, to_currency, valid_from),

    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- Indexes for fast rate lookups
CREATE INDEX idx_rates_active_lookup ON exchange_rates(from_currency, to_currency, valid_from DESC)
    WHERE is_active = true;
CREATE INDEX idx_rates_validity ON exchange_rates(valid_from, valid_until);
```

#### Example Exchange Rates (Test Fixtures)

```sql
-- Critical rate from the incident: EUR -> CLP
INSERT INTO exchange_rates (from_currency, to_currency, rate, valid_from, rate_source) VALUES
    ('EUR', 'CLP', 1052.0000, '2024-01-01', 'TEST_FIXTURE'),
    ('EUR', 'CLP', 1052.1234, '2024-01-01', 'TEST_FIXTURE'),  -- >4 decimals (edge case)

    -- High precision rates (>4 decimals)
    ('EUR', 'JPY', 161.25345, '2024-01-01', 'TEST_FIXTURE'),
    ('EUR', 'COP', 4250.12345, '2024-01-01', 'TEST_FIXTURE'),
    ('USD', 'CLP', 969.5432, '2024-01-01', 'TEST_FIXTURE'),

    -- Reverse rates (small decimals)
    ('CLP', 'EUR', 0.00095057, '2024-01-01', 'TEST_FIXTURE'),
    ('JPY', 'EUR', 0.00620341, '2024-01-01', 'TEST_FIXTURE'),
    ('COP', 'EUR', 0.00023529, '2024-01-01', 'TEST_FIXTURE'),

    -- Standard two-decimal currency pairs
    ('EUR', 'USD', 1.08500000, '2024-01-01', 'TEST_FIXTURE'),
    ('GBP', 'USD', 1.25470000, '2024-01-01', 'TEST_FIXTURE'),
    ('EUR', 'GBP', 0.86500000, '2024-01-01', 'TEST_FIXTURE'),

    -- Three-decimal currencies
    ('EUR', 'KWD', 0.33450000, '2024-01-01', 'TEST_FIXTURE'),
    ('USD', 'BHD', 0.37700000, '2024-01-01', 'TEST_FIXTURE');
```

### 1.4 Database Constraints That Prevent the Rounding Bug

These constraints enforce correct data relationships and prevent the specific bug pattern.

```sql
-- 1. Ensure authorized amount respects target currency decimal places
CREATE OR REPLACE FUNCTION validate_authorized_amount_precision()
RETURNS TRIGGER AS $$
DECLARE
    target_decimals SMALLINT;
    amount_decimals SMALLINT;
BEGIN
    -- Get decimal places for authorized currency
    SELECT decimal_places INTO target_decimals
    FROM currency_configs
    WHERE currency_code = NEW.authorized_currency;

    -- Calculate decimal places in authorized amount
    amount_decimals := LENGTH(SPLIT_PART(NEW.authorized_amount::TEXT, '.', 2));

    -- Enforce constraint
    IF amount_decimals > target_decimals THEN
        RAISE EXCEPTION 'Authorized amount % has % decimal places, but % allows %',
            NEW.authorized_amount, amount_decimals, NEW.authorized_currency, target_decimals;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_authorized_amount
    BEFORE INSERT OR UPDATE ON transactions
    FOR EACH ROW
    EXECUTE FUNCTION validate_authorized_amount_precision();

-- 2. Ensure settlement amount (if present) has correct precision
CREATE OR REPLACE FUNCTION validate_settlement_amount_precision()
RETURNS TRIGGER AS $$
DECLARE
    target_decimals SMALLINT;
    amount_decimals SMALLINT;
BEGIN
    -- Only validate if settlement currency is present
    IF NEW.settlement_currency IS NOT NULL AND NEW.settlement_amount IS NOT NULL THEN
        SELECT decimal_places INTO target_decimals
        FROM currency_configs
        WHERE currency_code = NEW.settlement_currency;

        amount_decimals := LENGTH(SPLIT_PART(NEW.settlement_amount::TEXT, '.', 2));

        IF amount_decimals > target_decimals THEN
            RAISE EXCEPTION 'Settlement amount % has % decimal places, but % allows %',
                NEW.settlement_amount, amount_decimals, NEW.settlement_currency, target_decimals;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_settlement_amount
    BEFORE INSERT OR UPDATE ON transactions
    FOR EACH ROW
    EXECUTE FUNCTION validate_settlement_amount_precision();

-- 3. Validate currency conversion consistency
CREATE OR REPLACE FUNCTION validate_conversion_consistency()
RETURNS TRIGGER AS $$
BEGIN
    -- If currencies differ, settlement fields must be present
    IF NEW.original_currency != NEW.authorized_currency THEN
        IF NEW.fx_rate IS NULL THEN
            RAISE EXCEPTION 'FX rate required when original currency % differs from authorized currency %',
                NEW.original_currency, NEW.authorized_currency;
        END IF;

        IF NEW.settlement_amount IS NULL OR NEW.settlement_currency IS NULL THEN
            RAISE EXCEPTION 'Settlement amount and currency required for cross-currency transaction';
        END IF;

        -- Verify settlement_currency matches authorized_currency
        IF NEW.settlement_currency != NEW.authorized_currency THEN
            RAISE EXCEPTION 'Settlement currency % must match authorized currency %',
                NEW.settlement_currency, NEW.authorized_currency;
        END IF;
    END IF;

    -- If same currency, settlement fields should be NULL
    IF NEW.original_currency = NEW.authorized_currency THEN
        IF NEW.fx_rate IS NOT NULL OR NEW.settlement_amount IS NOT NULL OR NEW.settlement_currency IS NOT NULL THEN
            RAISE EXCEPTION 'Settlement fields must be NULL for same-currency transaction';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_conversion_consistency
    BEFORE INSERT OR UPDATE ON transactions
    FOR EACH ROW
    EXECUTE FUNCTION validate_conversion_consistency();

-- 4. Audit log for tracking amount changes (immutability)
CREATE TABLE transaction_audit_log (
    audit_id BIGSERIAL PRIMARY KEY,
    transaction_id UUID NOT NULL REFERENCES transactions(transaction_id),
    operation VARCHAR(10) NOT NULL,  -- INSERT, UPDATE, DELETE
    old_data JSONB,
    new_data JSONB,
    changed_by VARCHAR(100),
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_operation_valid CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE'))
);

CREATE OR REPLACE FUNCTION audit_transaction_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO transaction_audit_log (transaction_id, operation, new_data)
        VALUES (NEW.transaction_id, 'INSERT', row_to_json(NEW)::jsonb);
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO transaction_audit_log (transaction_id, operation, old_data, new_data)
        VALUES (NEW.transaction_id, 'UPDATE', row_to_json(OLD)::jsonb, row_to_json(NEW)::jsonb);
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO transaction_audit_log (transaction_id, operation, old_data)
        VALUES (OLD.transaction_id, 'DELETE', row_to_json(OLD)::jsonb);
        RETURN OLD;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_transactions
    AFTER INSERT OR UPDATE OR DELETE ON transactions
    FOR EACH ROW
    EXECUTE FUNCTION audit_transaction_changes();
```

---

## 2. Application-Level Data Models

### 2.1 Python Data Classes (Pydantic)

Reference implementation already exists in `/framework/models/`:
- `/framework/models/currency.py` - Currency configurations
- `/framework/models/transaction.py` - Transaction models

Key validations in application code:
1. All amounts converted to `Decimal` type (never `float`)
2. Decimal places validated against currency configuration
3. Min/max amount enforcement
4. FX rate availability checks

### 2.2 Rounding Order Enforcement

The critical logic to prevent the bug:

```python
def convert_amount_correctly(
    amount: Decimal,
    from_currency: CurrencyCode,
    to_currency: CurrencyCode,
    fx_rate: Decimal
) -> Decimal:
    """
    CORRECT: Convert THEN round to target currency.

    Example:
        €49.99 -> CLP at rate 1052
        49.99 * 1052 = 52,594.48
        round(52,594.48) = 52,594 CLP ✓
    """
    # Step 1: Convert using high-precision arithmetic
    converted = amount * fx_rate

    # Step 2: Round to target currency's decimal places
    to_config = get_currency(to_currency)
    final_amount = to_config.round_amount(converted)

    return final_amount


def convert_amount_incorrectly(
    amount: Decimal,
    from_currency: CurrencyCode,
    to_currency: CurrencyCode,
    fx_rate: Decimal
) -> Decimal:
    """
    BUG: Round source amount BEFORE conversion.

    Example:
        €49.99 -> CLP at rate 1052
        round(49.99) = 49.00  (prematurely rounded to whole number)
        49.00 * 1052 = 51,548 CLP ✗ (WRONG by 1,046 CLP)
    """
    # BUG: Rounding source amount first
    from_config = get_currency(from_currency)
    rounded_source = from_config.round_amount(amount)

    # Convert already-rounded amount
    converted = rounded_source * fx_rate

    # Round again (redundant)
    to_config = get_currency(to_currency)
    final_amount = to_config.round_amount(converted)

    return final_amount
```

---

## 3. Key Data Architecture Questions Answered

### Q1: How should currency amounts be stored to prevent precision loss?

**Answer**: Use `DECIMAL(19, 4)` for all amount fields:
- **19 digits total**: Supports large amounts without overflow
- **4 decimal places**: Exceeds maximum currency precision (3 decimals)
- **Never use FLOAT or DOUBLE**: These binary types cause precision loss in decimal arithmetic
- **Use DECIMAL(19, 8) for FX rates**: Higher precision prevents compounding errors in conversions

### Q2: What database constraints prevent incorrect rounding order?

**Answer**: Multi-layered enforcement:
1. **Trigger validation**: `validate_authorized_amount_precision()` ensures authorized amounts match currency decimal rules
2. **Consistency checks**: `validate_conversion_consistency()` enforces FX rate presence when currencies differ
3. **Audit trail**: Immutable log tracks all amount changes for forensic analysis
4. **Application-level**: Currency agent enforces correct conversion order (convert THEN round)

### Q3: How do we model exchange rates to support deterministic testing?

**Answer**:
- Store rates with `DECIMAL(19, 8)` precision
- Include validity time range (`valid_from`, `valid_until`)
- Tag rate source (`TEST_FIXTURE` vs `ECB` vs `OANDA`)
- Support multiple simultaneous rates for A/B testing
- Enable rate staleness detection via timestamps

### Q4: What data validations catch zero-decimal currency violations?

**Answer**:
1. **Database trigger**: Rejects any amount with decimals for zero-decimal currencies
2. **Currency config**: `decimal_places=0` enforced in `currency_configs` table
3. **Application validator**: `validate_amount_for_currency()` checks decimal places
4. **Rounding method**: `round_amount()` truncates/rounds to integer for zero-decimal currencies

### Q5: How do we generate test data that covers all currency pair combinations efficiently?

**Answer**: See TEST_DATA_STRATEGY.md (next deliverable) for comprehensive approach.

---

## 4. Schema Migration Strategy

### Initial Migration (V1)

```sql
-- migrations/001_initial_schema.sql
BEGIN;

CREATE TABLE currency_configs (...);  -- As defined above
CREATE TABLE exchange_rates (...);
CREATE TABLE transactions (...);
CREATE TABLE transaction_audit_log (...);

-- Create triggers
CREATE TRIGGER trg_validate_authorized_amount ...;
CREATE TRIGGER trg_validate_settlement_amount ...;
CREATE TRIGGER trg_validate_conversion_consistency ...;
CREATE TRIGGER trg_audit_transactions ...;

-- Seed currency configurations
INSERT INTO currency_configs VALUES (...);

-- Seed test exchange rates
INSERT INTO exchange_rates VALUES (...);

COMMIT;
```

### Future Migrations

- **V2**: Add support for new currencies (just insert into `currency_configs`)
- **V3**: Add rate history table for analytics
- **V4**: Add merchant-specific currency preferences
- **V5**: Add settlement reconciliation table

---

## 5. Data Integrity Checklist

Before deploying to production, verify:

- [ ] All amount columns use DECIMAL type (no FLOAT/DOUBLE)
- [ ] DECIMAL precision is DECIMAL(19, 4) for amounts
- [ ] DECIMAL precision is DECIMAL(19, 8) for FX rates
- [ ] Database triggers validate currency decimal places
- [ ] Audit log captures all transaction changes
- [ ] Currency configs table seeded with all supported currencies
- [ ] Exchange rate table has test fixtures for all critical pairs
- [ ] Foreign key constraints enforce referential integrity
- [ ] Indexes exist on frequently queried columns
- [ ] Application code uses Decimal type (not float) for all arithmetic

---

## 6. Incident Prevention Mapping

| Bug Characteristic | Prevention Mechanism | Location |
|-------------------|---------------------|----------|
| Rounded BEFORE conversion | Application logic enforces correct order | `currency_agent.py:convert_amount()` |
| Zero-decimal currency (CLP, COP) | Database trigger validates decimal places | `validate_authorized_amount_precision()` |
| Exchange rate >4 decimals | DECIMAL(19,8) storage prevents truncation | `exchange_rates.rate` column |
| Amount mismatch between display & auth | Audit log tracks all amount changes | `transaction_audit_log` table |
| Missing FX rate for cross-currency | Constraint enforces FX rate presence | `validate_conversion_consistency()` |
| Precision loss in arithmetic | DECIMAL type prevents binary float errors | All amount/rate columns |

---

## Appendix A: Currency Decimal Place Reference

| Decimal Places | Count | Currencies |
|---------------|-------|-----------|
| 0 (Zero-decimal) | 8 | CLP, COP, JPY, KRW, VND, IDR, ISK, TWD |
| 2 (Standard) | ~150 | EUR, USD, GBP, BRL, MXN, CAD, AUD, CNY, INR, SGD, etc. |
| 3 (Three-decimal) | 5 | KWD, BHD, OMR, JOD, TND |

## Appendix B: Storage Size Analysis

| Data Type | Storage Size | Precision | Use Case |
|-----------|-------------|-----------|----------|
| DECIMAL(19,4) | 11 bytes | 19 total digits, 4 after decimal | Currency amounts |
| DECIMAL(19,8) | 11 bytes | 19 total digits, 8 after decimal | FX rates |
| FLOAT(24) | 4 bytes | ~7 decimal digits | ❌ NEVER USE for money |
| DOUBLE(53) | 8 bytes | ~15 decimal digits | ❌ NEVER USE for money |

**Rationale**: The 3-7 byte overhead of DECIMAL over FLOAT is negligible compared to the risk of precision loss causing financial errors.

---

**Document Version**: 1.0
**Last Updated**: 2026-02-25
**Owner**: Data Architect (Principal)
**Review Cycle**: Quarterly or after any currency-related incident
