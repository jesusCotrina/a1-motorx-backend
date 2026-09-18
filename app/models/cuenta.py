import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ParametrosCuenta(Base):
    """Los dos unicos campos del modulo Cuentas que el usuario ingresa a
    mano en vez de calcularse desde ventas/gastos/ordenes de trabajo: el
    saldo inicial de caja (Flujo de caja) y el impuesto (Estado de
    resultados), por empresa + periodo ('YYYY-MM'). Sin distincion de
    moneda: el taller opera solo en soles."""

    __tablename__ = "cuentas_parametros"

    empresa_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("empresas.id"), primary_key=True
    )
    periodo: Mapped[str] = mapped_column(String(7), primary_key=True)
    saldo_inicial: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    impuesto: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
