# Quickstart Guide - Sistema de Gestión de Contactos

## Instalación Rápida (< 2 minutos)

### 1. Requisitos Previos
```bash
# Verificar versión de Python
python --version  # Debe ser 3.7 o superior
```

### 2. Instalar Dependencias
```bash
cd order_system
pip install -r requirements.txt
```

### 3. Ejecutar Tests
```bash
# Tests básicos
pytest tests/

# Tests con coverage
pytest tests/ --cov=contact_system --cov-report=html

# Tests verbose
pytest tests/ -v
```

### 4. Ejecutar Demo Interactiva
```bash
python example_usage.py
```

## Verificación Exitosa

Si todo está correcto, deberías ver:

```
============================== 29 passed in 0.31s ==============================
```

Y el reporte de cobertura:
```
TOTAL                                                70      1    99%
```

## Uso Básico en 30 Segundos

### Crear y Gestionar Contactos

```python
# Importar módulos necesarios
from contact_system.domain import Contact
from contact_system.repository import ContactRepository

# 1. Inicializar repositorio
repo = ContactRepository()

# 2. Crear contacto
contact = Contact(
    name="Juan Pérez",
    email="juan@example.com",
    phone="+1234567890"
)

# 3. Guardar en repositorio
repo.create(contact)

# 4. Buscar contactos
results = repo.find_by_name("Juan")
print(f"Encontrados: {len(results)} contactos")

# 5. Listar todos
all_contacts = repo.list_all()
print(f"Total: {len(all_contacts)} contactos")
```

## Manejo de Errores

```python
from contact_system.domain import ValidationError, DuplicateEmailError

# Email inválido (sin @)
try:
    contact = Contact("Juan", "invalid-email", "123")
except ValidationError as e:
    print(f"Error: {e}")

# Email duplicado
try:
    repo.create(contact1)  # Primera vez: OK
    repo.create(contact1)  # Segunda vez: Error
except DuplicateEmailError as e:
    print(f"Error: {e}")
```

## Ejemplos Comunes

### Búsqueda Case-Insensitive

```python
contact = Contact("Juan Pérez", "juan@test.com", "123")
repo.create(contact)

# Todas estas búsquedas funcionan
repo.find_by_name("Juan")      # ✓
repo.find_by_name("juan")      # ✓
repo.find_by_name("JUAN")      # ✓
repo.find_by_name("Pérez")     # ✓
repo.find_by_name("pérez")     # ✓
```

### Búsqueda Parcial

```python
contact1 = Contact("Juan Pérez", "juan1@test.com", "123")
contact2 = Contact("Juan García", "juan2@test.com", "456")
repo.create(contact1)
repo.create(contact2)

# Buscar por "Juan" devuelve ambos
results = repo.find_by_name("Juan")
print(len(results))  # 2
```

### Normalización Automática

```python
# El sistema normaliza automáticamente los datos
contact = Contact(
    name="  José  ",                    # Con espacios
    email="  JOSE@EXAMPLE.COM  ",       # Mayúsculas y espacios
    phone="  555-1234  "                # Con espacios
)

print(contact.name)   # "José" (sin espacios)
print(contact.email)  # "jose@example.com" (lowercase, sin espacios)
print(contact.phone)  # "555-1234" (sin espacios)
```

## Estructura del Proyecto

```
order_system/
├── contact_system/       # Código fuente
│   ├── domain/          # Entidades y reglas de negocio
│   └── repository/      # Gestión de datos
├── tests/               # Suite de tests
├── example_usage.py     # Demo interactiva
├── README.md           # Documentación completa
└── requirements.txt    # Dependencias
```

## Comandos Útiles

```bash
# Ejecutar solo tests de validación
pytest tests/test_contact_system.py::TestContactValidation -v

# Ejecutar solo tests de repositorio
pytest tests/test_contact_system.py::TestContactRepository -v

# Ver reporte de cobertura en HTML
pytest tests/ --cov=contact_system --cov-report=html
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux

# Limpiar cache de pytest
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type d -name .pytest_cache -exec rm -rf {} +
```

## Casos de Uso Reales

### Sistema de CRM Básico

```python
repo = ContactRepository()

# Agregar clientes
repo.create(Contact("Ana García", "ana@empresa.com", "555-0001"))
repo.create(Contact("Luis Martínez", "luis@empresa.com", "555-0002"))
repo.create(Contact("María López", "maria@empresa.com", "555-0003"))

# Buscar cliente específico
clientes = repo.find_by_name("Ana")
if clientes:
    print(f"Cliente encontrado: {clientes[0].email}")

# Listar todos los clientes
print(f"Total de clientes: {repo.count()}")
```

### Validación de Formularios Web

```python
def validate_contact_form(form_data):
    """Valida datos de formulario usando el sistema."""
    try:
        contact = Contact(
            name=form_data['name'],
            email=form_data['email'],
            phone=form_data['phone']
        )
        return {"valid": True, "contact": contact}
    except ValidationError as e:
        return {"valid": False, "error": str(e)}

# Uso
result = validate_contact_form({
    'name': 'Juan',
    'email': 'juan@test.com',
    'phone': '123'
})

if result['valid']:
    repo.create(result['contact'])
```

### Importación Masiva de Contactos

```python
import csv

def import_contacts_from_csv(filename):
    """Importa contactos desde archivo CSV."""
    repo = ContactRepository()
    imported = 0
    errors = []

    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                contact = Contact(
                    name=row['name'],
                    email=row['email'],
                    phone=row['phone']
                )
                repo.create(contact)
                imported += 1
            except (ValidationError, DuplicateEmailError) as e:
                errors.append(f"Row {row}: {e}")

    return {
        'imported': imported,
        'errors': errors,
        'total': repo.count()
    }
```

## Troubleshooting

### Error: ModuleNotFoundError

```bash
# Asegúrate de estar en el directorio correcto
cd order_system

# Verifica la estructura
ls contact_system/
```

### Error: pytest: command not found

```bash
# Instalar pytest
pip install pytest pytest-cov

# Verificar instalación
pytest --version
```

### Error: Import Error

```python
# Usa imports absolutos desde la raíz de order_system
from contact_system.domain import Contact  # ✓
# NO uses:
# from domain import Contact  # ✗
```

## Próximos Pasos

1. **Leer documentación completa:** `README.md`
2. **Entender arquitectura:** `ARCHITECTURE.md`
3. **Ver resumen del PR:** `PR_SUMMARY.md`
4. **Ejecutar demo:** `python example_usage.py`
5. **Explorar tests:** `tests/test_contact_system.py`

## Soporte

Para más información, consulta:
- `README.md` - Documentación completa
- `ARCHITECTURE.md` - Diseño del sistema
- `PR_SUMMARY.md` - Resumen del proyecto

## Resumen de Comandos

```bash
# Setup
cd order_system
pip install -r requirements.txt

# Testing
pytest tests/                                    # Tests básicos
pytest tests/ -v                                 # Verbose
pytest tests/ --cov=contact_system              # Con coverage

# Demo
python example_usage.py                         # Ejecutar demo

# Development
pytest tests/ --cov=contact_system --cov-report=html  # HTML coverage
open htmlcov/index.html                               # Ver reporte
```

Listo para usar en < 2 minutos.
