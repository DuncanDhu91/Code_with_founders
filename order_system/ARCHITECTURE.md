# Arquitectura del Sistema de Gestión de Contactos

## Diagrama de Capas

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│                  (example_usage.py, tests)                   │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Repository Layer                           │
│                 ContactRepository                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ create(contact) -> Contact                           │  │
│  │ find_by_name(name) -> List[Contact]                  │  │
│  │ list_all() -> List[Contact]                          │  │
│  │ _email_exists(email) -> bool                         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  Storage:                                                    │
│  - _contacts: dict[str, Contact]     (id -> Contact)       │
│  - _email_index: dict[str, str]      (email -> id)         │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     Domain Layer                             │
│                       Contact                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Attributes:                                          │  │
│  │ - id: str (UUID)                                     │  │
│  │ - name: str (validated)                              │  │
│  │ - email: str (validated, normalized)                 │  │
│  │ - phone: str (validated)                             │  │
│  │                                                       │  │
│  │ Methods:                                              │  │
│  │ - _validate_name(name)                               │  │
│  │ - _validate_email(email)                             │  │
│  │ - _validate_phone(phone)                             │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│                      Exceptions                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ - ValidationError (base)                             │  │
│  │ - DuplicateEmailError (specific)                     │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Flujo de Creación de Contacto

```
User/Test
    │
    │ 1. new Contact(name, email, phone)
    ▼
┌──────────┐
│ Contact  │ 2. Validate all fields
│  __init__│    - _validate_name()
└────┬─────┘    - _validate_email()
     │          - _validate_phone()
     │ 3. If valid, normalize data
     │    - trim whitespace
     │    - lowercase email
     │    - generate UUID
     ▼
Contact Instance Created
     │
     │ 4. repo.create(contact)
     ▼
┌────────────────┐
│ ContactRepo    │ 5. Check email uniqueness
│  create()      │    - _email_exists(email)
└────┬───────────┘
     │
     ├─ If duplicate → raise DuplicateEmailError
     │
     └─ 6. If unique:
        - Store in _contacts dict
        - Index in _email_index
        - Return contact
```

## Flujo de Búsqueda por Nombre

```
User/Test
    │
    │ 1. repo.find_by_name("Juan")
    ▼
┌────────────────┐
│ ContactRepo    │ 2. Normalize search term
│  find_by_name()│    - strip whitespace
└────┬───────────┘    - convert to lowercase
     │
     │ 3. Iterate over all contacts
     │    O(n) linear search
     ▼
For each contact:
    ├─ If search_term in contact.name.lower()
    │  → Add to results list
    │
    └─ Else continue
         ▼
    Return List[Contact]
```

## Estructura de Datos

### 1. Contact (Domain Entity)

```python
Contact {
    id: "550e8400-e29b-41d4-a716-446655440000"  # UUID v4
    name: "Juan Pérez"                          # Original case
    email: "juan@example.com"                   # Normalized lowercase
    phone: "+52 55 1234 5678"                   # Any format
}
```

### 2. ContactRepository Storage

```python
_contacts = {
    "550e8400-e29b-41d4-a716-446655440000": Contact(...),
    "6ba7b810-9dad-11d1-80b4-00c04fd430c8": Contact(...),
    # ... more contacts
}

_email_index = {
    "juan@example.com": "550e8400-e29b-41d4-a716-446655440000",
    "maria@example.com": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    # ... more emails
}
```

## Complejidad Temporal

| Operación              | Complejidad | Justificación                          |
|------------------------|-------------|----------------------------------------|
| `create(contact)`      | O(1)        | Dict insert + index update             |
| `_email_exists(email)` | O(1)        | Dict lookup en _email_index            |
| `find_by_name(name)`   | O(n)        | Linear scan sobre todos los contactos  |
| `list_all()`           | O(n)        | Convert dict.values() to list          |
| `count()`              | O(1)        | len() sobre dict                       |

## Patrones de Diseño Aplicados

### 1. Repository Pattern

**Problema:** Necesidad de abstraer la lógica de almacenamiento de datos.

**Solución:** `ContactRepository` encapsula toda la lógica de persistencia.

**Beneficios:**
- Fácil cambiar de in-memory a DB real
- Tests unitarios sin dependencias externas
- Separación de concerns clara

```python
# Fácil migración a PostgreSQL
class PostgresContactRepository(ContactRepository):
    def create(self, contact):
        session.add(contact)
        session.commit()
```

### 2. Fail-Fast Validation

