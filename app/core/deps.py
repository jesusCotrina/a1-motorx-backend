import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No autenticado")

    payload = decode_token(creds.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido o expirado")

    try:
        user_id = uuid.UUID(str(payload.get("sub")))
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido") from None

    user = db.get(User, user_id)
    if user is None or not user.is_active or not user.empresa.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario no válido")
    return user


def require_roles(*codes: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role.code not in codes:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Permisos insuficientes"
            )
        return user

    return checker


def require_empresa(user: User = Depends(get_current_user)) -> uuid.UUID:
    """ID de la empresa (tenant) del usuario autenticado.

    Todo usuario (super_admin, admin, mecanico) pertenece a una empresa: no
    hay un rol de plataforma sin tenant.
    """
    return user.empresa_id
