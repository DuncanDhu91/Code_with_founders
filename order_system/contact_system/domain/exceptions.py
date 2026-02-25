"""Custom exceptions for the contact management system."""


class ValidationError(Exception):
    """Raised when a validation rule is violated."""
    pass


class DuplicateEmailError(ValidationError):
    """Raised when attempting to create a contact with an existing email."""
    pass
