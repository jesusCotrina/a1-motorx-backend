import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import User


class TipoGasto(Base):
    __tablename__ = "tipos_gasto"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("empresas.id"), index=True
    )
    nombre: Mapped[str] = mapped_column(String(80))
    categoria: Mapped[str] = mapped_column(String(20), default="operativo")
    """'operativo' (tambien es la base de "compras y gastos" del flujo de
    caja y del IGV), 'financiero_ingreso' o 'financiero_egreso' (estado de
    resultados)."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Gasto(Base):
    __tablename__ = "gastos"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("empresas.id"), index=True
    )
    tipo_gasto_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tipos_gasto.id"), index=True
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    fecha: Mapped[date] = mapped_column(Date)
    comprobante: Mapped[str | None] = mapped_column(String(80))
    proveedor_colaborador: Mapped[str | None] = mapped_column(String(160))
    metodo_pago: Mapped[str] = mapped_column(String(40))
    costo_total: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    monto_pagado: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    """Cuanto de costo_total ya se pago. Si se registra menor al costo, la
    diferencia es saldo por pagar (modulo Cuentas > Cuentas por cobrar y
    pagar)."""
    aplica_credito_fiscal: Mapped[bool] = mapped_column(default=True)
    """Si el comprobante de este gasto discrimina IGV (da derecho a credito
    fiscal). Determina si cuenta para el "IGV de compras" de Cuentas >
    Cuentas por cobrar y pagar."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    tipo_gasto: Mapped[TipoGasto] = relationship(lazy="joined")
    usuario: Mapped[User] = relationship(lazy="joined")
