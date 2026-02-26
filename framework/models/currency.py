"""Currency models and enums for test framework."""

from enum import Enum
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, validator


class CurrencyCode(str, Enum):
    """Supported currency codes."""
    # Two-decimal currencies (most common)
    EUR = "EUR"
    USD = "USD"
    GBP = "GBP"
    BRL = "BRL"
    MXN = "MXN"
    COP = "COP"
    PEN = "PEN"
    ARS = "ARS"

    # Zero-decimal currencies (critical for the bug)
    CLP = "CLP"  # Chilean Peso
    JPY = "JPY"  # Japanese Yen
    KRW = "KRW"  # Korean Won

    # Three-decimal currencies (Middle East)
    KWD = "KWD"  # Kuwaiti Dinar
    BHD = "BHD"  # Bahraini Dinar
    OMR = "OMR"  # Omani Rial
    JOD = "JOD"  # Jordanian Dinar
    TND = "TND"  # Tunisian Dinar


class DecimalPlaces(int, Enum):
    """Number of decimal places for each currency type."""
    ZERO = 0
    TWO = 2
    THREE = 3


class Currency(BaseModel):
    """Currency configuration model."""
    code: CurrencyCode
    decimal_places: int = Field(..., ge=0, le=3)
    min_amount: Decimal
    max_amount: Decimal
    symbol: str
    name: str

    class Config:
        use_enum_values = True

    @validator('min_amount', 'max_amount', pre=True)
    def convert_to_decimal(cls, v):
        """Convert amounts to Decimal for precision."""
        if isinstance(v, (int, float, str)):
            return Decimal(str(v))
        return v

    def format_amount(self, amount: Decimal) -> str:
        """Format amount according to currency rules."""
        if self.decimal_places == 0:
            return f"{self.symbol}{int(amount)}"
        return f"{self.symbol}{amount:.{self.decimal_places}f}"

    def round_amount(self, amount: Decimal) -> Decimal:
        """Round amount to currency's decimal places."""
        if self.decimal_places == 0:
            return Decimal(int(amount))
        quantizer = Decimal(10) ** -self.decimal_places
        return amount.quantize(quantizer)


# Currency configurations
CURRENCY_CONFIGS = {
    # Two-decimal currencies
    CurrencyCode.EUR: Currency(
        code=CurrencyCode.EUR,
        decimal_places=2,
        min_amount=Decimal("0.01"),
        max_amount=Decimal("999999.99"),
        symbol="€",
        name="Euro"
    ),
    CurrencyCode.USD: Currency(
        code=CurrencyCode.USD,
        decimal_places=2,
        min_amount=Decimal("0.01"),
        max_amount=Decimal("999999.99"),
        symbol="$",
        name="US Dollar"
    ),
    CurrencyCode.GBP: Currency(
        code=CurrencyCode.GBP,
        decimal_places=2,
        min_amount=Decimal("0.01"),
        max_amount=Decimal("999999.99"),
        symbol="£",
        name="British Pound"
    ),
    CurrencyCode.BRL: Currency(
        code=CurrencyCode.BRL,
        decimal_places=2,
        min_amount=Decimal("0.01"),
        max_amount=Decimal("999999.99"),
        symbol="R$",
        name="Brazilian Real"
    ),
    CurrencyCode.MXN: Currency(
        code=CurrencyCode.MXN,
        decimal_places=2,
        min_amount=Decimal("0.01"),
        max_amount=Decimal("999999.99"),
        symbol="MX$",
        name="Mexican Peso"
    ),

    # Zero-decimal currencies (THE CRITICAL ONES)
    CurrencyCode.CLP: Currency(
        code=CurrencyCode.CLP,
        decimal_places=0,
        min_amount=Decimal("1"),
        max_amount=Decimal("999999999"),
        symbol="CLP$",
        name="Chilean Peso"
    ),
    CurrencyCode.JPY: Currency(
        code=CurrencyCode.JPY,
        decimal_places=0,
        min_amount=Decimal("1"),
        max_amount=Decimal("9999999"),
        symbol="¥",
        name="Japanese Yen"
    ),
    CurrencyCode.KRW: Currency(
        code=CurrencyCode.KRW,
        decimal_places=0,
        min_amount=Decimal("1"),
        max_amount=Decimal("999999999"),
        symbol="₩",
        name="Korean Won"
    ),
    CurrencyCode.COP: Currency(
        code=CurrencyCode.COP,
        decimal_places=0,
        min_amount=Decimal("1"),
        max_amount=Decimal("999999999"),
        symbol="COL$",
        name="Colombian Peso"
    ),

    # Three-decimal currencies
    CurrencyCode.KWD: Currency(
        code=CurrencyCode.KWD,
        decimal_places=3,
        min_amount=Decimal("0.001"),
        max_amount=Decimal("999999.999"),
        symbol="KD",
        name="Kuwaiti Dinar"
    ),
    CurrencyCode.BHD: Currency(
        code=CurrencyCode.BHD,
        decimal_places=3,
        min_amount=Decimal("0.001"),
        max_amount=Decimal("999999.999"),
        symbol="BD",
        name="Bahraini Dinar"
    ),
    CurrencyCode.OMR: Currency(
        code=CurrencyCode.OMR,
        decimal_places=3,
        min_amount=Decimal("0.001"),
        max_amount=Decimal("999999.999"),
        symbol="OMR",
        name="Omani Rial"
    ),
}


def get_currency(code: CurrencyCode) -> Currency:
    """Get currency configuration by code."""
    return CURRENCY_CONFIGS[code]
