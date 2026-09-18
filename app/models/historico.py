import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import User
from app.models.vehiculo import Vehiculo


class HistoricoMantenimiento(Base):
    __tablename__ = "historico_mantenimiento"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("empresas.id"), index=True
    )
    vehiculo_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("vehiculos.id"), index=True
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), index=True
    )
    """Quien registro el mantenimiento (admin, super_admin o mecanico)."""
    orden_trabajo_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("ordenes_trabajo.id"), index=True
    )
    fec_mantenimiento: Mapped[date] = mapped_column(Date)
    kilometraje: Mapped[int]
    tipo_mantenimiento: Mapped[str] = mapped_column(String(60))
    cambios_realizados: Mapped[list[str]] = mapped_column(JSON, default=list)
    nota: Mapped[str | None] = mapped_column(String(2000))
    costo: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    pago_cliente: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    vehiculo: Mapped[Vehiculo] = relationship(lazy="joined")
    usuario: Mapped[User] = relationship(lazy="joined")


class HistoricoReparacion(Base):
    __tablename__ = "historico_reparaciones"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("empresas.id"), index=True
    )
    vehiculo_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("vehiculos.id"), index=True
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), index=True
    )
    """Quien registro la reparacion (admin, super_admin o mecanico)."""
    orden_trabajo_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("ordenes_trabajo.id"), index=True
    )
    fec_reparacion: Mapped[date] = mapped_column(Date)
    kilometraje: Mapped[int]
    reparaciones_realizadas: Mapped[list[str]] = mapped_column(JSON, default=list)
    nota: Mapped[str | None] = mapped_column(String(2000))
    costo: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    pago_cliente: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    vehiculo: Mapped[Vehiculo] = relationship(lazy="joined")
    usuario: Mapped[User] = relationship(lazy="joined")
