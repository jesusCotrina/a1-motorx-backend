import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import require_empresa
from app.core.periodo import rango_mes
from app.core.ventas_totales import (
    cantidad_ventas,
    saldo_por_cobrar,
    total_ventas,
    total_ventas_producto,
)
from app.db.session import get_db
from app.models.gasto import Gasto
from app.models.historico import HistoricoMantenimiento, HistoricoReparacion
from app.models.orden_trabajo import OrdenTrabajo
from app.models.producto import Producto
from app.schemas.resumen import (
    IngresoPorTipoItem,
    InventarioMiniOut,
    OrdenesEstadoOut,
    ResumenGastosOut,
    ResumenOut,
    ResumenSerieItem,
    ResumenVentasOut,
)

router = APIRouter()

BAJO_STOCK_UMBRAL = 10


def _total_gastos(db: Session, empresa_id: uuid.UUID, inicio, fin) -> Decimal:
    return (
        db.scalar(
            select(func.coalesce(func.sum(Gasto.costo_total), 0)).where(
                Gasto.empresa_id == empresa_id, Gasto.fecha >= inicio, Gasto.fecha < fin
            )
        )
        or Decimal(0)
    )


def _total_historico(
    modelo, columna_fecha, db: Session, empresa_id: uuid.UUID, inicio, fin
) -> Decimal:
    return (
        db.scalar(
            select(func.coalesce(func.sum(modelo.costo), 0)).where(
                modelo.empresa_id == empresa_id, columna_fecha >= inicio, columna_fecha < fin
            )
        )
        or Decimal(0)
    )


def _variacion_pct(actual: Decimal, anterior: Decimal) -> Decimal | None:
    if anterior == 0:
        return None
    return (actual - anterior) / anterior * Decimal(100)


def _periodos_previos(periodo: str, cantidad: int) -> list[str]:
    anio, mes = (int(p) for p in periodo.split("-"))
    periodos = []
    for _ in range(cantidad):
        periodos.append(f"{anio:04d}-{mes:02d}")
        mes -= 1
        if mes == 0:
            mes = 12
            anio -= 1
    return list(reversed(periodos))


def _conteo_ordenes_por_estado(
    db: Session, empresa_id: uuid.UUID, inicio, fin
) -> OrdenesEstadoOut:
    orden_ids = list(
        db.scalars(
            select(OrdenTrabajo.id).where(
                OrdenTrabajo.empresa_id == empresa_id,
                OrdenTrabajo.fecha >= inicio,
                OrdenTrabajo.fecha < fin,
            )
        )
    )
    if not orden_ids:
        return OrdenesEstadoOut(pendientes=0, pagadas=0)

    pagado_por_orden = dict.fromkeys(orden_ids, True)
    for modelo in (HistoricoMantenimiento, HistoricoReparacion):
        filas = db.execute(
            select(modelo.orden_trabajo_id, modelo.costo, modelo.pago_cliente).where(
                modelo.orden_trabajo_id.in_(orden_ids)
            )
        )
        for orden_id, costo, pago in filas:
            if pago < (costo or Decimal("0")):
                pagado_por_orden[orden_id] = False

    pagadas = sum(1 for v in pagado_por_orden.values() if v)
    return OrdenesEstadoOut(pendientes=len(orden_ids) - pagadas, pagadas=pagadas)


@router.get("", response_model=ResumenOut)
def resumen(
    mes: str | None = None,
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> ResumenOut:
    periodo, inicio, fin = rango_mes(mes)
    _, p_inicio, p_fin = rango_mes(_periodos_previos(periodo, 2)[0])

    total_v = total_ventas(db, empresa_id, inicio, fin)
    total_g = _total_gastos(db, empresa_id, inicio, fin)
    cantidad_v = cantidad_ventas(db, empresa_id, inicio, fin)
    saldo_cobrar = saldo_por_cobrar(db, empresa_id, inicio, fin)
    utilidad = total_v - total_g
    cantidad_g = (
        db.scalar(
            select(func.count()).where(
                Gasto.empresa_id == empresa_id, Gasto.fecha >= inicio, Gasto.fecha < fin
            )
        )
        or 0
    )
    total_ordenes = (
        db.scalar(
            select(func.count()).where(
                OrdenTrabajo.empresa_id == empresa_id,
                OrdenTrabajo.fecha >= inicio,
                OrdenTrabajo.fecha < fin,
            )
        )
        or 0
    )

    total_v_ant = total_ventas(db, empresa_id, p_inicio, p_fin)
    total_g_ant = _total_gastos(db, empresa_id, p_inicio, p_fin)
    saldo_cobrar_ant = saldo_por_cobrar(db, empresa_id, p_inicio, p_fin)
    total_ordenes_ant = (
        db.scalar(
            select(func.count()).where(
                OrdenTrabajo.empresa_id == empresa_id,
                OrdenTrabajo.fecha >= p_inicio,
                OrdenTrabajo.fecha < p_fin,
            )
        )
        or 0
    )

    serie_mensual = []
    for p in _periodos_previos(periodo, 6):
        _, s_inicio, s_fin = rango_mes(p)
        serie_mensual.append(
            ResumenSerieItem(
                periodo=p,
                ventas=total_ventas(db, empresa_id, s_inicio, s_fin),
                gastos=_total_gastos(db, empresa_id, s_inicio, s_fin),
            )
        )

    total_mant = _total_historico(
        HistoricoMantenimiento,
        HistoricoMantenimiento.fec_mantenimiento,
        db,
        empresa_id,
        inicio,
        fin,
    )
    total_rep = _total_historico(
        HistoricoReparacion, HistoricoReparacion.fec_reparacion, db, empresa_id, inicio, fin
    )
    total_prod = total_ventas_producto(db, empresa_id, inicio, fin)

    total_productos = (
        db.scalar(
            select(func.count()).select_from(Producto).where(Producto.empresa_id == empresa_id)
        )
        or 0
    )
    bajo_stock = (
        db.scalar(
            select(func.count())
            .select_from(Producto)
            .where(Producto.empresa_id == empresa_id, Producto.stock_actual < BAJO_STOCK_UMBRAL)
        )
        or 0
    )

    return ResumenOut(
        periodo=periodo,
        ventas=ResumenVentasOut(
            cantidad=cantidad_v,
            total=total_v,
            cobrado=total_v - saldo_cobrar,
        ),
        gastos=ResumenGastosOut(cantidad=cantidad_g, total=total_g),
        utilidad=utilidad,
        saldo_por_cobrar=saldo_cobrar,
        total_ordenes_trabajo=total_ordenes,
        serie_mensual=serie_mensual,
        variacion_ventas_pct=_variacion_pct(total_v, total_v_ant),
        variacion_gastos_pct=_variacion_pct(total_g, total_g_ant),
        variacion_utilidad_pct=_variacion_pct(utilidad, total_v_ant - total_g_ant),
        variacion_saldo_por_cobrar_pct=_variacion_pct(saldo_cobrar, saldo_cobrar_ant),
        variacion_ordenes_pct=_variacion_pct(Decimal(total_ordenes), Decimal(total_ordenes_ant)),
        ingresos_por_tipo=[
            IngresoPorTipoItem(etiqueta="Mantenimiento", monto=total_mant),
            IngresoPorTipoItem(etiqueta="Reparación", monto=total_rep),
            IngresoPorTipoItem(etiqueta="Ventas", monto=total_prod),
        ],
        ordenes_trabajo=_conteo_ordenes_por_estado(db, empresa_id, inicio, fin),
        inventario=InventarioMiniOut(total_productos=total_productos, bajo_stock=bajo_stock),
    )
