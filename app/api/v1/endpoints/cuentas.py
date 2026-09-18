import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import require_empresa, require_roles
from app.core.periodo import rango_mes
from app.core.ventas_totales import (
    entradas_caja_detalle,
    ingresos_caja,
    ingresos_detalle,
    saldo_por_cobrar,
    total_ventas,
    ventas_pendientes_detalle,
)
from app.db.session import get_db
from app.models.cuenta import ParametrosCuenta
from app.models.gasto import Gasto, TipoGasto
from app.models.producto import Producto
from app.models.venta import DetalleVenta, Venta
from app.schemas.cuenta import (
    CostoVentaItem,
    CuentaPorCobrarItem,
    CuentaPorPagarItem,
    CuentasCobrarPagarOut,
    EntradaCajaItem,
    EstadoResultadosOut,
    FlujoCajaOut,
    ImpuestoIn,
    IngresoItem,
    SaldoInicialIn,
)

router = APIRouter(dependencies=[Depends(require_roles("admin", "super_admin"))])

IGV_TASA = Decimal("0.18")


def _costo_venta(db: Session, empresa_id: uuid.UUID, inicio, fin) -> Decimal:
    return (
        db.scalar(
            select(func.coalesce(func.sum(DetalleVenta.unidades * Producto.costo_soles), 0))
            .select_from(DetalleVenta)
            .join(Venta, DetalleVenta.venta_id == Venta.id)
            .join(Producto, DetalleVenta.producto_id == Producto.id)
            .where(Venta.empresa_id == empresa_id, Venta.fecha >= inicio, Venta.fecha < fin)
        )
        or Decimal(0)
    )


def _total_gastos(
    db: Session, empresa_id: uuid.UUID, inicio, fin, categoria: str | None
) -> Decimal:
    stmt = select(func.coalesce(func.sum(Gasto.costo_total), 0)).where(
        Gasto.empresa_id == empresa_id, Gasto.fecha >= inicio, Gasto.fecha < fin
    )
    if categoria:
        stmt = stmt.join(TipoGasto).where(TipoGasto.categoria == categoria)
    return db.scalar(stmt) or Decimal(0)


def _total_compras_credito_fiscal(db: Session, empresa_id: uuid.UUID, inicio, fin) -> Decimal:
    """Base para el credito fiscal de IGV: solo los gastos operativos cuyo
    comprobante discrimina IGV (Gasto.aplica_credito_fiscal)."""
    return (
        db.scalar(
            select(func.coalesce(func.sum(Gasto.costo_total), 0))
            .join(TipoGasto)
            .where(
                Gasto.empresa_id == empresa_id,
                Gasto.fecha >= inicio,
                Gasto.fecha < fin,
                Gasto.aplica_credito_fiscal.is_(True),
                TipoGasto.categoria == "operativo",
            )
        )
        or Decimal(0)
    )


def _parametros(db: Session, empresa_id: uuid.UUID, periodo: str) -> ParametrosCuenta:
    parametros = db.get(ParametrosCuenta, (empresa_id, periodo))
    if parametros is None:
        parametros = ParametrosCuenta(empresa_id=empresa_id, periodo=periodo)
        db.add(parametros)
        db.commit()
        db.refresh(parametros)
    return parametros


