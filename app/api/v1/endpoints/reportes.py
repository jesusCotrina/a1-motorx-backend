import calendar
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import require_empresa, require_roles
from app.core.periodo import rango_mes
from app.db.session import get_db
from app.models.historico import HistoricoMantenimiento, HistoricoReparacion
from app.models.orden_trabajo import OrdenTrabajo
from app.models.producto import Producto
from app.models.user import User
from app.models.venta import DetalleVenta, Venta
from app.schemas.reportes import (
    ClienteTopItem,
    EtiquetaMontoItem,
    ProductoTopItem,
    VendedorVentaItem,
    VentaDiariaItem,
)

router = APIRouter(dependencies=[Depends(require_roles("admin", "super_admin"))])


@router.get("/ventas-diarias", response_model=list[VentaDiariaItem])
def ventas_diarias(
    mes: str | None = None,
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[VentaDiariaItem]:
    """Total vendido de cada dia del mes (con ceros en los dias sin venta):
    ventas de producto mas ventas por servicio (mantenimiento/reparacion)."""
    _, inicio, fin = rango_mes(mes)
    totales_por_dia: dict[int, Decimal] = {}

    filas = db.execute(
        select(func.extract("day", Venta.fecha), func.coalesce(func.sum(Venta.total_soles), 0))
        .where(Venta.empresa_id == empresa_id, Venta.fecha >= inicio, Venta.fecha < fin)
        .group_by(func.extract("day", Venta.fecha))
    ).all()
    for dia, total in filas:
        totales_por_dia[int(dia)] = totales_por_dia.get(int(dia), Decimal(0)) + Decimal(total)

    for modelo, columna_fecha in (
        (HistoricoMantenimiento, HistoricoMantenimiento.fec_mantenimiento),
        (HistoricoReparacion, HistoricoReparacion.fec_reparacion),
    ):
        filas = db.execute(
            select(func.extract("day", columna_fecha), func.coalesce(func.sum(modelo.costo), 0))
            .where(modelo.empresa_id == empresa_id, columna_fecha >= inicio, columna_fecha < fin)
            .group_by(func.extract("day", columna_fecha))
        ).all()
        for dia, total in filas:
            totales_por_dia[int(dia)] = totales_por_dia.get(int(dia), Decimal(0)) + Decimal(total)

    _, dias_del_mes = calendar.monthrange(inicio.year, inicio.month)
    return [
        VentaDiariaItem(dia=d, total=totales_por_dia.get(d, Decimal(0)))
        for d in range(1, dias_del_mes + 1)
    ]


@router.get("/ventas-por-vendedor", response_model=list[VendedorVentaItem])
def ventas_por_vendedor(
    mes: str | None = None,
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[VendedorVentaItem]:
    """Ventas de producto mas ventas por servicio, por vendedor/mecanico
    (quien registro la venta, o quien registro el mantenimiento/reparacion)."""
    _, inicio, fin = rango_mes(mes)
    totales: dict[str, Decimal] = {}

    filas = db.execute(
        select(User.full_name, func.coalesce(func.sum(Venta.total_soles), 0))
        .select_from(Venta)
        .join(User, Venta.vendedor_id == User.id)
        .where(Venta.empresa_id == empresa_id, Venta.fecha >= inicio, Venta.fecha < fin)
        .group_by(User.full_name)
    ).all()
    for nombre, total in filas:
        totales[nombre] = totales.get(nombre, Decimal(0)) + Decimal(total)

    for modelo, columna_fecha, usuario_fk in (
        (
            HistoricoMantenimiento,
            HistoricoMantenimiento.fec_mantenimiento,
            HistoricoMantenimiento.usuario_id,
        ),
        (HistoricoReparacion, HistoricoReparacion.fec_reparacion, HistoricoReparacion.usuario_id),
    ):
        filas = db.execute(
            select(User.full_name, func.coalesce(func.sum(modelo.costo), 0))
            .select_from(modelo)
            .join(User, usuario_fk == User.id)
            .where(modelo.empresa_id == empresa_id, columna_fecha >= inicio, columna_fecha < fin)
            .group_by(User.full_name)
        ).all()
        for nombre, total in filas:
            totales[nombre] = totales.get(nombre, Decimal(0)) + Decimal(total)

    resultado = [
        VendedorVentaItem(vendedor_nombre=nombre, total=total)
        for nombre, total in totales.items()
        if total > 0
    ]
    resultado.sort(key=lambda i: i.total, reverse=True)
    return resultado


@router.get("/productos-mas-vendidos", response_model=list[ProductoTopItem])
def productos_mas_vendidos(
    mes: str | None = None,
    limit: int = Query(10, ge=1, le=50),
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[ProductoTopItem]:
    _, inicio, fin = rango_mes(mes)
    filas = db.execute(
        select(
            Producto.nombre,
            func.coalesce(func.sum(DetalleVenta.unidades), 0),
            func.coalesce(func.sum(DetalleVenta.subtotal), 0),
        )
        .select_from(DetalleVenta)
        .join(Venta, DetalleVenta.venta_id == Venta.id)
        .join(Producto, DetalleVenta.producto_id == Producto.id)
        .where(Venta.empresa_id == empresa_id, Venta.fecha >= inicio, Venta.fecha < fin)
        .group_by(Producto.nombre)
        .order_by(func.sum(DetalleVenta.unidades).desc())
        .limit(limit)
    ).all()
    return [
        ProductoTopItem(producto_nombre=nombre, unidades=unidades, monto=monto)
        for nombre, unidades, monto in filas
    ]


@router.get("/top-clientes", response_model=list[ClienteTopItem])
def top_clientes(
    mes: str | None = None,
    limit: int = Query(10, ge=1, le=50),
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[ClienteTopItem]:
    """Top clientes por ventas de producto mas ventas por servicio."""
    _, inicio, fin = rango_mes(mes)
    totales: dict[str, Decimal] = {}

    etiqueta = func.coalesce(Venta.cliente_nombre, Venta.cliente_documento, "Cliente sin nombre")
    filas = db.execute(
        select(etiqueta, func.coalesce(func.sum(Venta.total_soles), 0))
        .where(Venta.empresa_id == empresa_id, Venta.fecha >= inicio, Venta.fecha < fin)
        .group_by(etiqueta)
    ).all()
    for nombre, total in filas:
        totales[nombre] = totales.get(nombre, Decimal(0)) + Decimal(total)

    for modelo, columna_fecha in (
        (HistoricoMantenimiento, HistoricoMantenimiento.fec_mantenimiento),
        (HistoricoReparacion, HistoricoReparacion.fec_reparacion),
    ):
        filas = db.execute(
            select(modelo)
            .where(modelo.empresa_id == empresa_id, columna_fecha >= inicio, columna_fecha < fin)
        ).scalars()
        for item in filas:
            cliente = item.vehiculo.cliente
            nombre = f"{cliente.nombres} {cliente.apellidos}".strip() or "Cliente sin nombre"
            totales[nombre] = totales.get(nombre, Decimal(0)) + (item.costo or Decimal(0))

    resultado = [
        ClienteTopItem(cliente_nombre=nombre, total=total)
        for nombre, total in totales.items()
        if total > 0
    ]
    resultado.sort(key=lambda i: i.total, reverse=True)
    return resultado[:limit]


@router.get("/ordenes-trabajo-ejecutadas", response_model=int)
def ordenes_trabajo_ejecutadas(
    mes: str | None = None,
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> int:
    _, inicio, fin = rango_mes(mes)
    return (
        db.scalar(
            select(func.count()).where(
                OrdenTrabajo.empresa_id == empresa_id,
                OrdenTrabajo.fecha >= inicio,
                OrdenTrabajo.fecha < fin,
            )
        )
        or 0
    )


def _venta_por_etiqueta(
    modelo, columna_fecha, columna_json, empresa_id: uuid.UUID, inicio, fin, db: Session
) -> list[EtiquetaMontoItem]:
    """Agrupa el costo de items de mantenimiento/reparacion por el primer
    (y, desde el rediseno de ordenes de trabajo, unico) elemento de su
    columna jsonb de cambios/trabajos realizados."""
    etiqueta = columna_json.op("->>")(0)
    filas = db.execute(
        select(etiqueta, func.coalesce(func.sum(modelo.costo), 0))
        .where(modelo.empresa_id == empresa_id, columna_fecha >= inicio, columna_fecha < fin)
        .group_by(etiqueta)
        .order_by(func.sum(modelo.costo).desc())
    ).all()
    return [
        EtiquetaMontoItem(etiqueta=nombre or "Sin especificar", monto=monto)
        for nombre, monto in filas
        if monto and monto > 0
    ]


@router.get("/ventas-por-tipo-mantenimiento", response_model=list[EtiquetaMontoItem])
def ventas_por_tipo_mantenimiento(
    mes: str | None = None,
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[EtiquetaMontoItem]:
    """Venta por 'Tipo de mantenimiento' (nivel de servicio: Basico/
    Intermedio/Completo, ver modulo Mantenimiento)."""
    _, inicio, fin = rango_mes(mes)
    filas = db.execute(
        select(
            HistoricoMantenimiento.tipo_mantenimiento,
            func.coalesce(func.sum(HistoricoMantenimiento.costo), 0),
        )
        .where(
            HistoricoMantenimiento.empresa_id == empresa_id,
            HistoricoMantenimiento.fec_mantenimiento >= inicio,
            HistoricoMantenimiento.fec_mantenimiento < fin,
        )
        .group_by(HistoricoMantenimiento.tipo_mantenimiento)
        .order_by(func.sum(HistoricoMantenimiento.costo).desc())
    ).all()
    return [
        EtiquetaMontoItem(etiqueta=tipo, monto=monto)
        for tipo, monto in filas
        if monto and monto > 0
    ]


@router.get("/ventas-por-cambio-mantenimiento", response_model=list[EtiquetaMontoItem])
def ventas_por_cambio_mantenimiento(
    mes: str | None = None,
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[EtiquetaMontoItem]:
    """Venta por 'Cambio realizado' del mantenimiento."""
    _, inicio, fin = rango_mes(mes)
    return _venta_por_etiqueta(
        HistoricoMantenimiento,
        HistoricoMantenimiento.fec_mantenimiento,
        HistoricoMantenimiento.cambios_realizados,
        empresa_id,
        inicio,
        fin,
        db,
    )


@router.get("/ventas-por-reparacion", response_model=list[EtiquetaMontoItem])
def ventas_por_reparacion(
    mes: str | None = None,
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[EtiquetaMontoItem]:
    """Venta por 'Trabajo realizado' de la reparacion."""
    _, inicio, fin = rango_mes(mes)
    return _venta_por_etiqueta(
        HistoricoReparacion,
        HistoricoReparacion.fec_reparacion,
        HistoricoReparacion.reparaciones_realizadas,
        empresa_id,
        inicio,
        fin,
        db,
    )


@router.get("/ventas-por-trabajo-combinado", response_model=list[EtiquetaMontoItem])
def ventas_por_trabajo_combinado(
    mes: str | None = None,
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[EtiquetaMontoItem]:
    """Union de 'Cambio realizado' (mantenimiento) y 'Trabajo realizado'
    (reparacion) en un solo grafico: cuanto se vendio por cada trabajo,
    sin importar si vino de un mantenimiento o de una reparacion."""
    _, inicio, fin = rango_mes(mes)
    combinado: dict[str, Decimal] = {}
    for item in ventas_por_cambio_mantenimiento(mes=mes, empresa_id=empresa_id, db=db):
        combinado[item.etiqueta] = combinado.get(item.etiqueta, Decimal(0)) + item.monto
    for item in ventas_por_reparacion(mes=mes, empresa_id=empresa_id, db=db):
        combinado[item.etiqueta] = combinado.get(item.etiqueta, Decimal(0)) + item.monto

    resultado = [EtiquetaMontoItem(etiqueta=k, monto=v) for k, v in combinado.items()]
    resultado.sort(key=lambda i: i.monto, reverse=True)
    return resultado
