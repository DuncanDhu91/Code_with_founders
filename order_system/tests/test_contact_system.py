"""Comprehensive test suite for Contact Management System."""

import pytest
from contact_system.domain import Contact, ValidationError, DuplicateEmailError
from contact_system.repository import ContactRepository


class TestContactValidation:
    """Test contact validation rules."""

    def test_create_valid_contact(self):
        """Should create a contact with valid data."""
        contact = Contact(
            name="Juan Pérez",
            email="juan@example.com",
            phone="+1234567890"
        )
        assert contact.name == "Juan Pérez"
        assert contact.email == "juan@example.com"
        assert contact.phone == "+1234567890"
        assert contact.id is not None

    def test_email_must_contain_at_symbol(self):
        """Should raise ValidationError if email doesn't contain @."""
        with pytest.raises(ValidationError, match="must contain @ symbol"):
            Contact(name="Juan", email="invalid-email", phone="123")

    def test_email_cannot_be_empty(self):
        """Should raise ValidationError if email is empty."""
        with pytest.raises(ValidationError, match="Email cannot be empty"):
            Contact(name="Juan", email="", phone="123")

    def test_email_cannot_be_whitespace(self):
        """Should raise ValidationError if email is only whitespace."""
        with pytest.raises(ValidationError, match="Email cannot be empty"):
            Contact(name="Juan", email="   ", phone="123")

    def test_phone_cannot_be_empty(self):
        """Should raise ValidationError if phone is empty."""
        with pytest.raises(ValidationError, match="Phone cannot be empty"):
            Contact(name="Juan", email="juan@test.com", phone="")

    def test_phone_cannot_be_whitespace(self):
        """Should raise ValidationError if phone is only whitespace."""
        with pytest.raises(ValidationError, match="Phone cannot be empty"):
            Contact(name="Juan", email="juan@test.com", phone="   ")

    def test_name_cannot_be_empty(self):
        """Should raise ValidationError if name is empty."""
        with pytest.raises(ValidationError, match="Name cannot be empty"):
            Contact(name="", email="juan@test.com", phone="123")

    def test_name_cannot_be_whitespace(self):
        """Should raise ValidationError if name is only whitespace."""
        with pytest.raises(ValidationError, match="Name cannot be empty"):
            Contact(name="   ", email="juan@test.com", phone="123")

    def test_contact_trims_whitespace(self):
        """Should trim leading/trailing whitespace from fields."""
        contact = Contact(
            name="  Juan  ",
            email="  juan@test.com  ",
            phone="  123  "
        )
        assert contact.name == "Juan"
        assert contact.email == "juan@test.com"
        assert contact.phone == "123"

    def test_email_is_normalized_to_lowercase(self):
        """Should convert email to lowercase for consistency."""
        contact = Contact(
            name="Juan",
            email="Juan@Example.COM",
            phone="123"
        )
        assert contact.email == "juan@example.com"


