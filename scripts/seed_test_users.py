"""Crea una empresa demo y un usuario de prueba por cada rol, con correo
aleatorio.

Uso:
    python scripts/seed_test_users.py

- Funciona igual con SQLite (crea el esquema si hace falta) y con PostgreSQL
  (en ese caso ejecuta antes: python scripts/migrate.py).
- Es idempotente: si ya existe un usuario para un rol, no crea otro (pero le
  asigna la empresa demo si le faltaba, para datos creados antes de la
  migracion de tenancy).
- Los 3 roles (super_admin, admin, mecanico) pertenecen a la misma empresa
  demo: cada empresa real tiene su propio super_admin (dueno del taller).
- Escribe las credenciales en back/TEST_USERS.txt y las imprime por pantalla.

Contrasena de todos los usuarios: Taller2026!
"""

from __future__ import annotations

import random
import string
import sys
from pathlib import Path

from sqlalchemy import select

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from app.core.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import Empresa, Role, User  # noqa: E402

PASSWORD = "Taller2026!"

EMPRESA_CODIGO = "DEMO"
EMPRESA_NOMBRE = "Taller Demo"

# (codigo de rol, nombre completo del usuario de prueba)
SPEC: list[tuple[str, str]] = [
    ("super_admin", "Sofia Nunez"),
    ("admin", "Andres Diaz"),
    ("mecanico", "Marco Ruiz"),
]


def _random_suffix(n: int = 5) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def main() -> None:
    if settings.is_sqlite:
        from app.db.bootstrap import init_db_dev

        init_db_dev()

    password_hash = hash_password(PASSWORD)
    rows: list[tuple[str, str, str]] = []

    with SessionLocal() as db:
        empresa = db.scalar(select(Empresa).where(Empresa.codigo == EMPRESA_CODIGO))
        if empresa is None:
            empresa = Empresa(codigo=EMPRESA_CODIGO, nombre=EMPRESA_NOMBRE)
            db.add(empresa)
            db.flush()

        for code, full_name in SPEC:
            role = db.scalar(select(Role).where(Role.code == code))
            if role is None:
                raise SystemExit(
                    f"El rol '{code}' no existe. Ejecuta primero las migraciones."
                )

            existing = db.scalar(select(User).where(User.role_id == role.id))
            if existing is not None:
                if existing.empresa_id != empresa.id:
                    existing.empresa_id = empresa.id
                    db.flush()
                rows.append((role.name, existing.email, "ya existia"))
                continue

            email = f"{code.replace('_', '')}.{_random_suffix()}@taller.app"
            db.add(
                User(
                    email=email,
                    password_hash=password_hash,
                    full_name=full_name,
                    role_id=role.id,
                    empresa_id=empresa.id,
                )
            )
            rows.append((role.name, email, "creado"))

        db.commit()

    width = max(len(r[0]) for r in rows)
    body = "\n".join(f"  {name:<{width}}  {email:<32}  {note}" for name, email, note in rows)
    report = (
        "Usuarios de prueba\n"
        "==================\n\n"
        f"Empresa demo: {EMPRESA_NOMBRE} (codigo {EMPRESA_CODIGO})\n"
        f"Contrasena (todos): {PASSWORD}\n\n"
        f"{body}\n"
    )
    print(report)
    (BASE_DIR / "TEST_USERS.txt").write_text(report, encoding="utf-8")
    print(f"Guardado en: {BASE_DIR / 'TEST_USERS.txt'}")


if __name__ == "__main__":
    main()
