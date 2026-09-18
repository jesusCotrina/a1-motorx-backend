import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.historico import HistoricoMantenimiento, HistoricoReparacion
from app.models.user import User
from app.schemas.taller import (
    HistoricoMantenimientoOut,
    HistoricoMantenimientoUpdate,
    HistoricoReparacionOut,
    HistoricoReparacionUpdate,
)

router = APIRouter()

_EDITORES = ("super_admin", "admin")


def _check_tenant(user: User, empresa_id: uuid.UUID) -> None:
    if user.empresa_id != empresa_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Permisos insuficientes")


@router.patch("/mantenimiento/{historico_id}", response_model=HistoricoMantenimientoOut)
def actualizar_mantenimiento(
    historico_id: uuid.UUID,
    data: HistoricoMantenimientoUpdate,
    user: User = Depends(require_roles(*_EDITORES)),
    db: Session = Depends(get_db),
) -> HistoricoMantenimientoOut:
    registro = db.get(HistoricoMantenimiento, historico_id)
    if registro is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registro no encontrado")
    _check_tenant(user, registro.empresa_id)

    registro.fec_mantenimiento = data.fec_mantenimiento
    registro.kilometraje = data.kilometraje
    registro.tipo_mantenimiento = data.tipo_mantenimiento
    registro.cambios_realizados = data.cambios_realizados
    registro.nota = data.nota
    registro.costo = data.costo
    registro.pago_cliente = data.pago_cliente
    db.commit()
    db.refresh(registro)
    return HistoricoMantenimientoOut.from_model(registro)


@router.patch("/reparaciones/{historico_id}", response_model=HistoricoReparacionOut)
def actualizar_reparacion(
    historico_id: uuid.UUID,
    data: HistoricoReparacionUpdate,
    user: User = Depends(require_roles(*_EDITORES)),
    db: Session = Depends(get_db),
) -> HistoricoReparacionOut:
    registro = db.get(HistoricoReparacion, historico_id)
    if registro is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registro no encontrado")
    _check_tenant(user, registro.empresa_id)

    registro.fec_reparacion = data.fec_reparacion
    registro.kilometraje = data.kilometraje
    registro.reparaciones_realizadas = data.reparaciones_realizadas
    registro.nota = data.nota
    registro.costo = data.costo
    registro.pago_cliente = data.pago_cliente
    db.commit()
    db.refresh(registro)
    return HistoricoReparacionOut.from_model(registro)
