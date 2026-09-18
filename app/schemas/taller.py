import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.models.historico import HistoricoMantenimiento, HistoricoReparacion
from app.models.orden_trabajo import OrdenTrabajo
from app.models.vehiculo import Vehiculo
from app.schemas.cliente import ClienteOut

EstadoPago = Literal["pagado", "pendiente"]


def _estado_pago(costo: Decimal | None, pago_cliente: Decimal) -> EstadoPago:
    return "pagado" if pago_cliente >= (costo or Decimal("0")) else "pendiente"


class VehiculoOut(BaseModel):
    id: uuid.UUID
    placa: str
    marca: str | None
    modelo: str | None
    carroceria: str | None
    num_motor: str | None
    vin_serie: str | None
    cliente: ClienteOut

    @classmethod
    def from_model(cls, vehiculo: Vehiculo) -> "VehiculoOut":
        return cls(
            id=vehiculo.id,
            placa=vehiculo.placa,
            marca=vehiculo.marca,
            modelo=vehiculo.modelo,
            carroceria=vehiculo.carroceria,
            num_motor=vehiculo.num_motor,
            vin_serie=vehiculo.vin_serie,
            cliente=ClienteOut.from_model(vehiculo.cliente),
        )


class VehiculoResumenOut(BaseModel):
    """Version minima de un vehiculo: solo placa y marca (para listarlo bajo
    la ficha de un cliente, que puede tener varios)."""

    id: uuid.UUID
    placa: str
    marca: str | None

    @classmethod
    def from_model(cls, vehiculo: Vehiculo) -> "VehiculoResumenOut":
        return cls(id=vehiculo.id, placa=vehiculo.placa, marca=vehiculo.marca)


class VehiculoCreate(BaseModel):
    placa: str
    marca: str | None = None
    modelo: str | None = None
    carroceria: str | None = None
    num_motor: str | None = None
    vin_serie: str | None = None
    tip_documento: str
    """Documento del dueno: se usa para resolver el cliente ya existente."""
    num_documento: str


class VehiculoUpdate(VehiculoCreate):
    pass


class HistoricoMantenimientoOut(BaseModel):
    id: uuid.UUID
    placa: str
    fec_mantenimiento: date
    kilometraje: int
    tipo_mantenimiento: str
    cambios_realizados: list[str]
    nota: str | None
    costo: Decimal | None
    pago_cliente: Decimal
    estado: EstadoPago
    creado_por: str

    @classmethod
    def from_model(cls, h: HistoricoMantenimiento) -> "HistoricoMantenimientoOut":
        return cls(
            id=h.id,
            placa=h.vehiculo.placa,
            fec_mantenimiento=h.fec_mantenimiento,
            kilometraje=h.kilometraje,
            tipo_mantenimiento=h.tipo_mantenimiento,
            cambios_realizados=h.cambios_realizados,
            nota=h.nota,
            costo=h.costo,
            pago_cliente=h.pago_cliente,
            estado=_estado_pago(h.costo, h.pago_cliente),
            creado_por=h.usuario.full_name,
        )


class HistoricoReparacionOut(BaseModel):
    id: uuid.UUID
    placa: str
    fec_reparacion: date
    kilometraje: int
    reparaciones_realizadas: list[str]
    nota: str | None
    costo: Decimal | None
    pago_cliente: Decimal
    estado: EstadoPago
    creado_por: str

    @classmethod
    def from_model(cls, h: HistoricoReparacion) -> "HistoricoReparacionOut":
        return cls(
            id=h.id,
            placa=h.vehiculo.placa,
            fec_reparacion=h.fec_reparacion,
            kilometraje=h.kilometraje,
            reparaciones_realizadas=h.reparaciones_realizadas,
            nota=h.nota,
            costo=h.costo,
            pago_cliente=h.pago_cliente,
            estado=_estado_pago(h.costo, h.pago_cliente),
            creado_por=h.usuario.full_name,
        )


