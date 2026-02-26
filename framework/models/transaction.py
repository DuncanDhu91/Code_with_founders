"""Transaction models for payment testing."""

from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
from framework.models.currency import CurrencyCode


class TransactionStatus(str, Enum):
    """Transaction status values."""
    PENDING = "PENDING"
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    DECLINED = "DECLINED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PaymentMethod(str, Enum):
    """Payment method types."""
    CARD = "CARD"
    BANK_TRANSFER = "BANK_TRANSFER"
    DIGITAL_WALLET = "DIGITAL_WALLET"


class Transaction(BaseModel):
    """Payment transaction model."""
    transaction_id: str
    merchant_id: str
    customer_id: str

    # Amount details
    original_amount: Decimal
    original_currency: CurrencyCode
    settlement_amount: Optional[Decimal] = None
    settlement_currency: Optional[CurrencyCode] = None
    authorized_amount: Optional[Decimal] = None

    # FX details
    fx_rate: Optional[Decimal] = None
    fx_rate_timestamp: Optional[datetime] = None

    # Status
    status: TransactionStatus
    payment_method: PaymentMethod

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True

    @validator('original_amount', 'settlement_amount', 'authorized_amount', 'fx_rate', pre=True)
    def convert_to_decimal(cls, v):
        """Convert amounts to Decimal for precision."""
        if v is None:
            return v
        if isinstance(v, (int, float, str)):
            return Decimal(str(v))
        return v


class AuthorizationRequest(BaseModel):
    """Payment authorization request."""
    merchant_id: str
    customer_id: str
    amount: Decimal
    currency: CurrencyCode
    settlement_currency: Optional[CurrencyCode] = None
    payment_method: PaymentMethod
    idempotency_key: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator('amount', pre=True)
    def convert_to_decimal(cls, v):
        """Convert amount to Decimal."""
        if isinstance(v, (int, float, str)):
            return Decimal(str(v))
        return v


class AuthorizationResponse(BaseModel):
    """Payment authorization response."""
    transaction_id: str
    status: TransactionStatus
    authorized_amount: Decimal
    authorized_currency: CurrencyCode
    settlement_amount: Optional[Decimal] = None
    settlement_currency: Optional[CurrencyCode] = None
    fx_rate: Optional[Decimal] = None
    message: Optional[str] = None
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @validator('authorized_amount', 'settlement_amount', 'fx_rate', pre=True)
    def convert_to_decimal(cls, v):
        """Convert amounts to Decimal."""
        if v is None:
            return v
        if isinstance(v, (int, float, str)):
            return Decimal(str(v))
        return v


class WebhookPayload(BaseModel):
    """Webhook event payload."""
    event_type: str
    transaction_id: str
    status: TransactionStatus
    amount: Decimal
    currency: CurrencyCode
    settlement_amount: Optional[Decimal] = None
    settlement_currency: Optional[CurrencyCode] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator('amount', 'settlement_amount', pre=True)
    def convert_to_decimal(cls, v):
        """Convert amounts to Decimal."""
        if v is None:
            return v
        if isinstance(v, (int, float, str)):
            return Decimal(str(v))
        return v
