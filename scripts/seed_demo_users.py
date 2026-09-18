"""Crea los usuarios de demostracion con contrasenas hasheadas.

Uso:
    python scripts/seed_demo_users.py

Contrasena para todos: demo1234
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402

DEMO_PASSWORD = "demo1234"

DEMO_USERS = [
    ("admin@demo.taller", "Admin Demo", 1),
    ("jefe@demo.taller", "Jefe Demo", 2),
    ("mecanico@demo.taller", "Mecanico Demo", 3),
    ("recepcion@demo.taller", "Recepcion Demo", 4),
]

engine = create_engine(settings.database_url, future=True)


def main() -> None:
    pwd_hash = hash_password(DEMO_PASSWORD)
    with engine.begin() as conn:
        for email, full_name, role_id in DEMO_USERS:
            conn.execute(
                text(
                    "INSERT INTO users (email, password_hash, full_name, role_id) "
                    "VALUES (:email, :ph, :fn, :rid) "
                    "ON CONFLICT (email) DO NOTHING"
                ),
                {"email": email, "ph": pwd_hash, "fn": full_name, "rid": role_id},
            )
    print(f"Usuarios demo creados (contrasena: {DEMO_PASSWORD}).")


if __name__ == "__main__":
    main()
