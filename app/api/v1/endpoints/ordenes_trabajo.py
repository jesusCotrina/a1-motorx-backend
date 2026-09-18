import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import require_empresa, require_roles
from app.db.session import get_db
from app.models.historico import HistoricoMantenimiento, HistoricoReparacion
from app.models.orden_trabajo import OrdenTrabajo
from app.models.user import User
from app.models.vehiculo import Vehiculo
from app.schemas.taller import (
    EstadoPago,
    ItemMantenimientoCreate,
    ItemReparacionCreate,
    OrdenTrabajoCreate,
    OrdenTrabajoOut,
    ResumenOrdenesOut,
)

router = APIRouter()

_CREADORES = ("super_admin", "admin", "mecanico")


def _resolver_vehiculo_por_placa(db: Session, empresa_id: uuid.UUID, placa: str) -> Vehiculo:
    placa_normalizada = placa.strip().upper()
    vehiculo = db.scalar(
        select(Vehiculo).where(
            Vehiculo.empresa_id == empresa_id, Vehiculo.placa == placa_normalizada
        )
    )
    if vehiculo is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "No existe un vehiculo con esa placa"
        )
    return vehiculo


def _ordenes_de_empresa(empresa_id: uuid.UUID, placa: str | None):
    stmt = select(OrdenTrabajo).where(OrdenTrabajo.empresa_id == empresa_id)
    if placa:
        termino = f"%{placa.strip().lower()}%"
        stmt = stmt.join(Vehiculo, OrdenTrabajo.vehiculo_id == Vehiculo.id).where(
            func.lower(Vehiculo.placa).like(termino)
        )
    return stmt


def _items_de_orden(
    db: Session, orden_id: uuid.UUID
) -> tuple[list[HistoricoMantenimiento], list[HistoricoReparacion]]:
    mantenimientos = list(
        db.scalars(
            select(HistoricoMantenimiento).where(
                HistoricoMantenimiento.orden_trabajo_id == orden_id
            )
        )
    )
    reparaciones = list(
        db.scalars(
            select(HistoricoReparacion).where(
                HistoricoReparacion.orden_trabajo_id == orden_id
            )
        )
    )
    return mantenimientos, reparaciones


