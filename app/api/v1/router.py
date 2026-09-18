from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    catalogos,
    clientes,
    cuentas,
    empresas,
    gastos,
    historico,
    inventario,
    ordenes_trabajo,
    productos,
    proveedores,
    reportes,
    resumen,
    vehiculos,
    ventas,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(clientes.router, prefix="/clientes", tags=["clientes"])
api_router.include_router(vehiculos.router, prefix="/vehiculos", tags=["vehiculos"])
api_router.include_router(historico.router, prefix="/historico", tags=["historico"])
api_router.include_router(
    ordenes_trabajo.router, prefix="/ordenes-trabajo", tags=["ordenes-trabajo"]
)
api_router.include_router(catalogos.router, prefix="/catalogos", tags=["catalogos"])
api_router.include_router(empresas.router, prefix="/empresas", tags=["empresas"])
api_router.include_router(productos.router, prefix="/productos", tags=["productos"])
api_router.include_router(proveedores.router, prefix="/proveedores", tags=["proveedores"])
api_router.include_router(inventario.router, prefix="/inventario", tags=["inventario"])
api_router.include_router(ventas.router, prefix="/ventas", tags=["ventas"])
api_router.include_router(gastos.router, prefix="/gastos", tags=["gastos"])
api_router.include_router(cuentas.router, prefix="/cuentas", tags=["cuentas"])
api_router.include_router(resumen.router, prefix="/resumen", tags=["resumen"])
api_router.include_router(reportes.router, prefix="/reportes", tags=["reportes"])


@api_router.get("/ping", tags=["health"])
def ping() -> dict[str, str]:
    return {"ping": "pong"}
