import uuid
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.producto import CategoriaProducto, Producto


class CategoriaProductoOut(BaseModel):
    id: uuid.UUID
    nombre: str

    @classmethod
    def from_model(cls, c: CategoriaProducto) -> "CategoriaProductoOut":
        return cls(id=c.id, nombre=c.nombre)


class CategoriaProductoCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)


class ProductoOut(BaseModel):
    id: uuid.UUID
    sku: str
    nombre: str
    categoria_id: uuid.UUID
    categoria_nombre: str
    precio_venta_soles: Decimal
    costo_soles: Decimal
    stock_actual: int
    descripcion: str | None
    observaciones: str | None

    @classmethod
    def from_model(cls, p: Producto) -> "ProductoOut":
        return cls(
            id=p.id,
            sku=p.sku,
            nombre=p.nombre,
            categoria_id=p.categoria_id,
            categoria_nombre=p.categoria.nombre,
            precio_venta_soles=p.precio_venta_soles,
            costo_soles=p.costo_soles,
            stock_actual=p.stock_actual,
            descripcion=p.descripcion,
            observaciones=p.observaciones,
        )


class ProductoCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=40)
    nombre: str = Field(min_length=1, max_length=160)
    categoria_id: uuid.UUID
    precio_venta_soles: Decimal
    costo_soles: Decimal
    descripcion: str | None = None
    observaciones: str | None = None
    unidades_ingresadas: int = Field(default=0, ge=0)


class ProductoUpdate(BaseModel):
    sku: str = Field(min_length=1, max_length=40)
    nombre: str = Field(min_length=1, max_length=160)
    categoria_id: uuid.UUID
    precio_venta_soles: Decimal
    costo_soles: Decimal
    descripcion: str | None = None
    observaciones: str | None = None