**Problema:** Detectar datos inválidos lo antes posible.

**Solución:** Validaciones en el constructor de `Contact`.

**Beneficios:**
- Imposible crear objetos inválidos
- Errores claros y tempranos
- Garantía de invariantes

```python
# Imposible crear contacto inválido
try:
    contact = Contact("", "invalid", "")
except ValidationError:
    # Error capturado inmediatamente
    pass
```

### 3. Value Objects (Implicit)

**Problema:** Email y phone tienen reglas de negocio.

**Solución:** Validación y normalización en construcción.

**Beneficios:**
- Email siempre en formato correcto (lowercase)
- Phone siempre no vacío
- Confianza en integridad de datos

### 4. Exception Hierarchy

**Problema:** Diferentes tipos de errores requieren manejo diferente.

**Solución:** `ValidationError` (base) y `DuplicateEmailError` (específico).

**Beneficios:**
- Catch selectivo: `except DuplicateEmailError`
- Mensajes de error descriptivos
- Fácil debugging

## Decisiones Arquitectónicas

### 1. In-Memory Storage

**Decisión:** Usar dicts Python en lugar de DB.

**Trade-offs:**
- ✓ Pro: Simple, rápido, sin dependencias
- ✓ Pro: Tests deterministas sin setup
- ✗ Con: No persistente entre ejecuciones
- ✗ Con: No escalable a millones de registros

**Mitigación:** Repository pattern permite cambiar a DB sin afectar domain layer.

### 2. Email Index Separado

**Decisión:** Mantener `_email_index` dict adicional.

**Trade-offs:**
- ✓ Pro: O(1) para verificar duplicados
- ✓ Pro: O(1) para buscar por email (futuro)
- ✗ Con: Usa más memoria
- ✗ Con: Dos estructuras a sincronizar

**Justificación:** La verificación de unicidad es crítica y frecuente.

### 3. Linear Search por Nombre

**Decisión:** No indexar nombres, buscar linealmente.

**Trade-offs:**
- ✓ Pro: Simple implementación
- ✓ Pro: Permite búsquedas parciales (LIKE)
- ✓ Pro: Suficiente para <10K contactos
- ✗ Con: O(n) no escala a millones

**Mitigación:** Si es necesario, agregar índice con Trie o full-text search.

### 4. Case-Insensitive Email

**Decisión:** Normalizar a lowercase.

**Trade-offs:**
- ✓ Pro: Mejor UX (evita duplicados)
- ✓ Pro: Estándar de la industria
- ✗ Con: Técnicamente RFC permite case-sensitivity

**Justificación:** En práctica, proveedores de email ignoran case.

## Extensibilidad

### Agregar Persistencia SQL

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class SQLContactRepository(ContactRepository):
    def __init__(self, connection_string):
        self.engine = create_engine(connection_string)
        self.Session = sessionmaker(bind=self.engine)

    def create(self, contact):
        session = self.Session()
        if self._email_exists(contact.email):
            raise DuplicateEmailError(...)
        session.add(contact)
        session.commit()
        return contact
```

### Agregar Cache Layer

```python
from functools import lru_cache

class CachedContactRepository(ContactRepository):
    @lru_cache(maxsize=1000)
    def find_by_name(self, name):
        return super().find_by_name(name)
```

### Agregar Validación Avanzada

```python
import email_validator

class Contact:
    @staticmethod
    def _validate_email(email):
        try:
            email_validator.validate_email(email)
        except email_validator.EmailNotValidError:
            raise ValidationError("Invalid email format")
```

## Testing Strategy

### Unit Tests (Domain Layer)

```python
# Test Contact validation independently
def test_contact_validates_email():
    with pytest.raises(ValidationError):
        Contact("name", "invalid", "phone")
```

### Integration Tests (Repository Layer)

```python
# Test repository operations with real Contact instances
def test_repository_prevents_duplicates():
    repo = ContactRepository()
    repo.create(Contact("A", "test@test.com", "123"))
    with pytest.raises(DuplicateEmailError):
        repo.create(Contact("B", "test@test.com", "456"))
```

### Edge Cases Tests

```python
# Test boundary conditions and special scenarios
def test_handles_special_characters():
    contact = Contact("José María", "josé@test.com", "+52")
    assert contact.name == "José María"
```

## Conclusión

Sistema con arquitectura limpia, separación de concerns clara y preparado para crecer. El uso de patrones estándar facilita mantenimiento y extensión futura.
