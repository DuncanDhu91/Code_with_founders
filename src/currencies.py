"""Currency metadata registry for multi-currency checkout system."""

CURRENCIES = {
    "USD": {
        "code": "USD",
        "name": "US Dollar",
        "symbol": "$",
        "decimal_places": 2,
    },
    "EUR": {
        "code": "EUR",
        "name": "Euro",
        "symbol": "€",
        "decimal_places": 2,
    },
    "GBP": {
        "code": "GBP",
        "name": "British Pound",
        "symbol": "£",
        "decimal_places": 2,
    },
    "JPY": {
        "code": "JPY",
        "name": "Japanese Yen",
        "symbol": "¥",
        "decimal_places": 0,
    },
    "MXN": {
        "code": "MXN",
        "name": "Mexican Peso",
        "symbol": "MX$",
        "decimal_places": 2,
    },
    "BRL": {
        "code": "BRL",
        "name": "Brazilian Real",
        "symbol": "R$",
        "decimal_places": 2,
    },
}


def get_currency(code):
    """
    Get currency metadata by code.

    Args:
        code: ISO currency code (e.g., 'USD', 'EUR')

    Returns:
        dict: Currency metadata

    Raises:
        InvalidCurrencyError: If currency code is not supported
    """
    from src.exceptions import InvalidCurrencyError

    if code not in CURRENCIES:
        raise InvalidCurrencyError(f"Currency '{code}' is not supported")

    return CURRENCIES[code]


def get_decimal_places(code):
    """
    Get decimal places for a currency.

    Args:
        code: ISO currency code

    Returns:
        int: Number of decimal places

    Raises:
        InvalidCurrencyError: If currency code is not supported
    """
    currency = get_currency(code)
    return currency["decimal_places"]


def is_supported_currency(code):
    """
    Check if a currency code is supported.

    Args:
        code: ISO currency code

    Returns:
        bool: True if currency is supported
    """
    return code in CURRENCIES
