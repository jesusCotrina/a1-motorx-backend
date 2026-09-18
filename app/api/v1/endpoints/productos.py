import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import require_empresa, require_roles
from app.db.session import get_db
from app.models.inventario import MovimientoInventario
from app.models.producto import CategoriaProducto, Producto
from app.models.user import User
from app.schemas.producto import (
    CategoriaProductoCreate,
    CategoriaProductoOut,
    ProductoCreate,
    ProductoOut,
    ProductoUpdate,
)

router = APIRouter()

_EDITORES = ("super_admin", "admin")


def _like(termino: str) -> str:
    return f"%{termino.strip().lower()}%"


@router.get("/categorias", response_model=list[CategoriaProductoOut])
def listar_categorias(
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[CategoriaProductoOut]:
    categorias = db.scalars(
        select(CategoriaProducto)
        .where(CategoriaProducto.empresa_id == empresa_id)
        .order_by(CategoriaProducto.nombre)
    )
    return [CategoriaProductoOut.from_model(c) for c in categorias]


@router.post(
    "/categorias", response_model=CategoriaProductoOut, status_code=status.HTTP_201_CREATED
)
def crear_categoria(
    data: CategoriaProductoCreate,
    empresa_id: uuid.UUID = Depends(require_empresa),
    _: object = Depends(require_roles(*_EDITORES)),
    db: Session = Depends(get_db),
) -> CategoriaProductoOut:
    nombre = data.nombre.strip()
    existe = db.scalar(
        select(CategoriaProducto).where(
            CategoriaProducto.empresa_id == empresa_id,
            func.lower(CategoriaProducto.nombre) == nombre.lower(),
        )
    )
    if existe is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe una categoria con ese nombre")

    categoria = CategoriaProducto(empresa_id=empresa_id, nombre=nombre)
    db.add(categoria)
    db.commit()
    db.refresh(categoria)
    return CategoriaProductoOut.from_model(categoria)


@router.get("", response_model=list[ProductoOut])
def buscar_productos(
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


@router.post("", response_model=ProductoOut, status_code=status.HTTP_201_CREATED)
def crear_producto(
    data: ProductoCreate,
    empresa_id: uuid.UUID = Depends(require_empresa),
    user: User = Depends(require_roles(*_EDITORES)),
    db: Session = Depends(get_db),
) -> ProductoOut:
    sku = data.sku.strip().upper()
    existe = db.scalar(
        select(Producto).where(Producto.empresa_id == empresa_id, Producto.sku == sku)
    )
    if existe is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un producto con ese SKU")

    categoria = db.scalar(
        select(CategoriaProducto).where(
            CategoriaProducto.id == data.categoria_id,
            CategoriaProducto.empresa_id == empresa_id,
        )
    )
    if categoria is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoria no encontrada")

    producto = Producto(
        empresa_id=empresa_id,
        categoria_id=categoria.id,
        sku=sku,
        nombre=data.nombre.strip(),
        precio_venta_soles=data.precio_venta_soles,
        costo_soles=data.costo_soles,
        descripcion=data.descripcion,
        observaciones=data.observaciones,
        stock_actual=data.unidades_ingresadas,
    )
    db.add(producto)
    db.flush()

    if data.unidades_ingresadas > 0:
        db.add(
            MovimientoInventario(
                empresa_id=empresa_id,
                producto_id=producto.id,
                usuario_id=user.id,
                tipo="ingreso",
                unidades=data.unidades_ingresadas,
                stock_resultante=producto.stock_actual,
            )
        )

    db.commit()
    db.refresh(producto)
    return ProductoOut.from_model(producto)


@router.patch("/{producto_id}", response_model=ProductoOut)
def actualizar_producto(
    producto_id: uuid.UUID,
    data: ProductoUpdate,
    empresa_id: uuid.UUID = Depends(require_empresa),
    _: object = Depends(require_roles(*_EDITORES)),
    db: Session = Depends(get_db),
) -> ProductoOut:
    producto = db.scalar(
        select(Producto).where(Producto.id == producto_id, Producto.empresa_id == empresa_id)
    )
    if producto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")

    sku = data.sku.strip().upper()
    if sku != producto.sku:
        existe = db.scalar(
            select(Producto).where(
                Producto.empresa_id == empresa_id,
                Producto.sku == sku,
                Producto.id != producto_id,
            )
        )
        if existe is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un producto con ese SKU")

    categoria = db.scalar(
        select(CategoriaProducto).where(
            CategoriaProducto.id == data.categoria_id,
            CategoriaProducto.empresa_id == empresa_id,
        )
    )
    if categoria is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoria no encontrada")

    producto.sku = sku
    producto.nombre = data.nombre.strip()
    producto.categoria_id = categoria.id
    producto.precio_venta_soles = data.precio_venta_soles
    producto.costo_soles = data.costo_soles
    producto.descripcion = data.descripcion
    producto.observaciones = data.observaciones
    db.commit()
    db.refresh(producto)
    return ProductoOut.from_model(producto)
