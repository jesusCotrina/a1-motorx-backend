import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.producto import Producto
from app.models.user import User


class Venta(Base):
    __tablename__ = "ventas"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("empresas.id"), index=True
    )
    fecha: Mapped[date] = mapped_column(Date)
    vendedor_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    cliente_documento: Mapped[str | None] = mapped_column(String(20))
    cliente_nombre: Mapped[str | None] = mapped_column(String(160))
    """Cliente de la venta: texto libre, no necesariamente un registro de
    la tabla clientes (no se crea automaticamente)."""
    flete: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    envio: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    monto_abonado: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    observacion: Mapped[str | None] = mapped_column(String(2000))
    metodo_pago: Mapped[str] = mapped_column(String(40))
    tipo_entrega: Mapped[str] = mapped_column(String(40))
    tipo_comprobante: Mapped[str] = mapped_column(String(40))
    total_soles: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    vendedor: Mapped[User] = relationship(lazy="joined")
    detalles: Mapped[list["DetalleVenta"]] = relationship(
        lazy="selectin", back_populates="venta", order_by="DetalleVenta.created_at"
    )
    cobros: Mapped[list["CobroVenta"]] = relationship(
        lazy="selectin", order_by="CobroVenta.fecha"
    )


class DetalleVenta(Base):
    __tablename__ = "detalle_venta"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    venta_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("ventas.id"), index=True)
    producto_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("productos.id"))
    unidades: Mapped[int] = mapped_column(Integer)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    producto: Mapped[Producto] = relationship(lazy="joined")
    venta: Mapped[Venta] = relationship(back_populates="detalles")


class CobroVenta(Base):
    """Un pago (total o parcial) recibido por una venta, con su propia
    fecha -- puede ser distinta de la fecha de la venta. Alimenta el Flujo
    de caja del modulo Cuentas: el ingreso se cuenta en el mes del cobro,
    no en el mes de la venta. `venta.monto_abonado` sigue siendo la suma
    acumulada (se actualiza junto con cada cobro nuevo) para no tener que
    sumar los cobros cada vez que se muestra el estado de una venta."""

    __tablename__ = "cobros_venta"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("empresas.id"), index=True
    )
    venta_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("ventas.id"), index=True)
    usuario_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    fecha: Mapped[date] = mapped_column(Date)
    monto: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
