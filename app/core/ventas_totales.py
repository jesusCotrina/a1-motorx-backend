"""Ventas de producto (Ventas/Inventario) y ventas por servicio (cada
mantenimiento y cada reparacion de una orden de trabajo) combinadas para
Cuentas, Resumen y Reportes: un mantenimiento o una reparacion es, para
efectos de reportes financieros, un tipo de venta mas (no un concepto
aparte). Se centraliza aqui en vez de duplicarlo en cada endpoint porque
los tres modulos necesitan exactamente el mismo criterio."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.historico import HistoricoMantenimiento, HistoricoReparacion
from app.models.venta import CobroVenta, Venta
from app.schemas.cuenta import CuentaPorCobrarItem, EntradaCajaItem, IngresoItem


def total_ventas_producto(db: Session, empresa_id: uuid.UUID, inicio: date, fin: date) -> Decimal:
    return (
        db.scalar(
            select(func.coalesce(func.sum(Venta.total_soles), 0)).where(
                Venta.empresa_id == empresa_id, Venta.fecha >= inicio, Venta.fecha < fin
            )
        )
        or Decimal(0)
    )


def _total_servicio(
    model, columna_fecha, db: Session, empresa_id: uuid.UUID, inicio, fin
) -> Decimal:
    return (
        db.scalar(
            select(func.coalesce(func.sum(model.costo), 0)).where(
                model.empresa_id == empresa_id,
                columna_fecha >= inicio,
                columna_fecha < fin,
            )
        )
        or Decimal(0)
    )


def total_ventas_servicio(db: Session, empresa_id: uuid.UUID, inicio: date, fin: date) -> Decimal:
    mant = _total_servicio(
        HistoricoMantenimiento,
        HistoricoMantenimiento.fec_mantenimiento,
        db,
        empresa_id,
        inicio,
        fin,
    )
    rep = _total_servicio(
        HistoricoReparacion, HistoricoReparacion.fec_reparacion, db, empresa_id, inicio, fin
    )
    return mant + rep


def total_ventas(db: Session, empresa_id: uuid.UUID, inicio: date, fin: date) -> Decimal:
    return total_ventas_producto(db, empresa_id, inicio, fin) + total_ventas_servicio(
        db, empresa_id, inicio, fin
    )


def cantidad_ventas(db: Session, empresa_id: uuid.UUID, inicio: date, fin: date) -> int:
    cantidad_producto = (
        db.scalar(
            select(func.count()).where(
                Venta.empresa_id == empresa_id, Venta.fecha >= inicio, Venta.fecha < fin
            )
        )
        or 0
    )
    cantidad_mant = (
        db.scalar(
            select(func.count())
            .select_from(HistoricoMantenimiento)
            .where(
                HistoricoMantenimiento.empresa_id == empresa_id,
                HistoricoMantenimiento.fec_mantenimiento >= inicio,
                HistoricoMantenimiento.fec_mantenimiento < fin,
            )
        )
        or 0
    )
    cantidad_rep = (
        db.scalar(
            select(func.count())
            .select_from(HistoricoReparacion)
            .where(
                HistoricoReparacion.empresa_id == empresa_id,
                HistoricoReparacion.fec_reparacion >= inicio,
                HistoricoReparacion.fec_reparacion < fin,
            )
        )
        or 0
    )
    return cantidad_producto + cantidad_mant + cantidad_rep


def _ventas_producto_pendientes(
    db: Session, empresa_id: uuid.UUID, inicio: date, fin: date
) -> list[CuentaPorCobrarItem]:
    ventas = db.scalars(
        select(Venta).where(
            Venta.empresa_id == empresa_id, Venta.fecha >= inicio, Venta.fecha < fin
        )
    )
    items = []
    for v in ventas:
        abonado = v.monto_abonado or Decimal(0)
        saldo = v.total_soles - abonado
        if saldo <= 0:
            continue
        items.append(
            CuentaPorCobrarItem(
                origen_id=v.id,
                fecha=v.fecha,
                titulo=v.cliente_nombre or v.cliente_documento or "Cliente sin nombre",
                subtitulo=f"Vendedor: {v.vendedor.full_name} · Venta de producto",
                total=v.total_soles,
                abonado=abonado,
                saldo=saldo,
            )
        )
    return items


def _servicio_pendientes(
    model, columna_fecha, etiqueta: str, db: Session, empresa_id: uuid.UUID, inicio, fin
) -> list[CuentaPorCobrarItem]:
    filas = db.scalars(
        select(model).where(
            model.empresa_id == empresa_id, columna_fecha >= inicio, columna_fecha < fin
        )
    )
    items = []
    for f in filas:
        costo = f.costo or Decimal(0)
        saldo = costo - f.pago_cliente
        if saldo <= 0:
            continue
        cliente = f.vehiculo.cliente
        items.append(
            CuentaPorCobrarItem(
                origen_id=f.id,
                fecha=getattr(f, columna_fecha.key),
                titulo=f"{cliente.nombres} {cliente.apellidos}".strip(),
                subtitulo=f"{etiqueta} · Placa {f.vehiculo.placa}",
                total=costo,
                abonado=f.pago_cliente,
                saldo=saldo,
            )
        )
    return items


def ventas_pendientes_detalle(
    db: Session, empresa_id: uuid.UUID, inicio: date, fin: date
) -> list[CuentaPorCobrarItem]:
    items = _ventas_producto_pendientes(db, empresa_id, inicio, fin)
    items += _servicio_pendientes(
        HistoricoMantenimiento,
        HistoricoMantenimiento.fec_mantenimiento,
        "Mantenimiento",
        db,
        empresa_id,
        inicio,
        fin,
    )
    items += _servicio_pendientes(
        HistoricoReparacion,
        HistoricoReparacion.fec_reparacion,
        "Reparación",
        db,
        empresa_id,
        inicio,
        fin,
    )
    items.sort(key=lambda i: i.fecha, reverse=True)
    return items


def saldo_por_cobrar(db: Session, empresa_id: uuid.UUID, inicio: date, fin: date) -> Decimal:
    items = ventas_pendientes_detalle(db, empresa_id, inicio, fin)
    return sum((i.saldo for i in items), Decimal(0))


def ingresos_caja(db: Session, empresa_id: uuid.UUID, inicio: date, fin: date) -> Decimal:
    """Entradas de caja: para ventas de producto, lo realmente cobrado en el
    periodo (segun la fecha de cada cobro, no la de la venta -- ver
    CobroVenta); para servicios (mantenimiento/reparacion) no se rastrea un
    cobro con fecha propia, asi que se reconoce el pago en la fecha del
    propio item."""
    cobros_producto = (
        db.scalar(
            select(func.coalesce(func.sum(CobroVenta.monto), 0))
            .select_from(CobroVenta)
            .join(Venta, CobroVenta.venta_id == Venta.id)
            .where(
                Venta.empresa_id == empresa_id,
                CobroVenta.fecha >= inicio,
                CobroVenta.fecha < fin,
            )
        )
        or Decimal(0)
    )
    pago_mant = (
        db.scalar(
            select(func.coalesce(func.sum(HistoricoMantenimiento.pago_cliente), 0)).where(
                HistoricoMantenimiento.empresa_id == empresa_id,
                HistoricoMantenimiento.fec_mantenimiento >= inicio,
                HistoricoMantenimiento.fec_mantenimiento < fin,
            )
        )
        or Decimal(0)
    )
    pago_rep = (
        db.scalar(
            select(func.coalesce(func.sum(HistoricoReparacion.pago_cliente), 0)).where(
                HistoricoReparacion.empresa_id == empresa_id,
                HistoricoReparacion.fec_reparacion >= inicio,
                HistoricoReparacion.fec_reparacion < fin,
            )
        )
        or Decimal(0)
    )
    return cobros_producto + pago_mant + pago_rep


def ingresos_detalle(
    db: Session, empresa_id: uuid.UUID, inicio: date, fin: date
) -> list[IngresoItem]:
    """Detalle de 'Ingresos (ventas)' del Estado de resultados: ventas de
    producto mas ventas por servicio, para el modal que se abre al hacer
    click en esa fila."""
    items = [
        IngresoItem(
            origen_id=v.id,
            fecha=v.fecha,
            titulo=v.cliente_nombre or v.cliente_documento or "Cliente sin nombre",
            subtitulo=f"Vendedor: {v.vendedor.full_name} · Venta de producto",
            monto=v.total_soles,
        )
        for v in db.scalars(
            select(Venta).where(
                Venta.empresa_id == empresa_id, Venta.fecha >= inicio, Venta.fecha < fin
            )
        )
    ]

    for modelo, columna_fecha, etiqueta in (
        (HistoricoMantenimiento, HistoricoMantenimiento.fec_mantenimiento, "Mantenimiento"),
        (HistoricoReparacion, HistoricoReparacion.fec_reparacion, "Reparación"),
    ):
        for item in db.scalars(
            select(modelo).where(
                modelo.empresa_id == empresa_id, columna_fecha >= inicio, columna_fecha < fin
            )
        ):
            cliente = item.vehiculo.cliente
            items.append(
                IngresoItem(
                    origen_id=item.id,
                    fecha=getattr(item, columna_fecha.key),
                    titulo=f"{cliente.nombres} {cliente.apellidos}".strip(),
                    subtitulo=f"{etiqueta} · Placa {item.vehiculo.placa}",
                    monto=item.costo or Decimal(0),
                )
            )

    items.sort(key=lambda i: i.fecha, reverse=True)
    return items


def entradas_caja_detalle(
    db: Session, empresa_id: uuid.UUID, inicio: date, fin: date
) -> list[EntradaCajaItem]:
    filas = db.execute(
        select(CobroVenta, Venta)
        .join(Venta, CobroVenta.venta_id == Venta.id)
        .where(
            Venta.empresa_id == empresa_id, CobroVenta.fecha >= inicio, CobroVenta.fecha < fin
        )
    )
    items = [
        EntradaCajaItem(
            origen_id=venta.id,
            fecha=cobro.fecha,
            titulo=venta.cliente_nombre or venta.cliente_documento or "Cliente sin nombre",
            subtitulo=f"Vendedor: {venta.vendedor.full_name} · Venta {venta.total_soles}",
            monto_cobro=cobro.monto,
        )
        for cobro, venta in filas
    ]

    for m in db.scalars(
        select(HistoricoMantenimiento).where(
            HistoricoMantenimiento.empresa_id == empresa_id,
            HistoricoMantenimiento.fec_mantenimiento >= inicio,
            HistoricoMantenimiento.fec_mantenimiento < fin,
            HistoricoMantenimiento.pago_cliente > 0,
        )
    ):
        cliente = m.vehiculo.cliente
        items.append(
            EntradaCajaItem(
                origen_id=m.id,
                fecha=m.fec_mantenimiento,
                titulo=f"{cliente.nombres} {cliente.apellidos}".strip(),
                subtitulo=f"Mantenimiento · Placa {m.vehiculo.placa}",
                monto_cobro=m.pago_cliente,
            )
        )
    for r in db.scalars(
        select(HistoricoReparacion).where(
            HistoricoReparacion.empresa_id == empresa_id,
            HistoricoReparacion.fec_reparacion >= inicio,
            HistoricoReparacion.fec_reparacion < fin,
            HistoricoReparacion.pago_cliente > 0,
        )
    ):
        cliente = r.vehiculo.cliente
        items.append(
            EntradaCajaItem(
                origen_id=r.id,
                fecha=r.fec_reparacion,
                titulo=f"{cliente.nombres} {cliente.apellidos}".strip(),
                subtitulo=f"Reparación · Placa {r.vehiculo.placa}",
                monto_cobro=r.pago_cliente,
            )
        )

    items.sort(key=lambda i: i.fecha, reverse=True)
    return items
