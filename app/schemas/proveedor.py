import uuid

from pydantic import BaseModel, Field

from app.models.proveedor import Proveedor


class ProveedorOut(BaseModel):
    id: uuid.UUID
    tip_documento: str
    num_documento: str
    nombre_razon_social: str
    pais: str | None
    telefono: str | None
    email: str | None
    tipo_proveedor: str | None
    observaciones: str | None

    @classmethod
    def from_model(cls, p: Proveedor) -> "ProveedorOut":
        return cls(
            id=p.id,
            tip_documento=p.tip_documento,
            num_documento=p.num_documento,
            nombre_razon_social=p.nombre_razon_social,
            pais=p.pais,
            telefono=p.telefono,
            email=p.email,
            tipo_proveedor=p.tipo_proveedor,
            observaciones=p.observaciones,
        )


class ProveedorCreate(BaseModel):
    tip_documento: str = Field(pattern="^(DNI|RUC)$")
    num_documento: str = Field(min_length=1, max_length=20)
    nombre_razon_social: str = Field(min_length=1, max_length=160)
    pais: str | None = None
    telefono: str | None = None
    email: str | None = None
    tipo_proveedor: str | None = None
    observaciones: str | None = None


class ProveedorUpdate(ProveedorCreate):
    pass
