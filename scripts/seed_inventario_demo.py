"""Datos de ejemplo del modulo Ventas/Inventario para la empresa demo (ver
seed_test_users.py): categorias, productos, proveedores, un ingreso de stock,
una venta de muestra, tipos de gasto y un par de gastos de ejemplo.

Uso:
    python scripts/seed_test_users.py   # primero: crea la empresa DEMO
    python scripts/seed_inventario_demo.py

Idempotente: los tipos de gasto se crean solo si no existen (por nombre); el
resto (productos/proveedores/venta) se omite por completo si el producto de
ejemplo ACE-001 ya existe.
"""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from app.db.session import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    CategoriaProducto,
    CobroVenta,
    DetalleVenta,
    Empresa,
    Gasto,
    MovimientoInventario,
    Producto,
    Proveedor,
    Role,
    TipoGasto,
    User,
    Venta,
)

EMPRESA_CODIGO = "DEMO"

CATEGORIAS = ["Lubricantes", "Filtros", "Repuestos"]

TIPOS_GASTO = [
    "Planilla",
    "Compra",
    "Alquiler",
    "Prosegur",
    "Agua",
    "Luz",
    "Internet",
    "Línea de celulares",
]

# (tipo, comprobante, proveedor_colaborador, metodo_pago, costo_soles)
GASTOS_EJEMPLO = [
    ("Alquiler", "F001-123", "Inmobiliaria Los Robles", "Transferencia", 1200.00),
    ("Internet", "B002-456", "Movistar Empresas", "Tarjeta", 150.00),
]

# (sku, nombre, categoria, precio_soles, costo_soles, stock_inicial)
PRODUCTOS = [
    ("ACE-001", "Aceite 20W50 (4L)", "Lubricantes", 45.00, 30.00, 20),
    ("FIL-001", "Filtro de aceite", "Filtros", 25.00, 15.00, 15),
    ("FRE-001", "Pastillas de freno (juego)", "Repuestos", 80.00, 50.00, 10),
]

PROVEEDORES = [
    (
        "RUC",
        "20123456789",
        "Lubricantes SAC",
        "Perú",
        "999888777",
        "ventas@lubrisac.pe",
        "Distribuidor",
    ),
    (
        "RUC",
        "20456789123",
        "Repuestos Perú EIRL",
        "Perú",
        "999111222",
        "contacto@repuestosperu.pe",
        "Mayorista",
    ),
]


