import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.empresa import Empresa


class EmpresaOut(BaseModel):
    id: uuid.UUID
    codigo: str
    nombre: str
    logo_url: str | None

    @classmethod
    def from_model(cls, empresa: Empresa) -> "EmpresaOut":
        return cls(
            id=empresa.id,
            codigo=empresa.codigo,
            nombre=empresa.nombre,
            logo_url=empresa.logo_url,
        )


class EmpresaAdminOut(BaseModel):
    """Vista de una empresa para el modulo de Administracion (solo super_admin)."""

    id: uuid.UUID
    codigo: str
    nombre: str
    ruc: str | None
    direccion: str | None
    logo_url: str | None
    is_active: bool
    created_at: datetime
    total_usuarios: int
    usuarios_activos: int

    @classmethod
    def from_model(
        cls, empresa: Empresa, total_usuarios: int, usuarios_activos: int
    ) -> "EmpresaAdminOut":
        return cls(
            id=empresa.id,
            codigo=empresa.codigo,
            nombre=empresa.nombre,
            ruc=empresa.ruc,
            direccion=empresa.direccion,
            logo_url=empresa.logo_url,
            is_active=empresa.is_active,
            created_at=empresa.created_at,
            total_usuarios=total_usuarios,
            usuarios_activos=usuarios_activos,
        )


class EmpresaUsuarioCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1)
    password: str = Field(min_length=8)
    role_code: str


class EmpresaCreate(BaseModel):
    codigo: str = Field(min_length=1, max_length=32)
    nombre: str = Field(min_length=1, max_length=120)
    ruc: str | None = None
    direccion: str | None = None
    logo_url: str | None = None
    usuarios: list[EmpresaUsuarioCreate]


class EmpresaUpdate(BaseModel):
    codigo: str = Field(min_length=1, max_length=32)
    nombre: str = Field(min_length=1, max_length=120)
    ruc: str | None = None
    direccion: str | None = None
    logo_url: str | None = None


class EmpresaEstadoUpdate(BaseModel):
    is_active: bool


class EmpresaUsuarioOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role_code: str
    role_name: str
    is_active: bool


class UsuarioEstadoUpdate(BaseModel):
    is_active: bool


class EmpresaUsuarioUpdate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1)
    role_code: str
