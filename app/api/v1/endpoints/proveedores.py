import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import require_empresa, require_roles
from app.db.session import get_db
from app.models.proveedor import Proveedor
from app.schemas.proveedor import ProveedorCreate, ProveedorOut, ProveedorUpdate

router = APIRouter()

_EDITORES = ("super_admin", "admin")


@router.get("", response_model=list[ProveedorOut])
def buscar_proveedores(
    response: Response,
    buscar: str | None = None,
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[ProveedorOut]:
    stmt = select(Proveedor).where(Proveedor.empresa_id == empresa_id)
    if buscar:
        termino = f"%{buscar.strip().lower()}%"
        stmt = stmt.where(
            func.lower(Proveedor.nombre_razon_social).like(termino)
            | func.lower(Proveedor.num_documento).like(termino)
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    response.headers["X-Total-Count"] = str(total)
    proveedores = db.scalars(
        stmt.order_by(Proveedor.nombre_razon_social).limit(limit).offset(offset)
    )
    return [ProveedorOut.from_model(p) for p in proveedores]


@router.post("", response_model=ProveedorOut, status_code=status.HTTP_201_CREATED)
def crear_proveedor(
    data: ProveedorCreate,
    empresa_id: uuid.UUID = Depends(require_empresa),
    _: object = Depends(require_roles(*_EDITORES)),
    db: Session = Depends(get_db),
) -> ProveedorOut:
    existe = db.scalar(
        select(Proveedor).where(
            Proveedor.empresa_id == empresa_id,
            Proveedor.num_documento == data.num_documento,
        )
    )
    if existe is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Ya existe un proveedor con ese numero de documento"
        )

    proveedor = Proveedor(empresa_id=empresa_id, **data.model_dump())
    db.add(proveedor)
    db.commit()
    db.refresh(proveedor)
    return ProveedorOut.from_model(proveedor)


@router.patch("/{proveedor_id}", response_model=ProveedorOut)
def actualizar_proveedor(
    proveedor_id: uuid.UUID,
    data: ProveedorUpdate,
    empresa_id: uuid.UUID = Depends(require_empresa),
    _: object = Depends(require_roles(*_EDITORES)),
    db: Session = Depends(get_db),
) -> ProveedorOut:
    proveedor = db.scalar(
        select(Proveedor).where(
            Proveedor.id == proveedor_id, Proveedor.empresa_id == empresa_id
        )
    )
    if proveedor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proveedor no encontrado")

    if data.num_documento != proveedor.num_documento:
        existe = db.scalar(
            select(Proveedor).where(
                Proveedor.empresa_id == empresa_id,
                Proveedor.num_documento == data.num_documento,
                Proveedor.id != proveedor_id,
            )
        )
        if existe is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Ya existe un proveedor con ese numero de documento"
            )

    for campo, valor in data.model_dump().items():
        setattr(proveedor, campo, valor)
    db.commit()
    db.refresh(proveedor)
    return ProveedorOut.from_model(proveedor)
