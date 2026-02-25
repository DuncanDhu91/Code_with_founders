"""Custom exceptions for currency conversion system."""


class InvalidCurrencyError(ValueError):
    """Raised when an unsupported currency code is provided."""
    pass


class InvalidAmountError(ValueError):
    """Raised when an invalid amount is provided (e.g., negative, zero)."""
    pass


class ConversionError(Exception):
    """Raised when a currency conversion fails."""
    pass
