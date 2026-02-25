<<<<<<< HEAD
# Code With Founders

Sistema integral de gestión empresarial con módulos de contactos y reservas.

## Descripción

Proyecto educativo que implementa patrones de arquitectura limpia en Python, incluyendo:
- **Sistema de Gestión de Contactos**: CRUD con validaciones y búsqueda
- **Sistema de Reservas**: Gestión de citas y disponibilidad

## Características

- Arquitectura por capas (Domain, Repository, Service)
- Validaciones robustas con excepciones personalizadas
- Búsqueda case-insensitive con coincidencias parciales
- Almacenamiento en memoria
- Cobertura de tests 99%+

## Estructura del Proyecto

```
.
├── order_system/          # Sistema de gestión de contactos
├── booking_system/        # Sistema de reservas
├── src/                   # Código fuente compartido
├── tests/                 # Tests unitarios
└── README.md              # Este archivo
```

## Instalación

### Requisitos
- Python 3.8+
- pytest (para tests)

### Setup

```bash
# Clonar el repositorio
git clone <repo-url>
cd Code_With_Founders

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

## Uso

### Sistema de Contactos

```python
from order_system.contact import Contact
from order_system.repository import ContactRepository

repo = ContactRepository()

# Crear contacto
contact = Contact(
    name="Juan Pérez",
    email="juan@example.com",
    phone="1234567890"
)
repo.add(contact)

# Buscar por nombre
results = repo.search_by_name("Juan")

# Obtener todos
all_contacts = repo.get_all()
```

## Testing

```bash
# Ejecutar todos los tests
pytest

# Con coverage
pytest --cov

# Tests específicos
pytest order_system/tests/
pytest booking_system/tests/
```

## Documentación Adicional

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Diseño detallado del sistema
- [SOLUTION_SUMMARY.md](./SOLUTION_SUMMARY.md) - Resumen de soluciones implementadas

## Contribuciones

Las contribuciones son bienvenidas. Por favor:
1. Crea una rama feature (`git checkout -b feature/mi-feature`)
2. Commit tus cambios (`git commit -am 'Add feature'`)
3. Push a la rama (`git push origin feature/mi-feature`)
4. Abre un Pull Request

## Licencia

MIT License

## Autor

Code With Founders - 2025
=======
# Code_with_founders
Repo for a challenge
>>>>>>> 87cf9a1ad1b58f9b5425bde9f8b52394761dfdba
