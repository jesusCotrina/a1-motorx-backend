import uuid

from pydantic import BaseModel, EmailStr

from app.models.user import User
from app.schemas.empresa import EmpresaOut


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: str
    role_name: str
    empresa: EmpresaOut

    @classmethod
    def from_model(cls, user: User) -> "UserOut":
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.code,
            role_name=user.role.name,
            empresa=EmpresaOut.from_model(user.empresa),
        )
