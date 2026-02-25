"""Ejemplo de uso del Sistema de Gestión de Contactos.

Este script demuestra todas las funcionalidades principales del sistema.
"""

from contact_system.domain import Contact, ValidationError, DuplicateEmailError
from contact_system.repository import ContactRepository


def print_separator():
    """Imprime una línea separadora."""
    print("\n" + "=" * 70 + "\n")


def main():
    """Ejecuta ejemplos de uso del sistema."""

    print("SISTEMA DE GESTIÓN DE CONTACTOS - DEMO")
    print_separator()

    # Inicializar repositorio
    repo = ContactRepository()

    # 1. CREAR CONTACTOS VÁLIDOS
    print("1. Creando contactos válidos...")
    try:
        contact1 = Contact(
            name="Juan Pérez",
            email="juan@example.com",
            phone="+52 55 1234 5678"
        )
        repo.create(contact1)
        print(f"✓ Contacto creado: {contact1.name} ({contact1.email})")

        contact2 = Contact(
            name="María García",
            email="maria@example.com",
            phone="555-9876"
        )
        repo.create(contact2)
        print(f"✓ Contacto creado: {contact2.name} ({contact2.email})")

        contact3 = Contact(
            name="Pedro López",
            email="pedro@company.com",
            phone="(555) 111-2222"
        )
        repo.create(contact3)
        print(f"✓ Contacto creado: {contact3.name} ({contact3.email})")

        contact4 = Contact(
            name="Ana Martínez",
            email="ana@test.org",
            phone="555-4444"
        )
        repo.create(contact4)
        print(f"✓ Contacto creado: {contact4.name} ({contact4.email})")

    except ValidationError as e:
        print(f"✗ Error de validación: {e}")

    print_separator()

    # 2. LISTAR TODOS LOS CONTACTOS
    print("2. Listando todos los contactos...")
    all_contacts = repo.list_all()
    print(f"Total de contactos: {len(all_contacts)}")
    for contact in all_contacts:
        print(f"  - {contact.name}: {contact.email} | {contact.phone}")

    print_separator()

    # 3. BUSCAR CONTACTOS POR NOMBRE
    print("3. Búsqueda de contactos...")

    # Búsqueda exacta
    results = repo.find_by_name("Juan Pérez")
    print(f"\nBúsqueda exacta 'Juan Pérez': {len(results)} resultados")
    for contact in results:
        print(f"  ✓ {contact.name} - {contact.email}")

    # Búsqueda parcial
    results = repo.find_by_name("María")
    print(f"\nBúsqueda parcial 'María': {len(results)} resultados")
    for contact in results:
        print(f"  ✓ {contact.name} - {contact.email}")

    # Búsqueda case-insensitive
    results = repo.find_by_name("PEDRO")
    print(f"\nBúsqueda case-insensitive 'PEDRO': {len(results)} resultados")
    for contact in results:
        print(f"  ✓ {contact.name} - {contact.email}")

    # Búsqueda sin resultados
    results = repo.find_by_name("Roberto")
    print(f"\nBúsqueda 'Roberto': {len(results)} resultados")

    print_separator()

    # 4. MANEJO DE ERRORES - EMAIL INVÁLIDO
    print("4. Intentando crear contacto con email inválido...")
    try:
        invalid_contact = Contact(
            name="Carlos Ruiz",
            email="invalid-email",  # Sin @
            phone="555-7777"
        )
        repo.create(invalid_contact)
    except ValidationError as e:
        print(f"✗ Error capturado correctamente: {e}")

    print_separator()

    # 5. MANEJO DE ERRORES - TELÉFONO VACÍO
    print("5. Intentando crear contacto con teléfono vacío...")
    try:
        invalid_contact = Contact(
            name="Laura Sánchez",
            email="laura@example.com",
            phone=""  # Vacío
        )
        repo.create(invalid_contact)
    except ValidationError as e:
        print(f"✗ Error capturado correctamente: {e}")

    print_separator()

    # 6. MANEJO DE ERRORES - EMAIL DUPLICADO
    print("6. Intentando crear contacto con email duplicado...")
    try:
        duplicate_contact = Contact(
            name="Juan Diferente",
            email="juan@example.com",  # Ya existe
            phone="555-0000"
        )
        repo.create(duplicate_contact)
    except DuplicateEmailError as e:
        print(f"✗ Error capturado correctamente: {e}")

    print_separator()

    # 7. EMAIL DUPLICADO CASE-INSENSITIVE
    print("7. Intentando crear contacto con email duplicado (diferente case)...")
    try:
        duplicate_contact = Contact(
            name="María Nueva",
            email="MARIA@EXAMPLE.COM",  # Ya existe (maria@example.com)
            phone="555-1111"
        )
        repo.create(duplicate_contact)
    except DuplicateEmailError as e:
        print(f"✗ Error capturado correctamente: {e}")

    print_separator()

    # 8. NORMALIZACIÓN DE DATOS
    print("8. Verificando normalización de datos...")
    test_contact = Contact(
        name="  José  ",  # Con espacios
        email="  JOSE@TEST.COM  ",  # Con espacios y mayúsculas
        phone="  555-8888  "  # Con espacios
    )
    print(f"Nombre normalizado: '{test_contact.name}'")
    print(f"Email normalizado: '{test_contact.email}'")
    print(f"Teléfono normalizado: '{test_contact.phone}'")

    print_separator()

    # 9. ESTADÍSTICAS FINALES
    print("9. Estadísticas finales del repositorio")
    print(f"Total de contactos: {repo.count()}")
    print(f"Contactos listados: {len(repo.list_all())}")

    print_separator()
    print("DEMO COMPLETADA EXITOSAMENTE ✓")
    print_separator()


if __name__ == "__main__":
    main()
