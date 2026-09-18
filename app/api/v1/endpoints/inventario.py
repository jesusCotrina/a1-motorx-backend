import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import require_empresa, require_roles
from app.core.periodo import rango_mes
from app.db.session import get_db
from app.models.gasto import Gasto
from app.models.inventario import MovimientoInventario
from app.models.producto import Producto
from app.models.proveedor import Proveedor
from app.models.user import User
from app.models.venta import Venta
from app.schemas.inventario import (
    GastosMesOut,
    IngresoInventarioCreate,
    ResumenInventarioOut,
    VentasMesOut,
)
from app.schemas.producto import ProductoOut

router = APIRouter()

_EDITORES = ("super_admin", "admin")


def _like(termino: str) -> str:
    return f"%{termino.strip().lower()}%"


@router.get("", response_model=list[ProductoOut])
def listar_inventario(
    response: Response,
    buscar: str | None = None,
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[ProductoOut]:
    stmt = select(Producto).where(Producto.empresa_id == empresa_id)
    if buscar:
        termino = _like(buscar)
        stmt = stmt.where(
            func.lower(Producto.nombre).like(termino) | func.lower(Producto.sku).like(termino)
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    response.headers["X-Total-Count"] = str(total)
    productos = db.scalars(stmt.order_by(Producto.nombre).limit(limit).offset(offset))
    return [ProductoOut.from_model(p) for p in productos]


@router.post("/ingresos", response_model=ProductoOut, status_code=status.HTTP_201_CREATED)
def registrar_ingreso(
    data: IngresoInventarioCreate,
    empresa_id: uuid.UUID = Depends(require_empresa),
    user: User = Depends(require_roles(*_EDITORES)),
    db: Session = Depends(get_db),
) -> ProductoOut:
    producto = db.scalar(
        select(Producto).where(
            Producto.id == data.producto_id, Producto.empresa_id == empresa_id
        )
    )
    if producto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")

    producto.stock_actual += data.unidades
    db.add(
        MovimientoInventario(
            empresa_id=empresa_id,
            producto_id=producto.id,
            usuario_id=user.id,
            tipo="ingreso",
            unidades=data.unidades,
            stock_resultante=producto.stock_actual,
        )
    )
    db.commit()
    db.refresh(producto)
    return ProductoOut.from_model(producto)


@router.get("/resumen", response_model=ResumenInventarioOut)
def resumen_inventario(
    mes: str | None = None,
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> ResumenInventarioOut:
    mes_str, inicio, fin = rango_mes(mes)

    total_productos = (
        db.scalar(
            select(func.count()).select_from(Producto).where(Producto.empresa_id == empresa_id)
        )
        or 0
    )
    total_proveedores = (
        db.scalar(
            select(func.count()).select_from(Proveedor).where(Proveedor.empresa_id == empresa_id)
        )
        or 0
    )
    total_stock = (
        db.scalar(
            select(func.coalesce(func.sum(Producto.stock_actual), 0)).where(
                Producto.empresa_id == empresa_id
            )
        )
        or 0
    )

    ventas_stmt = select(Venta).where(
        Venta.empresa_id == empresa_id, Venta.fecha >= inicio, Venta.fecha < fin
    )
    cantidad_ventas = (
        db.scalar(select(func.count()).select_from(ventas_stmt.subquery())) or 0
    )
    total_soles = (
        db.scalar(
            select(func.coalesce(func.sum(Venta.total_soles), 0)).where(
                Venta.empresa_id == empresa_id, Venta.fecha >= inicio, Venta.fecha < fin
            )
        )
        or 0
    )

    cantidad_gastos = (
        db.scalar(
            select(func.count()).select_from(Gasto).where(
                Gasto.empresa_id == empresa_id, Gasto.fecha >= inicio, Gasto.fecha < fin
            )
        )
        or 0
    )
    gastos_soles = (
        db.scalar(
            select(func.coalesce(func.sum(Gasto.costo_total), 0)).where(
                Gasto.empresa_id == empresa_id,
                Gasto.fecha >= inicio,
                Gasto.fecha < fin,
            )
        )
        or 0
    )

    return ResumenInventarioOut(
        total_productos=total_productos,
        total_proveedores=total_proveedores,
        total_stock_unidades=total_stock,
        ventas_mes=VentasMesOut(
            mes=mes_str,
            cantidad=cantidad_ventas,
            total_soles=total_soles,
        ),
        gastos_mes=GastosMesOut(
            mes=mes_str,
            cantidad=cantidad_gastos,
            total_soles=gastos_soles,
        ),
    )
