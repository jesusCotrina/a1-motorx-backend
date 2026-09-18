from app.models.catalogo import TipoMantenimiento, TipoReparacion
from app.models.cliente import Cliente
from app.models.cuenta import ParametrosCuenta
from app.models.empresa import Empresa
from app.models.gasto import Gasto, TipoGasto
from app.models.historico import HistoricoMantenimiento, HistoricoReparacion
from app.models.inventario import MovimientoInventario
from app.models.orden_trabajo import OrdenTrabajo
from app.models.producto import CategoriaProducto, Producto
from app.models.proveedor import Proveedor
from app.models.role import Role
from app.models.user import User
from app.models.vehiculo import Vehiculo
from app.models.venta import CobroVenta, DetalleVenta, Venta

__all__ = [
    "Role",
    "User",
    "Empresa",
    "Cliente",
    "Vehiculo",
    "TipoMantenimiento",
    "TipoReparacion",
    "HistoricoMantenimiento",
    "HistoricoReparacion",
    "OrdenTrabajo",
    "CategoriaProducto",
    "Producto",
    "Proveedor",
    "MovimientoInventario",
    "Venta",
    "DetalleVenta",
    "CobroVenta",
    "TipoGasto",
    "Gasto",
    "ParametrosCuenta",
]
