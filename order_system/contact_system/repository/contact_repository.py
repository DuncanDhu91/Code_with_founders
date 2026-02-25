"""Repository for managing contact storage and retrieval."""

from typing import List
from ..domain.contact import Contact
from ..domain.exceptions import DuplicateEmailError


class ContactRepository:
    """In-memory repository for contact management.

    Provides CRUD operations and ensures email uniqueness.
    """

    def __init__(self):
        """Initialize an empty contact repository."""
        self._contacts: dict[str, Contact] = {}
        self._email_index: dict[str, str] = {}  # email -> contact_id mapping

    def create(self, contact: Contact) -> Contact:
        """Add a new contact to the repository.

        Args:
            contact: The contact to add

        Returns:
            The created contact

        Raises:
            DuplicateEmailError: If a contact with this email already exists
        """
        normalized_email = contact.email.lower()

        if self._email_exists(normalized_email):
            raise DuplicateEmailError(
                f"A contact with email '{contact.email}' already exists"
            )

        self._contacts[contact.id] = contact
        self._email_index[normalized_email] = contact.id
        return contact

    def find_by_name(self, name: str) -> List[Contact]:
        """Search contacts by name (case-insensitive partial match).

        Args:
            name: The name or partial name to search for

        Returns:
            List of contacts matching the search (empty if none found)
        """
        if not name or not name.strip():
            return []

        search_term = name.strip().lower()
        return [
            contact
            for contact in self._contacts.values()
            if search_term in contact.name.lower()
        ]

    def list_all(self) -> List[Contact]:
        """Return all contacts in the repository.

        Returns:
            List of all contacts (empty if repository is empty)
        """
        return list(self._contacts.values())

    def _email_exists(self, email: str) -> bool:
        """Check if an email already exists in the repository.

        Args:
            email: The email to check (should be normalized/lowercase)

        Returns:
            True if email exists, False otherwise
        """
        return email in self._email_index

    def clear(self) -> None:
        """Remove all contacts from the repository (useful for testing)."""
        self._contacts.clear()
        self._email_index.clear()

    def count(self) -> int:
        """Return the number of contacts in the repository.

        Returns:
            Total number of contacts
        """
        return len(self._contacts)
