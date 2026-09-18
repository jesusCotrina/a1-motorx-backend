import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import User
from app.models.vehiculo import Vehiculo


class OrdenTrabajo(Base):
    """Agrupa uno o varios mantenimientos y/o reparaciones de un mismo
    vehiculo, registrados juntos en una sola visita. Los items en si viven
    en historico_mantenimiento/historico_reparaciones (ver esos modelos),
    enlazados por orden_trabajo_id; esta tabla es solo el encabezado comun
    (vehiculo, quien la creo, fecha)."""

    __tablename__ = "ordenes_trabajo"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("empresas.id"), index=True
    )
    vehiculo_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("vehiculos.id"), index=True
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    fecha: Mapped[date] = mapped_column(Date, default=date.today)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    vehiculo: Mapped[Vehiculo] = relationship(lazy="joined")
    usuario: Mapped[User] = relationship(lazy="joined")
