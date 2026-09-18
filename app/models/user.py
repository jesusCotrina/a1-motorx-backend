import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, SmallInteger, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.empresa import Empresa
from app.models.role import Role


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    role_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("roles.id"), index=True
    )
    # Todo usuario pertenece a una empresa (multi-tenant): cada empresa tiene
    # su propio super_admin, admin y mecanico. No hay un rol de plataforma
    # sin empresa. Invariante reforzada en BD con NOT NULL (ver
    # db/migrations/006_super_admin_por_empresa.sql).
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("empresas.id"), index=True
    )
    num_documento: Mapped[str | None] = mapped_column(String(20))
    """DNI/documento del usuario; se autocompleta al elegirlo como vendedor
    en una venta. Nullable porque los usuarios existentes no lo tienen
    cargado (no hay todavia una pantalla para editarlo)."""
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    role: Mapped[Role] = relationship(lazy="joined")
    empresa: Mapped[Empresa] = relationship(lazy="joined")
