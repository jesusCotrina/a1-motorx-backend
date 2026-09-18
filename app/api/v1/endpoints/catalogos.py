import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import require_empresa, require_roles
from app.db.session import get_db
from app.models.catalogo import TipoMantenimiento, TipoReparacion
from app.schemas.taller import (
    TipoMantenimientoCreate,
    TipoMantenimientoOut,
    TipoReparacionCreate,
    TipoReparacionOut,
)

router = APIRouter()

_EDITORES = ("super_admin", "admin")


@router.get("/mantenimiento", response_model=list[TipoMantenimientoOut])
def listar_tipos_mantenimiento(
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[TipoMantenimientoOut]:
    tipos = db.scalars(
        select(TipoMantenimiento)
        .where(TipoMantenimiento.empresa_id == empresa_id)
        .order_by(TipoMantenimiento.categoria, TipoMantenimiento.nombre)
    )
    return [
        TipoMantenimientoOut(id=t.id, categoria=t.categoria, nombre=t.nombre) for t in tipos
    ]


@router.post(
    "/mantenimiento", response_model=TipoMantenimientoOut, status_code=status.HTTP_201_CREATED
)
def crear_tipo_mantenimiento(
    data: TipoMantenimientoCreate,
    empresa_id: uuid.UUID = Depends(require_empresa),
    _: object = Depends(require_roles(*_EDITORES)),
    db: Session = Depends(get_db),
) -> TipoMantenimientoOut:
    categoria = data.categoria.strip()
    nombre = data.nombre.strip()
    existe = db.scalar(
        select(TipoMantenimiento).where(
            TipoMantenimiento.empresa_id == empresa_id,
            func.lower(TipoMantenimiento.categoria) == categoria.lower(),
            func.lower(TipoMantenimiento.nombre) == nombre.lower(),
        )
    )
    if existe is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe ese cambio para ese tipo")

    tipo = TipoMantenimiento(empresa_id=empresa_id, categoria=categoria, nombre=nombre)
    db.add(tipo)
    db.commit()
    db.refresh(tipo)
    return TipoMantenimientoOut(id=tipo.id, categoria=tipo.categoria, nombre=tipo.nombre)


@router.get("/reparacion", response_model=list[TipoReparacionOut])
def listar_tipos_reparacion(
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[TipoReparacionOut]:
    tipos = db.scalars(
        select(TipoReparacion)
        .where(TipoReparacion.empresa_id == empresa_id)
        .order_by(TipoReparacion.nombre)
    )
    return [TipoReparacionOut(id=t.id, nombre=t.nombre) for t in tipos]


@router.post(
    "/reparacion", response_model=TipoReparacionOut, status_code=status.HTTP_201_CREATED
)
def crear_tipo_reparacion(
    data: TipoReparacionCreate,
    empresa_id: uuid.UUID = Depends(require_empresa),
    _: object = Depends(require_roles(*_EDITORES)),
    db: Session = Depends(get_db),
) -> TipoReparacionOut:
    nombre = data.nombre.strip()
    existe = db.scalar(
        select(TipoReparacion).where(
            TipoReparacion.empresa_id == empresa_id,
            func.lower(TipoReparacion.nombre) == nombre.lower(),
        )
    )
    if existe is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un trabajo con ese nombre")

    tipo = TipoReparacion(empresa_id=empresa_id, nombre=nombre)
    db.add(tipo)
    db.commit()
    db.refresh(tipo)
    return TipoReparacionOut(id=tipo.id, nombre=tipo.nombre)
