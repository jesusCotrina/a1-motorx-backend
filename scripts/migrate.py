"""Aplicador de migraciones SQL simple (solo PostgreSQL).

Ejecuta en orden los ficheros db/migrations/*.sql que aun no aparezcan en la
tabla schema_migrations. Cada fichero es responsable de insertar su propia
fila en schema_migrations (ver 001_init.sql como ejemplo).

Uso:
    python scripts/migrate.py            # aplica migraciones pendientes
    python scripts/migrate.py --status   # muestra el estado
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine, text

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from app.core.config import settings  # noqa: E402

MIGRATIONS_DIR = BASE_DIR / "db" / "migrations"

if settings.is_sqlite:
    raise SystemExit(
        "DATABASE_URL apunta a SQLite: no se usan migraciones SQL.\n"
        "El esquema se crea solo al arrancar la API (ver app/db/bootstrap.py)."
    )

engine = create_engine(settings.database_url, future=True)


def applied_versions() -> set[str]:
    with engine.connect() as conn:
        exists = conn.execute(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'schema_migrations'"
            )
        ).first()
        if not exists:
            return set()
        return set(conn.execute(text("SELECT version FROM schema_migrations")).scalars())


def run_sql_file(path: Path) -> None:
    with engine.begin() as conn:
        conn.exec_driver_sql(path.read_text(encoding="utf-8"))


def migrate() -> None:
    done = applied_versions()
    pending = [f for f in sorted(MIGRATIONS_DIR.glob("*.sql")) if f.stem not in done]
    if not pending:
        print("Sin migraciones pendientes.")
        return
    for f in pending:
        print(f"Aplicando {f.name} ...")
        run_sql_file(f)
    print(f"{len(pending)} migracion(es) aplicada(s).")


def status() -> None:
    done = applied_versions()
    for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
        print(f"{'OK ' if f.stem in done else '-- '}{f.name}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--status":
        status()
    else:
        migrate()