@router.get("", response_model=list[OrdenTrabajoOut])
def listar_ordenes_trabajo(
    response: Response,
    placa: str | None = None,
    estado: EstadoPago | None = None,
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[OrdenTrabajoOut]:
    """Sin placa, lista las ultimas ordenes de trabajo de toda la empresa
    (cualquier vehiculo), mas recientes primero. Con placa, solo las de ese
    vehiculo (coincidencia parcial). El estado de una orden (pagado/pendiente)
    es un agregado de sus items (ver OrdenTrabajoOut.from_model), no una
    columna propia, asi que el filtro `estado` se aplica en Python despues de
    traer las ordenes candidatas (acotadas por empresa y, si se dio, placa) en
    vez de un WHERE en SQL -- reusa la misma logica de agregado que ya usa la
    respuesta, sin duplicarla."""
    stmt = _ordenes_de_empresa(empresa_id, placa).order_by(
        OrdenTrabajo.fecha.desc(), OrdenTrabajo.created_at.desc()
    )
    ordenes = list(db.scalars(stmt))

    convertidas = []
    for orden in ordenes:
        mantenimientos, reparaciones = _items_de_orden(db, orden.id)
        convertidas.append(OrdenTrabajoOut.from_model(orden, mantenimientos, reparaciones))
    if estado:
        convertidas = [o for o in convertidas if o.estado == estado]

    response.headers["X-Total-Count"] = str(len(convertidas))
    return convertidas[offset : offset + limit]


@router.get("/resumen", response_model=ResumenOrdenesOut)
def resumen_ordenes_trabajo(
    placa: str | None = None,
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> ResumenOrdenesOut:
    stmt = _ordenes_de_empresa(empresa_id, placa).with_only_columns(OrdenTrabajo.id)
    ids = list(db.scalars(stmt))
    if not ids:
        return ResumenOrdenesOut(
            total_ordenes=0,
            total_mantenimientos=0,
            total_reparaciones=0,
            venta_total=Decimal("0"),
            venta_por_cobrar=Decimal("0"),
        )

    total_mantenimientos = (
        db.scalar(
            select(func.count())
            .select_from(HistoricoMantenimiento)
            .where(HistoricoMantenimiento.orden_trabajo_id.in_(ids))
        )
        or 0
    )
    total_reparaciones = (
        db.scalar(
            select(func.count())
            .select_from(HistoricoReparacion)
            .where(HistoricoReparacion.orden_trabajo_id.in_(ids))
        )
        or 0
    )
    costo_mant = db.scalar(
        select(func.coalesce(func.sum(HistoricoMantenimiento.costo), 0)).where(
            HistoricoMantenimiento.orden_trabajo_id.in_(ids)
        )
    )
    costo_rep = db.scalar(
        select(func.coalesce(func.sum(HistoricoReparacion.costo), 0)).where(
            HistoricoReparacion.orden_trabajo_id.in_(ids)
        )
    )
    pago_mant = db.scalar(
        select(func.coalesce(func.sum(HistoricoMantenimiento.pago_cliente), 0)).where(
            HistoricoMantenimiento.orden_trabajo_id.in_(ids)
        )
    )
    pago_rep = db.scalar(
        select(func.coalesce(func.sum(HistoricoReparacion.pago_cliente), 0)).where(
            HistoricoReparacion.orden_trabajo_id.in_(ids)
        )
    )
    venta_total = Decimal(costo_mant) + Decimal(costo_rep)
    pago_total = Decimal(pago_mant) + Decimal(pago_rep)
    return ResumenOrdenesOut(
        total_ordenes=len(ids),
        total_mantenimientos=total_mantenimientos,
        total_reparaciones=total_reparaciones,
        venta_total=venta_total,
        venta_por_cobrar=max(venta_total - pago_total, Decimal("0")),
    )


def _crear_item_mantenimiento(
    empresa_id: uuid.UUID,
    vehiculo_id: uuid.UUID,
    usuario_id: uuid.UUID,
    orden_id: uuid.UUID,
    item: ItemMantenimientoCreate,
) -> HistoricoMantenimiento:
    return HistoricoMantenimiento(
        empresa_id=empresa_id,
        vehiculo_id=vehiculo_id,
        usuario_id=usuario_id,
        orden_trabajo_id=orden_id,
        fec_mantenimiento=item.fec_mantenimiento,
        kilometraje=item.kilometraje,
        tipo_mantenimiento=item.tipo_mantenimiento,
        cambios_realizados=[item.cambio_realizado],
        nota=item.nota,
        costo=item.costo,
        pago_cliente=item.pago_cliente,
    )


def _crear_item_reparacion(
    empresa_id: uuid.UUID,
    vehiculo_id: uuid.UUID,
    usuario_id: uuid.UUID,
    orden_id: uuid.UUID,
    item: ItemReparacionCreate,
) -> HistoricoReparacion:
    return HistoricoReparacion(
        empresa_id=empresa_id,
        vehiculo_id=vehiculo_id,
        usuario_id=usuario_id,
        orden_trabajo_id=orden_id,
        fec_reparacion=item.fec_reparacion,
        kilometraje=item.kilometraje,
        reparaciones_realizadas=[item.trabajo_realizado],
        nota=item.nota,
        costo=item.costo,
        pago_cliente=item.pago_cliente,
    )


@router.post("", response_model=OrdenTrabajoOut, status_code=status.HTTP_201_CREATED)
def crear_orden_trabajo(
    data: OrdenTrabajoCreate,
    empresa_id: uuid.UUID = Depends(require_empresa),
    user: User = Depends(require_roles(*_CREADORES)),
    db: Session = Depends(get_db),
) -> OrdenTrabajoOut:
    if not data.mantenimientos and not data.reparaciones:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "La orden debe tener al menos un mantenimiento o una reparacion",
        )

    vehiculo = _resolver_vehiculo_por_placa(db, empresa_id, data.placa)

    orden = OrdenTrabajo(
        empresa_id=empresa_id,
        vehiculo_id=vehiculo.id,
        usuario_id=user.id,
        fecha=date.today(),
    )
    db.add(orden)
    db.flush()

    for item in data.mantenimientos:
        db.add(_crear_item_mantenimiento(empresa_id, vehiculo.id, user.id, orden.id, item))
    for item in data.reparaciones:
        db.add(_crear_item_reparacion(empresa_id, vehiculo.id, user.id, orden.id, item))

    db.commit()
    db.refresh(orden)
    mantenimientos, reparaciones = _items_de_orden(db, orden.id)
    return OrdenTrabajoOut.from_model(orden, mantenimientos, reparaciones)
