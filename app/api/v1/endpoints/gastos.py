import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import require_empresa, require_roles
from app.core.periodo import rango_mes
from app.db.session import get_db
from app.models.gasto import Gasto, TipoGasto
from app.models.user import User
from app.schemas.gasto import (
    GastoOut,
    GastosCreate,
    TipoGastoCreate,
    TipoGastoOut,
)

router = APIRouter()

_EDITORES = ("super_admin", "admin")


@router.get("", response_model=list[GastoOut])
def listar_gastos(
    response: Response,
    mes: str | None = None,
    buscar: str | None = None,
    categoria: str | None = None,
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[GastoOut]:
    _, inicio, fin = rango_mes(mes)
    stmt = select(Gasto).where(
        Gasto.empresa_id == empresa_id, Gasto.fecha >= inicio, Gasto.fecha < fin
    )
    if categoria:
        stmt = stmt.join(TipoGasto).where(TipoGasto.categoria == categoria)
    else:
        stmt = stmt.join(TipoGasto)
    if buscar:
        termino = f"%{buscar.strip().lower()}%"
        stmt = stmt.where(
            func.lower(TipoGasto.nombre).like(termino)
            | func.lower(Gasto.proveedor_colaborador).like(termino)
            | func.lower(Gasto.comprobante).like(termino)
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    response.headers["X-Total-Count"] = str(total)
    gastos = db.scalars(
        stmt.order_by(Gasto.fecha.desc(), Gasto.created_at.desc()).limit(limit).offset(offset)
    )
    return [GastoOut.from_model(g) for g in gastos]


@router.get("/tipos", response_model=list[TipoGastoOut])
def listar_tipos_gasto(
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[TipoGastoOut]:
    tipos = db.scalars(
        select(TipoGasto).where(TipoGasto.empresa_id == empresa_id).order_by(TipoGasto.nombre)
    )
    return [TipoGastoOut.from_model(t) for t in tipos]


@router.post("/tipos", response_model=TipoGastoOut, status_code=status.HTTP_201_CREATED)
def crear_tipo_gasto(
    data: TipoGastoCreate,
    empresa_id: uuid.UUID = Depends(require_empresa),
    _: object = Depends(require_roles(*_EDITORES)),
    db: Session = Depends(get_db),
) -> TipoGastoOut:
    nombre = data.nombre.strip()
    existe = db.scalar(
        select(TipoGasto).where(
            TipoGasto.empresa_id == empresa_id,
            func.lower(TipoGasto.nombre) == nombre.lower(),
        )
    )
    if existe is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un tipo de gasto con ese nombre")

    tipo = TipoGasto(empresa_id=empresa_id, nombre=nombre, categoria=data.categoria)
    db.add(tipo)
    db.commit()
    db.refresh(tipo)
    return TipoGastoOut.from_model(tipo)


@router.post("", response_model=list[GastoOut], status_code=status.HTTP_201_CREATED)
def crear_gastos(
    data: GastosCreate,
    empresa_id: uuid.UUID = Depends(require_empresa),
    user: User = Depends(require_roles(*_EDITORES)),
    db: Session = Depends(get_db),
) -> list[GastoOut]:
    tipos: dict[uuid.UUID, TipoGasto] = {}
    for item in data.gastos:
        if item.tipo_gasto_id not in tipos:
            tipo = db.scalar(
                select(TipoGasto).where(
                    TipoGasto.id == item.tipo_gasto_id, TipoGasto.empresa_id == empresa_id
                )
            )
            if tipo is None:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND, f"Tipo de gasto {item.tipo_gasto_id} no encontrado"
                )
            tipos[item.tipo_gasto_id] = tipo

    creados = []
    for item in data.gastos:
        monto_pagado = item.monto_pagado if item.monto_pagado is not None else item.costo_total
        if monto_pagado < 0 or monto_pagado > item.costo_total:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "El monto pagado no puede ser mayor que el costo total",
            )
        gasto = Gasto(
            empresa_id=empresa_id,
            tipo_gasto_id=tipos[item.tipo_gasto_id].id,
            usuario_id=user.id,
            fecha=date.today(),
            comprobante=item.comprobante,
            proveedor_colaborador=item.proveedor_colaborador,
            metodo_pago=item.metodo_pago,
            costo_total=item.costo_total,
            monto_pagado=monto_pagado,
            aplica_credito_fiscal=item.aplica_credito_fiscal,
        )
        db.add(gasto)
        creados.append(gasto)

    db.commit()
    for g in creados:
        db.refresh(g)
    return [GastoOut.from_model(g) for g in creados]
