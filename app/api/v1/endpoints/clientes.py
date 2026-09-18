import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.deps import require_empresa, require_roles
from app.db.session import get_db
from app.models.cliente import Cliente
from app.models.vehiculo import Vehiculo
from app.schemas.cliente import ClienteCreate, ClienteOut, ClienteUpdate
from app.schemas.taller import VehiculoResumenOut

router = APIRouter()

_EDITORES = ("super_admin", "admin")
_LIMITE_RESULTADOS = 20


def _like(termino: str) -> str:
    return f"%{termino.strip().lower()}%"


@router.get("", response_model=list[ClienteOut])
def buscar_clientes(
    tip_documento: str | None = None,
    num_documento: str | None = None,
    nombres: str | None = None,
    apellidos: str | None = None,
    telefono: str | None = None,
    buscar: str | None = None,
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[ClienteOut]:
    """Sin filtros, lista los clientes de la empresa en orden alfabetico
    (hasta _LIMITE_RESULTADOS). `buscar` es un termino libre que matchea
    numero de documento, nombres o apellidos (OR) - lo usa el autocompletado
    de cliente del formulario de vehiculo, que deja elegir por cualquiera de
    los dos campos con la misma busqueda. El resto de filtros siguen siendo
    exactos/AND para el buscador de Clientes."""
    stmt = select(Cliente).where(Cliente.empresa_id == empresa_id)

    if tip_documento:
        stmt = stmt.where(Cliente.tip_documento == tip_documento)
    if num_documento:
        stmt = stmt.where(func.lower(Cliente.num_documento).like(_like(num_documento)))
    if nombres:
        stmt = stmt.where(func.lower(Cliente.nombres).like(_like(nombres)))
    if apellidos:
        stmt = stmt.where(func.lower(Cliente.apellidos).like(_like(apellidos)))
    if telefono:
        stmt = stmt.where(func.lower(Cliente.telefono).like(_like(telefono)))
    if buscar:
        termino = _like(buscar)
        stmt = stmt.where(
            or_(
                func.lower(Cliente.num_documento).like(termino),
                func.lower(Cliente.nombres).like(termino),
                func.lower(Cliente.apellidos).like(termino),
            )
        )

    stmt = stmt.order_by(Cliente.nombres, Cliente.apellidos).limit(_LIMITE_RESULTADOS)
    clientes = db.scalars(stmt)
    return [ClienteOut.from_model(c) for c in clientes]


@router.get("/{cliente_id}/vehiculos", response_model=list[VehiculoResumenOut])
def vehiculos_de_cliente(
    cliente_id: uuid.UUID,
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[VehiculoResumenOut]:
    cliente = db.scalar(
        select(Cliente).where(Cliente.id == cliente_id, Cliente.empresa_id == empresa_id)
    )
    if cliente is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")

    vehiculos = db.scalars(select(Vehiculo).where(Vehiculo.cliente_id == cliente_id))
    return [VehiculoResumenOut.from_model(v) for v in vehiculos]


@router.post("", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
def crear_cliente(
    data: ClienteCreate,
    empresa_id: uuid.UUID = Depends(require_empresa),
    _: object = Depends(require_roles(*_EDITORES)),
    db: Session = Depends(get_db),
) -> ClienteOut:
    existe = db.scalar(
        select(Cliente).where(
            Cliente.empresa_id == empresa_id,
            Cliente.num_documento == data.num_documento,
        )
    )
    if existe is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Ya existe un cliente con ese numero de documento"
        )

    cliente = Cliente(empresa_id=empresa_id, **data.model_dump())
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return ClienteOut.from_model(cliente)


@router.patch("/{cliente_id}", response_model=ClienteOut)
def actualizar_cliente(
    cliente_id: uuid.UUID,
    data: ClienteUpdate,
    empresa_id: uuid.UUID = Depends(require_empresa),
    _: object = Depends(require_roles(*_EDITORES)),
    db: Session = Depends(get_db),
) -> ClienteOut:
    cliente = db.scalar(
        select(Cliente).where(Cliente.id == cliente_id, Cliente.empresa_id == empresa_id)
    )
    if cliente is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")

    for campo, valor in data.model_dump().items():
        setattr(cliente, campo, valor)
    db.commit()
    db.refresh(cliente)
    return ClienteOut.from_model(cliente)