def main() -> None:
    with SessionLocal() as db:
        empresa = db.scalar(select(Empresa).where(Empresa.codigo == EMPRESA_CODIGO))
        if empresa is None:
            raise SystemExit(
                f"No existe la empresa '{EMPRESA_CODIGO}'. "
                "Ejecuta primero: python scripts/seed_test_users.py"
            )

        super_admin = db.scalar(
            select(User)
            .join(Role)
            .where(User.empresa_id == empresa.id, Role.code == "super_admin")
        )
        mecanico = db.scalar(
            select(User).join(Role).where(User.empresa_id == empresa.id, Role.code == "mecanico")
        )
        if super_admin is None or mecanico is None:
            raise SystemExit(
                f"La empresa '{EMPRESA_CODIGO}' no tiene los 3 roles de usuario. "
                "Ejecuta primero: python scripts/seed_test_users.py"
            )

        tipos_gasto: dict[str, TipoGasto] = {
            t.nombre: t
            for t in db.scalars(
                select(TipoGasto).where(TipoGasto.empresa_id == empresa.id)
            )
        }
        creados_tipos = 0
        for nombre in TIPOS_GASTO:
            if nombre not in tipos_gasto:
                tipo = TipoGasto(empresa_id=empresa.id, nombre=nombre)
                db.add(tipo)
                tipos_gasto[nombre] = tipo
                creados_tipos += 1
        db.flush()

        existe_gasto_ejemplo = db.scalar(
            select(Gasto).where(
                Gasto.empresa_id == empresa.id, Gasto.comprobante == GASTOS_EJEMPLO[0][1]
            )
        )
        if existe_gasto_ejemplo is None:
            for tipo_nombre, comprobante, proveedor, metodo, costo in GASTOS_EJEMPLO:
                db.add(
                    Gasto(
                        empresa_id=empresa.id,
                        tipo_gasto_id=tipos_gasto[tipo_nombre].id,
                        usuario_id=super_admin.id,
                        fecha=date.today(),
                        comprobante=comprobante,
                        proveedor_colaborador=proveedor,
                        metodo_pago=metodo,
                        costo_total=Decimal(str(costo)),
                        monto_pagado=Decimal(str(costo)),
                    )
                )
        db.commit()
        print(f"Tipos de gasto: {creados_tipos} nuevos (de {len(TIPOS_GASTO)} esperados).")
        if existe_gasto_ejemplo is None:
            print(f"Gastos de ejemplo creados: {len(GASTOS_EJEMPLO)}.")
        else:
            print("Los gastos de ejemplo ya existian.")

        existe = db.scalar(
            select(Producto).where(Producto.empresa_id == empresa.id, Producto.sku == "ACE-001")
        )
        if existe is not None:
            print("Los productos de ejemplo ya existen. Nada mas que hacer.")
            return

        categorias: dict[str, CategoriaProducto] = {}
        for nombre in CATEGORIAS:
            categoria = CategoriaProducto(empresa_id=empresa.id, nombre=nombre)
            db.add(categoria)
            categorias[nombre] = categoria
        db.flush()

        productos: dict[str, Producto] = {}
        for sku, nombre, categoria, precio_s, costo_s, stock in PRODUCTOS:
            producto = Producto(
                empresa_id=empresa.id,
                categoria_id=categorias[categoria].id,
                sku=sku,
                nombre=nombre,
                precio_venta_soles=Decimal(str(precio_s)),
                costo_soles=Decimal(str(costo_s)),
                stock_actual=stock,
            )
            db.add(producto)
            productos[sku] = producto
        db.flush()

        for sku, *_rest, stock in PRODUCTOS:
            db.add(
                MovimientoInventario(
                    empresa_id=empresa.id,
                    producto_id=productos[sku].id,
                    usuario_id=super_admin.id,
                    tipo="ingreso",
                    unidades=stock,
                    stock_resultante=stock,
                )
            )

        for tip_doc, num_doc, razon_social, pais, telefono, email, tipo in PROVEEDORES:
            db.add(
                Proveedor(
                    empresa_id=empresa.id,
                    tip_documento=tip_doc,
                    num_documento=num_doc,
                    nombre_razon_social=razon_social,
                    pais=pais,
                    telefono=telefono,
                    email=email,
                    tipo_proveedor=tipo,
                )
            )

        # Venta de muestra: el mecanico vende 2 aceites y 1 filtro de aceite.
        aceite = productos["ACE-001"]
        filtro = productos["FIL-001"]
        unidades_aceite, unidades_filtro = 2, 1
        subtotal_aceite = aceite.precio_venta_soles * unidades_aceite
        subtotal_filtro = filtro.precio_venta_soles * unidades_filtro

        venta = Venta(
            empresa_id=empresa.id,
            fecha=date.today(),
            vendedor_id=mecanico.id,
            cliente_documento="87654321",
            cliente_nombre="Cliente de muestra",
            flete=Decimal("0"),
            envio=Decimal("0"),
            monto_abonado=subtotal_aceite + subtotal_filtro,
            observacion="Venta de ejemplo generada por seed_inventario_demo.py",
            metodo_pago="Efectivo",
            tipo_entrega="Recojo en tienda",
            tipo_comprobante="Boleta",
            total_soles=subtotal_aceite + subtotal_filtro,
        )
        db.add(venta)
        db.flush()

        db.add(
            CobroVenta(
                empresa_id=empresa.id,
                venta_id=venta.id,
                usuario_id=mecanico.id,
                fecha=date.today(),
                monto=subtotal_aceite + subtotal_filtro,
            )
        )

        db.add(
            DetalleVenta(
                venta_id=venta.id,
                producto_id=aceite.id,
                unidades=unidades_aceite,
                precio_unitario=aceite.precio_venta_soles,
                subtotal=subtotal_aceite,
            )
        )
        db.add(
            DetalleVenta(
                venta_id=venta.id,
                producto_id=filtro.id,
                unidades=unidades_filtro,
                precio_unitario=filtro.precio_venta_soles,
                subtotal=subtotal_filtro,
            )
        )

        aceite.stock_actual -= unidades_aceite
        filtro.stock_actual -= unidades_filtro
        db.add(
            MovimientoInventario(
                empresa_id=empresa.id,
                producto_id=aceite.id,
                usuario_id=mecanico.id,
                tipo="venta",
                unidades=unidades_aceite,
                stock_resultante=aceite.stock_actual,
            )
        )
        db.add(
            MovimientoInventario(
                empresa_id=empresa.id,
                producto_id=filtro.id,
                usuario_id=mecanico.id,
                tipo="venta",
                unidades=unidades_filtro,
                stock_resultante=filtro.stock_actual,
            )
        )

        db.commit()

    print(f"Datos de ejemplo creados para la empresa '{EMPRESA_CODIGO}': {len(CATEGORIAS)}")
    print(f"categorias, {len(PRODUCTOS)} productos, {len(PROVEEDORES)} proveedores y 1 venta.")


if __name__ == "__main__":
    main()