class HistoricoMantenimientoUpdate(BaseModel):
    fec_mantenimiento: date
    kilometraje: int
    tipo_mantenimiento: str
    cambios_realizados: list[str]
    nota: str | None = None
    costo: Decimal | None = None
    pago_cliente: Decimal = Decimal("0")


class HistoricoReparacionUpdate(BaseModel):
    fec_reparacion: date
    kilometraje: int
    reparaciones_realizadas: list[str]
    nota: str | None = None
    costo: Decimal | None = None
    pago_cliente: Decimal = Decimal("0")


class TipoMantenimientoOut(BaseModel):
    id: uuid.UUID
    categoria: str
    nombre: str


class TipoMantenimientoCreate(BaseModel):
    categoria: str
    nombre: str


class TipoReparacionOut(BaseModel):
    id: uuid.UUID
    nombre: str


class TipoReparacionCreate(BaseModel):
    nombre: str


class ItemMantenimientoCreate(BaseModel):
    fec_mantenimiento: date
    kilometraje: int
    tipo_mantenimiento: str
    """Nivel de servicio (p.ej. Basico/Intermedio/Completo): la 'categoria'
    del catalogo tipos_mantenimiento."""
    cambio_realizado: str
    """El 'nombre' del catalogo tipos_mantenimiento; se guarda como lista de
    un solo elemento en cambios_realizados para no migrar esa columna."""
    nota: str | None = None
    costo: Decimal | None = None
    pago_cliente: Decimal = Decimal("0")


class ItemReparacionCreate(BaseModel):
    fec_reparacion: date
    kilometraje: int
    trabajo_realizado: str
    """El 'nombre' del catalogo tipos_reparacion (guardado igual que antes
    en reparaciones_realizadas, como lista de un solo elemento)."""
    nota: str | None = None
    costo: Decimal | None = None
    pago_cliente: Decimal = Decimal("0")


class OrdenTrabajoCreate(BaseModel):
    placa: str
    mantenimientos: list[ItemMantenimientoCreate] = []
    reparaciones: list[ItemReparacionCreate] = []


class OrdenTrabajoOut(BaseModel):
    id: uuid.UUID
    placa: str
    cliente_nombre: str
    fecha: date
    mantenimientos: list[HistoricoMantenimientoOut]
    reparaciones: list[HistoricoReparacionOut]
    costo_total: Decimal
    pago_total: Decimal
    estado: EstadoPago
    creado_por: str

    @classmethod
    def from_model(
        cls,
        orden: OrdenTrabajo,
        mantenimientos: list[HistoricoMantenimiento],
        reparaciones: list[HistoricoReparacion],
    ) -> "OrdenTrabajoOut":
        items_mant = [HistoricoMantenimientoOut.from_model(m) for m in mantenimientos]
        items_rep = [HistoricoReparacionOut.from_model(r) for r in reparaciones]
        costo_total = sum((i.costo or Decimal("0") for i in items_mant), Decimal("0")) + sum(
            (i.costo or Decimal("0") for i in items_rep), Decimal("0")
        )
        pago_total = sum((i.pago_cliente for i in items_mant), Decimal("0")) + sum(
            (i.pago_cliente for i in items_rep), Decimal("0")
        )
        todos_pagados = all(i.estado == "pagado" for i in items_mant + items_rep)
        cliente = orden.vehiculo.cliente
        return cls(
            id=orden.id,
            placa=orden.vehiculo.placa,
            cliente_nombre=f"{cliente.nombres} {cliente.apellidos}",
            fecha=orden.fecha,
            mantenimientos=items_mant,
            reparaciones=items_rep,
            costo_total=costo_total,
            pago_total=pago_total,
            estado="pagado" if todos_pagados else "pendiente",
            creado_por=orden.usuario.full_name,
        )


class ResumenOrdenesOut(BaseModel):
    total_ordenes: int
    total_mantenimientos: int
    total_reparaciones: int
    venta_total: Decimal
    venta_por_cobrar: Decimal
