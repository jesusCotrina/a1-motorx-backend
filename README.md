# Gestión de Talleres — Backend (FastAPI)

API REST que da servicio a la app web, la demo y la app móvil (Flutter).

## Stack

- FastAPI + Uvicorn
- SQLAlchemy 2.0 (modelos declarativos)
- Autenticación JWT (access + refresh), contraseñas con bcrypt
- Base de datos:
  - **Desarrollo rápido**: SQLite (por defecto, sin instalar nada). El esquema
    se crea solo al arrancar (`app/db/bootstrap.py`).
  - **Real / producción**: PostgreSQL 16 con scripts SQL numerados en
    `db/migrations/` (`scripts/migrate.py`).

## Puesta en marcha (SQLite, sin dependencias externas)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

copy .env.example .env            # ya trae SQLite por defecto

python scripts\seed_test_users.py  # crea 1 usuario por rol (correos aleatorios)
uvicorn app.main:app --reload
```

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- OpenAPI JSON: http://localhost:8000/openapi.json

Las credenciales de prueba quedan en `back/TEST_USERS.txt`
(contraseña común: `Taller2026!`).

## Puesta en marcha con PostgreSQL

1. Levanta PostgreSQL (Docker: `docker compose up -d`, o instalación nativa).
2. En `.env`:
   `DATABASE_URL=postgresql+psycopg://taller:taller@localhost:5432/taller`
3. Aplica migraciones y siembra usuarios:

```powershell
python scripts\migrate.py           # aplica db/migrations/*.sql
python scripts\migrate.py --status   # estado
python scripts\seed_test_users.py
```

Cada `NNN_nombre.sql` termina insertando su versión en `schema_migrations`
(ver `001_init.sql`).

## Roles

| id | code          | name                |
|----|---------------|---------------------|
| 1  | `super_admin` | Super Administrador |
| 2  | `admin`       | Administrador       |
| 3  | `mecanico`    | Mecánico            |

## Endpoints de autenticación

| Método | Ruta                  | Descripción                              |
|--------|-----------------------|------------------------------------------|
| POST   | `/api/v1/auth/login`  | `{email, password}` → tokens + usuario   |
| POST   | `/api/v1/auth/refresh`| `{refresh_token}` → tokens nuevos        |
| GET    | `/api/v1/auth/me`     | Usuario actual (cabecera `Bearer`)       |

Protección por rol en el resto de endpoints:

```python
from app.core.deps import require_roles

@router.get("/algo", dependencies=[Depends(require_roles("admin", "super_admin"))])
```

## Tests

```powershell
pytest
```

Los tests usan SQLite en fichero temporal (`test.db`), aislado de `dev.db`.

## Estructura

```
app/
  main.py                 FastAPI + lifespan (bootstrap SQLite)
  core/
    config.py             settings desde .env
    security.py           hash de contraseñas + JWT
    deps.py               get_current_user, require_roles
  db/
    base.py               DeclarativeBase
    session.py            engine + sesión
    bootstrap.py          crea esquema + roles (solo SQLite)
  models/                 Role, User
  schemas/                auth, user (Pydantic)
  api/v1/
    router.py             router raíz v1
    endpoints/auth.py     login / refresh / me
db/
  migrations/001_init.sql esquema PostgreSQL
scripts/
  migrate.py              aplicador de migraciones (PostgreSQL)
  seed_test_users.py      usuarios de prueba por rol
```
