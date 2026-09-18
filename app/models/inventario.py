import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.producto import Producto
from app.models.user import User


class MovimientoInventario(Base):
    __tablename__ = "movimientos_inventario"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("empresas.id"), index=True
    )
    producto_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("productos.id"), index=True
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    tipo: Mapped[str] = mapped_column(String(20))
    """'ingreso' (unico tipo por ahora: alta de stock manual o inicial)."""
    unidades: Mapped[int] = mapped_column(Integer)
    stock_resultante: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    producto: Mapped[Producto] = relationship(lazy="joined")
    usuario: Mapped[User] = relationship(lazy="joined")
