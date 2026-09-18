import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class EstadoResultadosOut(BaseModel):
    periodo: str
    ingresos: Decimal
    costo_venta: Decimal
    utilidad_bruta: Decimal
    gastos_operativos: Decimal
    utilidad_operativa: Decimal
    ingresos_financieros: Decimal
    gastos_financieros: Decimal
    utilidad_antes_impuestos: Decimal
    impuesto: Decimal
    utilidad_neta: Decimal


class IngresoItem(BaseModel):
    """Una fila del detalle de 'Ingresos (ventas)' del Estado de resultados:
    una venta de producto, o un mantenimiento/reparacion (venta por
    servicio) del periodo."""

    origen_id: uuid.UUID
    fecha: date
    titulo: str
    subtitulo: str
    monto: Decimal


class CostoVentaItem(BaseModel):
    venta_id: uuid.UUID
    fecha: date
    producto_nombre: str
    unidades: int
    costo_unitario: Decimal
    subtotal_costo: Decimal


class ImpuestoIn(BaseModel):
    mes: str = Field(pattern=r"^\d{4}-\d{2}$")
    monto: Decimal = Field(ge=0)


class FlujoCajaOut(BaseModel):
    periodo: str
    saldo_inicial: Decimal
    ingresos_ventas: Decimal
    compras_y_gastos: Decimal
    saldo_final: Decimal


class SaldoInicialIn(BaseModel):
    mes: str = Field(pattern=r"^\d{4}-\d{2}$")
    monto: Decimal


class EntradaCajaItem(BaseModel):
    origen_id: uuid.UUID
    fecha: date
    """Fecha en que se cobro este monto (no necesariamente la de la venta
    ni la del item de servicio)."""
    titulo: str
    subtitulo: str
    monto_cobro: Decimal


class CuentasCobrarPagarOut(BaseModel):
    periodo: str
    total_ventas: Decimal
    saldo_por_cobrar: Decimal
    saldo_por_pagar: Decimal
    igv_ventas: Decimal
    """Debito fiscal: 18% del total de ventas del periodo (productos +
    servicios: mantenimientos y reparaciones cuentan como venta tambien)."""
    igv_compras: Decimal
    """Credito fiscal: 18% de las compras/gastos operativos del periodo."""
    igv_diferencia: Decimal
    """igv_ventas - igv_compras. Positivo: se debe IGV a SUNAT (por pagar).
    Negativo: hay credito fiscal a favor (SUNAT "debe" IGV, se arrastra al
    siguiente periodo)."""


class CuentaPorCobrarItem(BaseModel):
    origen_id: uuid.UUID
    fecha: date
    titulo: str
    subtitulo: str
    total: Decimal
    abonado: Decimal
    saldo: Decimal


class CuentaPorPagarItem(BaseModel):
    gasto_id: uuid.UUID
    fecha: date
    tipo_gasto_nombre: str
    proveedor_colaborador: str | None
    costo_total: Decimal
    monto_pagado: Decimal
    saldo: Decimal
