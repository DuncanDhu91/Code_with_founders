"""Contact entity with built-in validation."""

from typing import Optional
from uuid import uuid4
from .exceptions import ValidationError


class Contact:
    """Represents a contact with name, email, and phone.

    All fields are validated during creation. Email must contain @,
    phone and name cannot be empty.
    """

    def __init__(self, name: str, email: str, phone: str, contact_id: Optional[str] = None):
        """Create a new contact with validation.

        Args:
            name: Contact's name (required, non-empty)
            email: Contact's email (required, must contain @)
            phone: Contact's phone number (required, non-empty)
            contact_id: Optional unique identifier (auto-generated if not provided)

        Raises:
            ValidationError: If any validation rule is violated
        """
        self._validate_name(name)
        self._validate_email(email)
        self._validate_phone(phone)

        self.id = contact_id or str(uuid4())
        self.name = name.strip()
        self.email = email.strip().lower()
        self.phone = phone.strip()

    @staticmethod
    def _validate_name(name: str) -> None:
        """Validate that name is not empty."""
        if not name or not name.strip():
            raise ValidationError("Name cannot be empty")

    @staticmethod
    def _validate_email(email: str) -> None:
        """Validate that email contains @ symbol."""
        if not email or not email.strip():
            raise ValidationError("Email cannot be empty")
        if "@" not in email:
            raise ValidationError("Email must contain @ symbol")

    @staticmethod
    def _validate_phone(phone: str) -> None:
        """Validate that phone is not empty."""
        if not phone or not phone.strip():
            raise ValidationError("Phone cannot be empty")

    def __repr__(self) -> str:
        """Return string representation of contact."""
        return f"Contact(id={self.id}, name={self.name}, email={self.email}, phone={self.phone})"

    def __eq__(self, other) -> bool:
        """Compare contacts by ID."""
        if not isinstance(other, Contact):
            return False
        return self.id == other.id
