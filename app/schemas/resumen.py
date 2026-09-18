from decimal import Decimal

from pydantic import BaseModel


class ResumenVentasOut(BaseModel):
    cantidad: int
    total: Decimal
    cobrado: Decimal


class ResumenGastosOut(BaseModel):
    cantidad: int
    total: Decimal


class ResumenSerieItem(BaseModel):
    periodo: str
    ventas: Decimal
    gastos: Decimal


class IngresoPorTipoItem(BaseModel):
    etiqueta: str
    monto: Decimal


class OrdenesEstadoOut(BaseModel):
    pendientes: int
    pagadas: int


class InventarioMiniOut(BaseModel):
    total_productos: int
    bajo_stock: int
    """Productos con stock_actual < 10."""


class ResumenOut(BaseModel):
    periodo: str
    ventas: ResumenVentasOut
    """Incluye tanto las ventas de producto (Ventas/Inventario) como las
    ventas por servicio (cada mantenimiento y cada reparacion de una orden
    de trabajo cuenta como una venta mas, ver modulo Mantenimiento)."""
    gastos: ResumenGastosOut
    utilidad: Decimal
    saldo_por_cobrar: Decimal
    total_ordenes_trabajo: int
    serie_mensual: list[ResumenSerieItem]
    variacion_ventas_pct: Decimal | None
    variacion_gastos_pct: Decimal | None
    variacion_utilidad_pct: Decimal | None
    variacion_saldo_por_cobrar_pct: Decimal | None
    variacion_ordenes_pct: Decimal | None
    """Variacion porcentual de cada metrica contra el mes anterior; `None`
    si el mes anterior no tiene base para comparar (valor en 0)."""
    ingresos_por_tipo: list[IngresoPorTipoItem]
    """Ventas del mes partidas en Mantenimiento / Reparacion / Ventas
    (productos), para el grafico de dona de Resumen."""
    ordenes_trabajo: OrdenesEstadoOut
    inventario: InventarioMiniOut
