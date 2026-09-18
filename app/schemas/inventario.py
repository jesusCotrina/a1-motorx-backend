import uuid
from decimal import Decimal

from pydantic import BaseModel, Field


class IngresoInventarioCreate(BaseModel):
    producto_id: uuid.UUID
    unidades: int = Field(gt=0)


class VentasMesOut(BaseModel):
    mes: str
    """YYYY-MM del mes consultado."""
    cantidad: int
    total_soles: Decimal


class GastosMesOut(BaseModel):
    mes: str
    """YYYY-MM del mes consultado."""
    cantidad: int
    total_soles: Decimal


class ResumenInventarioOut(BaseModel):
    total_productos: int
    total_proveedores: int
    total_stock_unidades: int
    ventas_mes: VentasMesOut
    gastos_mes: GastosMesOut
