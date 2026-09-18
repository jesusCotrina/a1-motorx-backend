import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///./test.db"
os.environ["JWT_SECRET"] = "test-secret"

_TEST_DB = Path(__file__).resolve().parents[1] / "test.db"
_TEST_DB.unlink(missing_ok=True)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.bootstrap import init_db_dev  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Empresa, Role, User  # noqa: E402

TEST_EMAIL = "test.admin@taller.app"
TEST_PASSWORD = "secret1234"


@pytest.fixture(scope="session", autouse=True)
def _prepare_db():
    init_db_dev()
    with SessionLocal() as db:
        role = db.scalar(select(Role).where(Role.code == "admin"))
        assert role is not None
        empresa = Empresa(codigo="TEST", nombre="Empresa de prueba")
        db.add(empresa)
        db.flush()
        db.add(
            User(
                email=TEST_EMAIL,
                password_hash=hash_password(TEST_PASSWORD),
                full_name="Test Admin",
                role_id=role.id,
                empresa_id=empresa.id,
            )
        )
        db.commit()
    yield
    Base.metadata.drop_all(engine)
    engine.dispose()
    _TEST_DB.unlink(missing_ok=True)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
