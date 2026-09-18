import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.venta import DetalleVenta, Venta


class VendedorOut(BaseModel):
    id: uuid.UUID
    full_name: str
    num_documento: str | None


class VentasTotalesOut(BaseModel):
    cantidad: int
    total_soles: Decimal
    total_pagado_soles: Decimal


class DetalleVentaInput(BaseModel):
    producto_id: uuid.UUID
    unidades: int = Field(gt=0)


class DetalleVentaOut(BaseModel):
    producto_id: uuid.UUID
    producto_nombre: str
    producto_sku: str
    unidades: int
    precio_unitario: Decimal
    subtotal: Decimal

    @classmethod
    def from_model(cls, d: DetalleVenta) -> "DetalleVentaOut":
        return cls(
            producto_id=d.producto_id,
            producto_nombre=d.producto.nombre,
            producto_sku=d.producto.sku,
            unidades=d.unidades,
            precio_unitario=d.precio_unitario,
            subtotal=d.subtotal,
        )


class CobroVentaIn(BaseModel):
    monto: Decimal = Field(ge=0)
    """Cuanto se cobra ahora (no el nuevo total abonado): se suma al
    monto_abonado existente, y se registra con la fecha de hoy para que el
    Flujo de caja lo cuente en las entradas del mes en que se cobra."""


class VentaCreate(BaseModel):
    fecha: date
    vendedor_id: uuid.UUID
    cliente_documento: str | None = None
    cliente_nombre: str | None = None
    flete: Decimal = Decimal(0)
    envio: Decimal = Decimal(0)
    monto_abonado: Decimal | None = None
    observacion: str | None = None
    metodo_pago: str = Field(min_length=1, max_length=40)
    tipo_entrega: str = Field(min_length=1, max_length=40)
    tipo_comprobante: str = Field(min_length=1, max_length=40)
    detalles: list[DetalleVentaInput] = Field(min_length=1)


class VentaOut(BaseModel):
    id: uuid.UUID
    fecha: date
    vendedor_id: uuid.UUID
    vendedor_nombre: str
    cliente_documento: str | None
    cliente_nombre: str | None
    flete: Decimal
    envio: Decimal
    monto_abonado: Decimal | None
    observacion: str | None
    metodo_pago: str
    tipo_entrega: str
    tipo_comprobante: str
    total_soles: Decimal
    detalles: list[DetalleVentaOut]

    @classmethod
    def from_model(cls, v: Venta) -> "VentaOut":
        return cls(
            id=v.id,
            fecha=v.fecha,
            vendedor_id=v.vendedor_id,
            vendedor_nombre=v.vendedor.full_name,
            cliente_documento=v.cliente_documento,
            cliente_nombre=v.cliente_nombre,
            flete=v.flete,
            envio=v.envio,
            monto_abonado=v.monto_abonado,
            observacion=v.observacion,
            metodo_pago=v.metodo_pago,
            tipo_entrega=v.tipo_entrega,
            tipo_comprobante=v.tipo_comprobante,
            total_soles=v.total_soles,
            detalles=[DetalleVentaOut.from_model(d) for d in v.detalles],
        )
