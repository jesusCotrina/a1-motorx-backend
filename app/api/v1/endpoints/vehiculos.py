import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import require_empresa, require_roles
from app.db.session import get_db
from app.models.cliente import Cliente
from app.models.vehiculo import Vehiculo
from app.schemas.taller import VehiculoCreate, VehiculoOut, VehiculoUpdate

router = APIRouter()

_EDITORES = ("super_admin", "admin")
_LIMITE_RESULTADOS = 10


def _like(termino: str) -> str:
    return f"%{termino.strip().lower()}%"


def _resolver_cliente(
    db: Session, empresa_id: uuid.UUID, tip_documento: str, num_documento: str
) -> Cliente:
    cliente = db.scalar(
        select(Cliente).where(
            Cliente.empresa_id == empresa_id,
            Cliente.tip_documento == tip_documento,
            Cliente.num_documento == num_documento,
        )
    )
    if cliente is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No existe un cliente con ese tipo y numero de documento en esta empresa. "
            "Crea el cliente primero.",
        )
    return cliente


@router.get("", response_model=list[VehiculoOut])
def buscar_vehiculos(
    placa: str | None = None,
    modelo: str | None = None,
    marca: str | None = None,
    carroceria: str | None = None,
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[VehiculoOut]:
    """Busca por placa, modelo, marca y/o carroceria (coincidencia parcial,
    combinados con AND si se dan varios). Sin filtros, lista los vehiculos
    de la empresa en orden alfabetico (vista por defecto). Sirve tanto para
    el modulo de Vehiculos como para el autocompletado de placa del modulo
    de Mantenimiento."""
    stmt = select(Vehiculo).where(Vehiculo.empresa_id == empresa_id)
    if placa:
        stmt = stmt.where(func.lower(Vehiculo.placa).like(_like(placa)))
    if modelo:
        stmt = stmt.where(func.lower(Vehiculo.modelo).like(_like(modelo)))
    if marca:
        stmt = stmt.where(func.lower(Vehiculo.marca).like(_like(marca)))
    if carroceria:
        stmt = stmt.where(func.lower(Vehiculo.carroceria).like(_like(carroceria)))

    vehiculos = db.scalars(
        stmt.order_by(Vehiculo.placa).limit(_LIMITE_RESULTADOS)
    )
    return [VehiculoOut.from_model(v) for v in vehiculos]


@router.post("", response_model=VehiculoOut, status_code=status.HTTP_201_CREATED)
def crear_vehiculo(
    data: VehiculoCreate,
    empresa_id: uuid.UUID = Depends(require_empresa),
    _: object = Depends(require_roles(*_EDITORES)),
    db: Session = Depends(get_db),
) -> VehiculoOut:
    cliente = _resolver_cliente(db, empresa_id, data.tip_documento, data.num_documento)

    placa_normalizada = data.placa.strip().upper()
    existe = db.scalar(
        select(Vehiculo).where(
            Vehiculo.empresa_id == empresa_id, Vehiculo.placa == placa_normalizada
        )
    )
    if existe is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Ya existe un vehiculo con esa placa"
        )

    vehiculo = Vehiculo(
        empresa_id=empresa_id,
        cliente_id=cliente.id,
        placa=placa_normalizada,
        marca=data.marca,
        modelo=data.modelo,
        carroceria=data.carroceria,
        num_motor=data.num_motor,
        vin_serie=data.vin_serie,
    )
    db.add(vehiculo)
    db.commit()
    db.refresh(vehiculo)
    return VehiculoOut.from_model(vehiculo)


@router.patch("/{vehiculo_id}", response_model=VehiculoOut)
def actualizar_vehiculo(
    vehiculo_id: uuid.UUID,
    data: VehiculoUpdate,
    empresa_id: uuid.UUID = Depends(require_empresa),
    _: object = Depends(require_roles(*_EDITORES)),
    db: Session = Depends(get_db),
) -> VehiculoOut:
    vehiculo = db.scalar(
        select(Vehiculo).where(
            Vehiculo.id == vehiculo_id, Vehiculo.empresa_id == empresa_id
        )
    )
    if vehiculo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehiculo no encontrado")

    cliente = _resolver_cliente(db, empresa_id, data.tip_documento, data.num_documento)

    placa_normalizada = data.placa.strip().upper()
    if placa_normalizada != vehiculo.placa:
        existe = db.scalar(
            select(Vehiculo).where(
                Vehiculo.empresa_id == empresa_id,
                Vehiculo.placa == placa_normalizada,
                Vehiculo.id != vehiculo_id,
            )
        )
        if existe is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Ya existe un vehiculo con esa placa"
            )

    vehiculo.placa = placa_normalizada
    vehiculo.marca = data.marca
    vehiculo.modelo = data.modelo
    vehiculo.carroceria = data.carroceria
    vehiculo.num_motor = data.num_motor
    vehiculo.vin_serie = data.vin_serie
    vehiculo.cliente_id = cliente.id
    db.commit()
    db.refresh(vehiculo)
    return VehiculoOut.from_model(vehiculo)
