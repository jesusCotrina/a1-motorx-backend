import uuid
from datetime import date

from pydantic import BaseModel

from app.models.cliente import Cliente


class ClienteOut(BaseModel):
    id: uuid.UUID
    tip_documento: str
    num_documento: str
    nombres: str
    apellidos: str
    correo: str | None
    telefono: str | None
    fec_nacimiento: date | None

    @classmethod
    def from_model(cls, cliente: Cliente) -> "ClienteOut":
        return cls(
            id=cliente.id,
            tip_documento=cliente.tip_documento,
            num_documento=cliente.num_documento,
            nombres=cliente.nombres,
            apellidos=cliente.apellidos,
            correo=cliente.correo,
            telefono=cliente.telefono,
            fec_nacimiento=cliente.fec_nacimiento,
        )


class ClienteCreate(BaseModel):
    tip_documento: str
    num_documento: str
    nombres: str
    apellidos: str
    correo: str | None = None
    telefono: str | None = None
    fec_nacimiento: date | None = None


class ClienteUpdate(ClienteCreate):
    pass
