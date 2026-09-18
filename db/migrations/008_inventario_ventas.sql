-- 008_inventario_ventas.sql
-- Modulo de Inventario/Ventas: catalogo de productos (con categorias por
-- empresa), proveedores, movimientos de stock y ventas (con su detalle de
-- lineas). Tambien agrega el documento de identidad del usuario (users.
-- num_documento), necesario para autocompletar el DNI del vendedor al
-- registrar una venta.

BEGIN;

ALTER TABLE users ADD COLUMN num_documento text;

CREATE TABLE categorias_producto (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id  uuid        NOT NULL REFERENCES empresas(id),
    nombre      text        NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (empresa_id, nombre)
);

CREATE INDEX idx_categorias_producto_empresa_id ON categorias_producto(empresa_id);

CREATE TABLE productos (
    id                    uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id            uuid        NOT NULL REFERENCES empresas(id),
    categoria_id          uuid        NOT NULL REFERENCES categorias_producto(id),
    sku                   text        NOT NULL,
    nombre                text        NOT NULL,
    precio_venta_soles    numeric(10, 2) NOT NULL,
    precio_venta_dolares  numeric(10, 2),
    costo_soles           numeric(10, 2) NOT NULL,
    costo_dolares         numeric(10, 2),
    stock_actual          integer     NOT NULL DEFAULT 0,
    descripcion           text,
    observaciones         text,
    created_at            timestamptz NOT NULL DEFAULT now(),
    updated_at            timestamptz NOT NULL DEFAULT now(),
    UNIQUE (empresa_id, sku)
);

CREATE INDEX idx_productos_empresa_id ON productos(empresa_id);
CREATE INDEX idx_productos_categoria_id ON productos(categoria_id);

CREATE TRIGGER trg_productos_updated_at
    BEFORE UPDATE ON productos
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE proveedores (
    id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id          uuid        NOT NULL REFERENCES empresas(id),
    tip_documento       text        NOT NULL DEFAULT 'RUC',
    num_documento       text        NOT NULL,
    nombre_razon_social text        NOT NULL,
    pais                text,
    telefono            text,
    email               text,
    tipo_proveedor      text,
    observaciones       text,
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now(),
    UNIQUE (empresa_id, num_documento)
);

CREATE INDEX idx_proveedores_empresa_id ON proveedores(empresa_id);

CREATE TRIGGER trg_proveedores_updated_at
    BEFORE UPDATE ON proveedores
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE movimientos_inventario (
    id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id       uuid        NOT NULL REFERENCES empresas(id),
    producto_id      uuid        NOT NULL REFERENCES productos(id),
    usuario_id       uuid        NOT NULL REFERENCES users(id),
    tipo             text        NOT NULL,
    unidades         integer     NOT NULL,
    stock_resultante integer     NOT NULL,
    created_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_mov_inventario_empresa_id ON movimientos_inventario(empresa_id);
CREATE INDEX idx_mov_inventario_producto_id ON movimientos_inventario(producto_id);

CREATE TABLE ventas (
    id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id       uuid        NOT NULL REFERENCES empresas(id),
    fecha            date        NOT NULL,
    vendedor_id      uuid        NOT NULL REFERENCES users(id),
    cliente_documento text,
    cliente_nombre   text,
    flete            numeric(10, 2) NOT NULL DEFAULT 0,
    envio            numeric(10, 2) NOT NULL DEFAULT 0,
    monto_abonado    numeric(10, 2),
    observacion      text,
    metodo_pago      text        NOT NULL,
    tipo_entrega     text        NOT NULL,
    tipo_comprobante text        NOT NULL,
    total_soles      numeric(10, 2) NOT NULL DEFAULT 0,
    total_dolares    numeric(10, 2) NOT NULL DEFAULT 0,
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_ventas_empresa_id ON ventas(empresa_id);
CREATE INDEX idx_ventas_empresa_fecha ON ventas(empresa_id, fecha DESC);

CREATE TRIGGER trg_ventas_updated_at
    BEFORE UPDATE ON ventas
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE detalle_venta (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    venta_id        uuid        NOT NULL REFERENCES ventas(id),
    producto_id     uuid        NOT NULL REFERENCES productos(id),
    unidades        integer     NOT NULL,
    moneda          text        NOT NULL,
    precio_unitario numeric(10, 2) NOT NULL,
    subtotal        numeric(10, 2) NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_detalle_venta_venta_id ON detalle_venta(venta_id);

INSERT INTO schema_migrations (version) VALUES ('008_inventario_ventas');

COMMIT;