class TestContactRepository:
    """Test contact repository operations."""

    @pytest.fixture
    def repository(self):
        """Provide a fresh repository for each test."""
        return ContactRepository()

    @pytest.fixture
    def sample_contact(self):
        """Provide a sample contact for testing."""
        return Contact(
            name="María García",
            email="maria@example.com",
            phone="555-1234"
        )

    def test_create_contact(self, repository, sample_contact):
        """Should successfully create a contact."""
        created = repository.create(sample_contact)
        assert created == sample_contact
        assert repository.count() == 1

    def test_cannot_create_duplicate_email(self, repository):
        """Should raise DuplicateEmailError for duplicate emails."""
        contact1 = Contact("Juan", "test@example.com", "123")
        contact2 = Contact("Pedro", "test@example.com", "456")

        repository.create(contact1)

        with pytest.raises(DuplicateEmailError, match="already exists"):
            repository.create(contact2)

    def test_duplicate_email_case_insensitive(self, repository):
        """Should detect duplicate emails regardless of case."""
        contact1 = Contact("Juan", "test@example.com", "123")
        contact2 = Contact("Pedro", "TEST@EXAMPLE.COM", "456")

        repository.create(contact1)

        with pytest.raises(DuplicateEmailError):
            repository.create(contact2)

    def test_find_by_name_exact_match(self, repository):
        """Should find contact by exact name match."""
        contact = Contact("Juan Pérez", "juan@test.com", "123")
        repository.create(contact)

        results = repository.find_by_name("Juan Pérez")
        assert len(results) == 1
        assert results[0] == contact

    def test_find_by_name_partial_match(self, repository):
        """Should find contact by partial name match."""
        contact = Contact("Juan Pérez", "juan@test.com", "123")
        repository.create(contact)

        results = repository.find_by_name("Juan")
        assert len(results) == 1
        assert results[0] == contact

    def test_find_by_name_case_insensitive(self, repository):
        """Should find contact regardless of case."""
        contact = Contact("Juan Pérez", "juan@test.com", "123")
        repository.create(contact)

        results = repository.find_by_name("juan pérez")
        assert len(results) == 1
        assert results[0] == contact

    def test_find_by_name_multiple_results(self, repository):
        """Should return all matching contacts."""
        contact1 = Contact("Juan Pérez", "juan1@test.com", "123")
        contact2 = Contact("Juan García", "juan2@test.com", "456")
        contact3 = Contact("Pedro López", "pedro@test.com", "789")

        repository.create(contact1)
        repository.create(contact2)
        repository.create(contact3)

        results = repository.find_by_name("Juan")
        assert len(results) == 2
        assert contact1 in results
        assert contact2 in results

    def test_find_by_name_no_results(self, repository):
        """Should return empty list when no matches found."""
        contact = Contact("Juan", "juan@test.com", "123")
        repository.create(contact)

        results = repository.find_by_name("Pedro")
        assert results == []

    def test_find_by_name_empty_query(self, repository):
        """Should return empty list for empty search query."""
        contact = Contact("Juan", "juan@test.com", "123")
        repository.create(contact)

        results = repository.find_by_name("")
        assert results == []

    def test_list_all_contacts(self, repository):
        """Should return all contacts in the repository."""
        contact1 = Contact("Juan", "juan@test.com", "123")
        contact2 = Contact("María", "maria@test.com", "456")
        contact3 = Contact("Pedro", "pedro@test.com", "789")

        repository.create(contact1)
        repository.create(contact2)
        repository.create(contact3)

        all_contacts = repository.list_all()
        assert len(all_contacts) == 3
        assert contact1 in all_contacts
        assert contact2 in all_contacts
        assert contact3 in all_contacts

    def test_list_all_empty_repository(self, repository):
        """Should return empty list when repository is empty."""
        assert repository.list_all() == []

    def test_repository_count(self, repository):
        """Should accurately count contacts."""
        assert repository.count() == 0

        repository.create(Contact("Juan", "juan@test.com", "123"))
        assert repository.count() == 1

        repository.create(Contact("María", "maria@test.com", "456"))
        assert repository.count() == 2

    def test_clear_repository(self, repository):
        """Should remove all contacts when cleared."""
        repository.create(Contact("Juan", "juan@test.com", "123"))
        repository.create(Contact("María", "maria@test.com", "456"))

        repository.clear()
        assert repository.count() == 0
        assert repository.list_all() == []


class TestContactEquality:
    """Test contact comparison logic."""

    def test_contacts_equal_by_id(self):
        """Should consider contacts equal if they have the same ID."""
        contact1 = Contact("Juan", "juan@test.com", "123", contact_id="same-id")
        contact2 = Contact("María", "maria@test.com", "456", contact_id="same-id")

        assert contact1 == contact2

    def test_contacts_not_equal_different_id(self):
        """Should consider contacts different if IDs differ."""
        contact1 = Contact("Juan", "juan@test.com", "123")
        contact2 = Contact("Juan", "juan@test.com", "123")

        assert contact1 != contact2

    def test_contact_not_equal_to_non_contact(self):
        """Should return False when comparing with non-Contact object."""
        contact = Contact("Juan", "juan@test.com", "123")
        assert contact != "not a contact"
        assert contact != 123
        assert contact != None


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_contact_with_special_characters(self):
        """Should handle special characters in fields."""
        contact = Contact(
            name="José María Ñoño",
            email="josé@example.com",
            phone="+52 (55) 1234-5678"
        )
        assert contact.name == "José María Ñoño"
        assert contact.email == "josé@example.com"
        assert contact.phone == "+52 (55) 1234-5678"

    def test_email_with_multiple_at_symbols(self):
        """Should accept email with multiple @ symbols."""
        contact = Contact(
            name="Juan",
            email="user@subdomain@example.com",
            phone="123"
        )
        assert "@" in contact.email

    def test_very_long_fields(self):
        """Should handle very long field values."""
        long_name = "A" * 1000
        long_email = "a" * 100 + "@" + "b" * 100 + ".com"
        long_phone = "1" * 50

        contact = Contact(name=long_name, email=long_email, phone=long_phone)
        assert len(contact.name) == 1000
        assert "@" in contact.email
        assert len(contact.phone) == 50
