"""Domain layer - Business logic and entities."""

from .contact import Contact
from .exceptions import ValidationError, DuplicateEmailError

__all__ = ["Contact", "ValidationError", "DuplicateEmailError"]
