import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from app.core.deps import require_empresa, require_roles
from app.core.periodo import rango_mes
from app.db.session import get_db
from app.models.cliente import Cliente
from app.models.inventario import MovimientoInventario
from app.models.producto import Producto
from app.models.user import User
from app.models.venta import CobroVenta, DetalleVenta, Venta
from app.schemas.venta import (
    CobroVentaIn,
    VendedorOut,
    VentaCreate,
    VentaOut,
    VentasTotalesOut,
)

router = APIRouter()

_VENDEDORES_ROLES = ("super_admin", "admin", "mecanico")


def _registrar_cliente_si_falta(
    db: Session, empresa_id: uuid.UUID, documento: str | None, nombre: str | None
) -> None:
    """Da de alta el cliente en `clientes` si su documento no existe todavia.

    El campo cliente de una venta sigue siendo texto libre (no crea ni
    exige un registro en `clientes`), pero si el usuario si escribio
    documento + nombre y no hay un cliente con ese documento en la empresa,
    se aprovecha para registrarlo -- asi aparece luego en el autocompletado
    de la proxima venta y en el modulo Clientes. No falla la venta si esto
    no se puede hacer (p. ej. documento duplicado por una carrera entre dos
    ventas simultaneas): es un efecto secundario, no el proposito del
    endpoint.
    """
    documento = (documento or "").strip()
    nombre = (nombre or "").strip()
    if not documento or not nombre:
        return
    existe = db.scalar(
        select(Cliente).where(
            Cliente.empresa_id == empresa_id, Cliente.num_documento == documento
        )
    )
    if existe is not None:
        return
    tip_documento = "RUC" if documento.isdigit() and len(documento) == 11 else "DNI"
    try:
        with db.begin_nested():
            db.add(
                Cliente(
                    empresa_id=empresa_id,
                    tip_documento=tip_documento,
                    num_documento=documento,
                    nombres=nombre,
                    apellidos="",
                )
            )
            db.flush()
    except IntegrityError:
        # Carrera entre dos ventas simultaneas dando de alta el mismo
        # cliente nuevo: la que llega segunda no rompe, simplemente no
        # duplica (la primera ya lo registro).
        pass


def _query_ventas(
    empresa_id: uuid.UUID,
    inicio,
    fin,
    buscar: str | None,
    estado: str | None,
) -> Select:
    stmt = select(Venta).where(
        Venta.empresa_id == empresa_id, Venta.fecha >= inicio, Venta.fecha < fin
    )
    if buscar:
        termino = f"%{buscar.strip().lower()}%"
        stmt = stmt.join(User, Venta.vendedor_id == User.id).where(
            func.lower(Venta.cliente_nombre).like(termino)
            | func.lower(Venta.cliente_documento).like(termino)
            | func.lower(User.full_name).like(termino)
        )
    if estado == "pagado":
        stmt = stmt.where(
            Venta.monto_abonado.isnot(None), Venta.monto_abonado >= Venta.total_soles
        )
    elif estado == "pendiente":
        stmt = stmt.where(
            or_(Venta.monto_abonado.is_(None), Venta.monto_abonado < Venta.total_soles)
        )
    return stmt


