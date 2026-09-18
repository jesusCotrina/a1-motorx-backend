import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.models.gasto import Gasto, TipoGasto

CategoriaGasto = Literal["operativo", "financiero_ingreso", "financiero_egreso"]


class TipoGastoOut(BaseModel):
    id: uuid.UUID
    nombre: str
    categoria: CategoriaGasto

    @classmethod
    def from_model(cls, t: TipoGasto) -> "TipoGastoOut":
        return cls(id=t.id, nombre=t.nombre, categoria=t.categoria)


class TipoGastoCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    categoria: CategoriaGasto = "operativo"


class GastoItemCreate(BaseModel):
    tipo_gasto_id: uuid.UUID
    comprobante: str | None = None
    proveedor_colaborador: str | None = None
    metodo_pago: str = Field(min_length=1, max_length=40)
    costo_total: Decimal
    monto_pagado: Decimal | None = None
    """Si no se especifica, se asume pagado por completo (= costo_total)."""
    aplica_credito_fiscal: bool = True


class GastosCreate(BaseModel):
    gastos: list[GastoItemCreate] = Field(min_length=1)


class GastoOut(BaseModel):
    id: uuid.UUID
    fecha: date
    tipo_gasto_id: uuid.UUID
    tipo_gasto_nombre: str
    categoria: CategoriaGasto
    comprobante: str | None
    proveedor_colaborador: str | None
    metodo_pago: str
    costo_total: Decimal
    monto_pagado: Decimal
    aplica_credito_fiscal: bool
    creado_por: str

    @classmethod
    def from_model(cls, g: Gasto) -> "GastoOut":
        return cls(
            id=g.id,
            fecha=g.fecha,
            tipo_gasto_id=g.tipo_gasto_id,
            tipo_gasto_nombre=g.tipo_gasto.nombre,
            categoria=g.tipo_gasto.categoria,
            comprobante=g.comprobante,
            proveedor_colaborador=g.proveedor_colaborador,
            metodo_pago=g.metodo_pago,
            costo_total=g.costo_total,
            monto_pagado=g.monto_pagado,
            aplica_credito_fiscal=g.aplica_credito_fiscal,
            creado_por=g.usuario.full_name,
        )