@router.get("/estado-resultados", response_model=EstadoResultadosOut)
def estado_resultados(
    mes: str | None = None,
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> EstadoResultadosOut:
    periodo, inicio, fin = rango_mes(mes)
    parametros = _parametros(db, empresa_id, periodo)

    ingresos = total_ventas(db, empresa_id, inicio, fin)
    costo_venta = _costo_venta(db, empresa_id, inicio, fin)
    utilidad_bruta = ingresos - costo_venta

    gastos_operativos = _total_gastos(db, empresa_id, inicio, fin, "operativo")
    utilidad_operativa = utilidad_bruta - gastos_operativos

    ingresos_financieros = _total_gastos(db, empresa_id, inicio, fin, "financiero_ingreso")
    gastos_financieros = _total_gastos(db, empresa_id, inicio, fin, "financiero_egreso")
    utilidad_antes_impuestos = utilidad_operativa + ingresos_financieros - gastos_financieros

    utilidad_neta = utilidad_antes_impuestos - parametros.impuesto

    return EstadoResultadosOut(
        periodo=periodo,
        ingresos=ingresos,
        costo_venta=costo_venta,
        utilidad_bruta=utilidad_bruta,
        gastos_operativos=gastos_operativos,
        utilidad_operativa=utilidad_operativa,
        ingresos_financieros=ingresos_financieros,
        gastos_financieros=gastos_financieros,
        utilidad_antes_impuestos=utilidad_antes_impuestos,
        impuesto=parametros.impuesto,
        utilidad_neta=utilidad_neta,
    )


@router.get("/estado-resultados/ingresos", response_model=list[IngresoItem])
def ingresos_estado_resultados(
    mes: str | None = None,
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[IngresoItem]:
    _, inicio, fin = rango_mes(mes)
    return ingresos_detalle(db, empresa_id, inicio, fin)


@router.get("/estado-resultados/costo-venta", response_model=list[CostoVentaItem])
def costo_venta_detalle(
    mes: str | None = None,
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[CostoVentaItem]:
    _, inicio, fin = rango_mes(mes)
    filas = db.execute(
        select(Venta.id, Venta.fecha, Producto.nombre, DetalleVenta.unidades, Producto.costo_soles)
        .select_from(DetalleVenta)
        .join(Venta, DetalleVenta.venta_id == Venta.id)
        .join(Producto, DetalleVenta.producto_id == Producto.id)
        .where(Venta.empresa_id == empresa_id, Venta.fecha >= inicio, Venta.fecha < fin)
        .order_by(Venta.fecha.desc())
    )
    return [
        CostoVentaItem(
            venta_id=venta_id,
            fecha=fecha,
            producto_nombre=nombre,
            unidades=unidades,
            costo_unitario=costo_unitario or Decimal(0),
            subtotal_costo=(costo_unitario or Decimal(0)) * unidades,
        )
        for venta_id, fecha, nombre, unidades, costo_unitario in filas
    ]


@router.put("/estado-resultados/impuesto", response_model=EstadoResultadosOut)
def actualizar_impuesto(
    data: ImpuestoIn,
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> EstadoResultadosOut:
    periodo, _, _ = rango_mes(data.mes)
    parametros = _parametros(db, empresa_id, periodo)
    parametros.impuesto = data.monto
    db.commit()
    return estado_resultados(mes=data.mes, empresa_id=empresa_id, db=db)


@router.get("/flujo-caja", response_model=FlujoCajaOut)
def flujo_caja(
    mes: str | None = None,
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> FlujoCajaOut:
    periodo, inicio, fin = rango_mes(mes)
    parametros = _parametros(db, empresa_id, periodo)

    ingresos_ventas = ingresos_caja(db, empresa_id, inicio, fin)
    compras_y_gastos = _total_gastos(db, empresa_id, inicio, fin, None)
    saldo_final = parametros.saldo_inicial + ingresos_ventas - compras_y_gastos

    return FlujoCajaOut(
        periodo=periodo,
        saldo_inicial=parametros.saldo_inicial,
        ingresos_ventas=ingresos_ventas,
        compras_y_gastos=compras_y_gastos,
        saldo_final=saldo_final,
    )


@router.put("/flujo-caja/saldo-inicial", response_model=FlujoCajaOut)
def actualizar_saldo_inicial(
    data: SaldoInicialIn,
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> FlujoCajaOut:
    periodo, _, _ = rango_mes(data.mes)
    parametros = _parametros(db, empresa_id, periodo)
    parametros.saldo_inicial = data.monto
    db.commit()
    return flujo_caja(mes=data.mes, empresa_id=empresa_id, db=db)


@router.get("/flujo-caja/entradas", response_model=list[EntradaCajaItem])
def flujo_caja_entradas(
    mes: str | None = None,
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[EntradaCajaItem]:
    _, inicio, fin = rango_mes(mes)
    return entradas_caja_detalle(db, empresa_id, inicio, fin)


@router.get("/cobrar-pagar", response_model=CuentasCobrarPagarOut)
def cobrar_pagar(
    mes: str | None = None,
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> CuentasCobrarPagarOut:
    periodo, inicio, fin = rango_mes(mes)

    total = total_ventas(db, empresa_id, inicio, fin)
    compras = _total_compras_credito_fiscal(db, empresa_id, inicio, fin)
    igv_ventas = total * IGV_TASA
    igv_compras = compras * IGV_TASA
    igv_diferencia = igv_ventas - igv_compras

    saldo_cobrar = saldo_por_cobrar(db, empresa_id, inicio, fin)
    saldo_pagar = (
        db.scalar(
            select(func.coalesce(func.sum(Gasto.costo_total - Gasto.monto_pagado), 0)).where(
                Gasto.empresa_id == empresa_id,
                Gasto.fecha >= inicio,
                Gasto.fecha < fin,
                Gasto.monto_pagado < Gasto.costo_total,
            )
        )
        or Decimal(0)
    )

    return CuentasCobrarPagarOut(
        periodo=periodo,
        total_ventas=total,
        saldo_por_cobrar=saldo_cobrar,
        saldo_por_pagar=saldo_pagar,
        igv_ventas=igv_ventas,
        igv_compras=igv_compras,
        igv_diferencia=igv_diferencia,
    )


@router.get("/cobrar-pagar/por-cobrar", response_model=list[CuentaPorCobrarItem])
def detalle_por_cobrar(
    mes: str | None = None,
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[CuentaPorCobrarItem]:
    _, inicio, fin = rango_mes(mes)
    return ventas_pendientes_detalle(db, empresa_id, inicio, fin)


@router.get("/cobrar-pagar/por-pagar", response_model=list[CuentaPorPagarItem])
def detalle_por_pagar(
    mes: str | None = None,
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[CuentaPorPagarItem]:
    _, inicio, fin = rango_mes(mes)
    gastos = db.scalars(
        select(Gasto)
        .where(
            Gasto.empresa_id == empresa_id,
            Gasto.fecha >= inicio,
            Gasto.fecha < fin,
            Gasto.monto_pagado < Gasto.costo_total,
        )
        .order_by(Gasto.fecha.desc())
    )
    return [
        CuentaPorPagarItem(
            gasto_id=g.id,
            fecha=g.fecha,
            tipo_gasto_nombre=g.tipo_gasto.nombre,
            proveedor_colaborador=g.proveedor_colaborador,
            costo_total=g.costo_total,
            monto_pagado=g.monto_pagado,
            saldo=g.costo_total - g.monto_pagado,
        )
        for g in gastos
    ]
