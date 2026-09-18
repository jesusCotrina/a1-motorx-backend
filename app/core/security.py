from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(
    subject: str, expires_delta: timedelta, token_type: str, extra: dict | None = None
) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        **(extra or {}),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str) -> str:
    return _create_token(
        subject,
        timedelta(minutes=settings.access_token_expire_minutes),
        "access",
    )


def create_refresh_token(subject: str, recordado: bool = False) -> str:
    """El refresh token lleva su propio flag 'recordado': al refrescar
    (POST /auth/refresh) se reemite con la misma duracion extendida sin que
    el cliente tenga que volver a mandar la casilla 'Recuerdame', para que
    una sesion recordada se mantenga recordada mientras se siga usando."""
    dias = (
        settings.refresh_token_expire_days_recordado
        if recordado
        else settings.refresh_token_expire_days
    )
    return _create_token(
        subject, timedelta(days=dias), "refresh", extra={"recordado": recordado}
    )


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except JWTError:
        return None