@router.get("", response_model=list[VentaOut])
def listar_ventas(
    response: Response,
    mes: str | None = None,
    buscar: str | None = None,
    estado: str | None = Query(None, pattern="^(pagado|pendiente)$"),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[VentaOut]:
    _, inicio, fin = rango_mes(mes)
    stmt = _query_ventas(empresa_id, inicio, fin, buscar, estado)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    response.headers["X-Total-Count"] = str(total)
    ventas = db.scalars(
        stmt.order_by(Venta.fecha.desc(), Venta.created_at.desc()).limit(limit).offset(offset)
    )
    return [VentaOut.from_model(v) for v in ventas]


@router.get("/totales", response_model=VentasTotalesOut)
def totales_ventas(
    mes: str | None = None,
    buscar: str | None = None,
    estado: str | None = Query(None, pattern="^(pagado|pendiente)$"),
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> VentasTotalesOut:
    _, inicio, fin = rango_mes(mes)
    stmt = _query_ventas(empresa_id, inicio, fin, buscar, estado)
    subq = stmt.subquery()
    cantidad = db.scalar(select(func.count()).select_from(subq)) or 0
    total_soles = db.scalar(select(func.coalesce(func.sum(subq.c.total_soles), 0))) or 0
    total_pagado_soles = (
        db.scalar(select(func.coalesce(func.sum(subq.c.monto_abonado), 0))) or 0
    )
    return VentasTotalesOut(
        cantidad=cantidad,
        total_soles=total_soles,
        total_pagado_soles=total_pagado_soles,
    )


@router.get("/vendedores", response_model=list[VendedorOut])
def listar_vendedores(
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[VendedorOut]:
    no_super_admin = User.role.has(code="admin") | User.role.has(code="mecanico")
    usuarios = db.scalars(
        select(User)
        .where(User.empresa_id == empresa_id, no_super_admin)
        .order_by(User.full_name)
    )
    return [
        VendedorOut(id=u.id, full_name=u.full_name, num_documento=u.num_documento)
        for u in usuarios
    ]


@router.post("", response_model=VentaOut, status_code=status.HTTP_201_CREATED)
def crear_venta(
    data: VentaCreate,
    empresa_id: uuid.UUID = Depends(require_empresa),
    user: User = Depends(require_roles(*_VENDEDORES_ROLES)),
    db: Session = Depends(get_db),
) -> VentaOut:
    vendedor = db.scalar(
        select(User).where(User.id == data.vendedor_id, User.empresa_id == empresa_id)
    )
    if vendedor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vendedor no encontrado")

    productos: dict[uuid.UUID, Producto] = {}
    for linea in data.detalles:
        if linea.producto_id not in productos:
            producto = db.scalar(
                select(Producto).where(
                    Producto.id == linea.producto_id, Producto.empresa_id == empresa_id
                )
            )
            if producto is None:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND, f"Producto {linea.producto_id} no encontrado"
                )
            productos[linea.producto_id] = producto

    unidades_por_producto: dict[uuid.UUID, int] = {}
    for linea in data.detalles:
        unidades_por_producto[linea.producto_id] = (
            unidades_por_producto.get(linea.producto_id, 0) + linea.unidades
        )
    for producto_id, unidades in unidades_por_producto.items():
        producto = productos[producto_id]
        if unidades > producto.stock_actual:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Stock insuficiente para {producto.nombre} "
                f"(disponible: {producto.stock_actual}, solicitado: {unidades})",
            )

    _registrar_cliente_si_falta(db, empresa_id, data.cliente_documento, data.cliente_nombre)

    venta = Venta(
        empresa_id=empresa_id,
        fecha=data.fecha,
        vendedor_id=vendedor.id,
        cliente_documento=data.cliente_documento,
        cliente_nombre=data.cliente_nombre,
        flete=data.flete,
        envio=data.envio,
        monto_abonado=data.monto_abonado,
        observacion=data.observacion,
        metodo_pago=data.metodo_pago,
        tipo_entrega=data.tipo_entrega,
        tipo_comprobante=data.tipo_comprobante,
    )
    db.add(venta)
    db.flush()

    total_soles = data.flete + data.envio

    for linea in data.detalles:
        producto = productos[linea.producto_id]
        precio_unitario = producto.precio_venta_soles
        subtotal = precio_unitario * linea.unidades
        db.add(
            DetalleVenta(
                venta_id=venta.id,
                producto_id=producto.id,
                unidades=linea.unidades,
                precio_unitario=precio_unitario,
                subtotal=subtotal,
            )
        )
        total_soles += subtotal

    for producto_id, unidades in unidades_por_producto.items():
        producto = productos[producto_id]
        producto.stock_actual -= unidades
        db.add(
            MovimientoInventario(
                empresa_id=empresa_id,
                producto_id=producto.id,
                usuario_id=user.id,
                tipo="venta",
                unidades=unidades,
                stock_resultante=producto.stock_actual,
            )
        )

    venta.total_soles = total_soles
    if data.monto_abonado:
        db.add(
            CobroVenta(
                empresa_id=empresa_id,
                venta_id=venta.id,
                usuario_id=user.id,
                fecha=data.fecha,
                monto=data.monto_abonado,
            )
        )
    db.commit()
    db.refresh(venta)
    return VentaOut.from_model(venta)


@router.patch("/{venta_id}/cobro", response_model=VentaOut)
def registrar_cobro(
    venta_id: uuid.UUID,
    data: CobroVentaIn,
    empresa_id: uuid.UUID = Depends(require_empresa),
    user: User = Depends(require_roles(*_VENDEDORES_ROLES)),
    db: Session = Depends(get_db),
) -> VentaOut:
    venta = db.scalar(
        select(Venta).where(Venta.id == venta_id, Venta.empresa_id == empresa_id)
    )
    if venta is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Venta no encontrada")

    abonado_actual = venta.monto_abonado or Decimal(0)
    saldo = venta.total_soles - abonado_actual
    if data.monto > saldo:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"El cobro no puede superar el saldo pendiente ({saldo})",
        )

    if data.monto > 0:
        venta.monto_abonado = abonado_actual + data.monto
        db.add(
            CobroVenta(
                empresa_id=empresa_id,
                venta_id=venta.id,
                usuario_id=user.id,
                fecha=date.today(),
                monto=data.monto,
            )
        )
        db.commit()
        db.refresh(venta)
    return VentaOut.from_model(venta)
