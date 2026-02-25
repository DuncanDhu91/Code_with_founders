# Sistema de Gestión de Contactos

Sistema simple y robusto para gestionar contactos con validaciones de datos y almacenamiento en memoria.

## Características

- Crear contactos con nombre, email y teléfono
- Validación de formato de email (debe contener @)
- Validación de teléfono no vacío
- Búsqueda de contactos por nombre (case-insensitive, coincidencia parcial)
- Listar todos los contactos
- Prevención de emails duplicados

## Requisitos

- Python 3.7+
- pytest (para testing)

## Instalación

```bash
# Instalar pytest
pip install pytest pytest-cov
```

## Estructura del Proyecto

```
order_system/
├── contact_system/
│   ├── __init__.py
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── contact.py          # Entidad Contact con validaciones
│   │   └── exceptions.py       # Excepciones personalizadas
│   └── repository/
│       ├── __init__.py
│       └── contact_repository.py  # Gestión de almacenamiento
└── tests/
    ├── __init__.py
    └── test_contact_system.py  # Suite completa de tests
```

## Uso

### Crear un Contacto

```python
from contact_system.domain import Contact

# Crear contacto válido
contact = Contact(
    name="Juan Pérez",
    email="juan@example.com",
    phone="+52 55 1234 5678"
)
```

### Gestionar Contactos con el Repositorio

```python
from contact_system.domain import Contact
from contact_system.repository import ContactRepository

# Inicializar repositorio
repo = ContactRepository()

# Crear contactos
contact1 = Contact("Juan Pérez", "juan@example.com", "555-1234")
contact2 = Contact("María García", "maria@example.com", "555-5678")

repo.create(contact1)
repo.create(contact2)

# Buscar por nombre
results = repo.find_by_name("Juan")  # Búsqueda parcial case-insensitive
print(results)  # [Contact(name=Juan Pérez, ...)]

# Listar todos
all_contacts = repo.list_all()
print(f"Total de contactos: {len(all_contacts)}")
```

### Manejo de Errores

```python
from contact_system.domain import Contact, ValidationError, DuplicateEmailError

# Email inválido
try:
    contact = Contact("Juan", "invalid-email", "123")
except ValidationError as e:
    print(f"Error: {e}")  # Email must contain @ symbol

# Email duplicado
try:
    repo.create(contact1)
    repo.create(contact1)  # Mismo email
except DuplicateEmailError as e:
    print(f"Error: {e}")  # A contact with email 'juan@example.com' already exists
```

## Testing

### Ejecutar Tests

```bash
# Todos los tests
pytest order_system/tests/

# Con coverage
pytest order_system/tests/ --cov=contact_system --cov-report=html

# Modo verbose
pytest order_system/tests/ -v

# Tests específicos
pytest order_system/tests/test_contact_system.py::TestContactValidation
```

### Cobertura de Tests

El proyecto incluye tests exhaustivos que cubren:

- Validación de email con/sin @
- Validación de campos vacíos
- Normalización de emails (lowercase)
- Detección de duplicados (case-insensitive)
- Búsqueda por nombre (parcial, case-insensitive)
- Manejo de caracteres especiales
- Edge cases (campos muy largos, espacios en blanco)

**Coverage objetivo:** >90%

## Validaciones

### Email
- Debe contener al menos un símbolo @
- No puede estar vacío
- Se normaliza a minúsculas
- Debe ser único en el sistema

### Teléfono
- No puede estar vacío
- Acepta cualquier formato (con o sin separadores)

### Nombre
- No puede estar vacío
- Acepta caracteres especiales (ñ, acentos, etc.)

## Decisiones de Diseño

### Arquitectura Limpia
- **Domain Layer**: Entidades con lógica de negocio y validaciones
- **Repository Layer**: Abstracción de almacenamiento de datos
- **Exception Layer**: Manejo explícito de errores

### Patrones Aplicados
- **Repository Pattern**: Separación de lógica de acceso a datos
- **Fail-Fast Validation**: Validaciones en el constructor
- **Value Objects**: Email y phone como valores validados
- **Inmutabilidad**: Una vez creado, el ID del contacto no cambia

### Trade-offs
- **Almacenamiento en memoria**: Simple pero no persistente (apropiado para el alcance del ejercicio)
- **Validación básica de email**: Solo verifica @, no formato RFC completo (suficiente para requisitos)
- **Búsqueda lineal**: O(n) aceptable para volúmenes pequeños

## Extensiones Futuras

Si se requiere escalar el sistema:

1. **Persistencia**: Agregar adapters para SQL/NoSQL
2. **Validación avanzada**: Usar bibliotecas como `email-validator`
3. **Índices**: Agregar índices por nombre para búsquedas O(log n)
4. **API REST**: Exponer funcionalidad vía FastAPI/Flask
5. **Actualización/Eliminación**: Agregar operaciones UPDATE y DELETE

## Autor

Sistema desarrollado como ejercicio de código en Python 3.7+

## Licencia

MIT
