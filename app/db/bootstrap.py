"""Arranque de base de datos para desarrollo con SQLite.

Cuando DATABASE_URL apunta a SQLite no hay migraciones: se crean las tablas
desde los modelos y se insertan los roles base. Con PostgreSQL se usan los
scripts de db/migrations/ (ver scripts/migrate.py).
"""


from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import Role, User  # noqa: F401  (registra los modelos en Base)

DEFAULT_ROLES: list[tuple[int, str, str]] = [
    (1, "super_admin", "Super Administrador"),
    (2, "admin", "Administrador"),
    (3, "mecanico", "Mecanico"),
]


def seed_roles() -> None:
    with SessionLocal() as db:
        for role_id, code, name in DEFAULT_ROLES:
            if db.get(Role, role_id) is None:
                db.add(Role(id=role_id, code=code, name=name))
        db.commit()


def init_db_dev() -> None:
    Base.metadata.create_all(engine)
    seed_roles()
