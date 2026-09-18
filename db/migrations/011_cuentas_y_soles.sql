-- 011_cuentas_y_soles.sql
-- Dos cosas a la vez porque estan relacionadas: (1) el taller opera solo en
-- soles, se quitan todas las columnas de dolares de ventas/productos/gastos;
-- (2) se agrega el modulo Cuentas (Estado de resultados, Flujo de caja,
-- Cuentas por cobrar y pagar), portado de Kaudal (a3-gestion-ventas-app)
-- pero sin distincion de moneda.
--
-- Cada sentencia usa guardas (IF EXISTS/IF NOT EXISTS) porque el primer
-- intento de aplicar esta migracion quedo a medias (fallo por un '%%' sin
-- escapar en un comentario, pero el driver ya habia aplicado parte de las
-- sentencias antes de eso) y hay que poder reejecutarla desde cualquier
-- estado intermedio sin reventar.

BEGIN;

-- ---------------------------------------------------------------------------
-- Solo soles: se quitan las columnas de dolares. Dato existente en esa
-- moneda se pierde a proposito (decision del usuario, taller opera 100%% en
-- soles).
-- ---------------------------------------------------------------------------
ALTER TABLE ventas DROP COLUMN IF EXISTS total_dolares;
ALTER TABLE detalle_venta DROP COLUMN IF EXISTS moneda;
ALTER TABLE productos DROP COLUMN IF EXISTS precio_venta_dolares;
ALTER TABLE productos DROP COLUMN IF EXISTS costo_dolares;
ALTER TABLE gastos DROP COLUMN IF EXISTS moneda;

-- ---------------------------------------------------------------------------
-- Cobros parciales de una venta: antes solo existia venta.monto_abonado
-- (un monto fijo puesto al crear la venta). Ahora se puede ir cobrando en
-- varias fechas -- Flujo de caja cuenta cada cobro en el mes en que se
-- cobra, no en el mes de la venta.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cobros_venta (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id  uuid        NOT NULL REFERENCES empresas(id),
    venta_id    uuid        NOT NULL REFERENCES ventas(id),
    usuario_id  uuid        NOT NULL REFERENCES users(id),
    fecha       date        NOT NULL,
    monto       numeric(10, 2) NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cobros_venta_empresa_fecha ON cobros_venta(empresa_id, fecha);
CREATE INDEX IF NOT EXISTS idx_cobros_venta_venta_id ON cobros_venta(venta_id);

-- ---------------------------------------------------------------------------
-- Gastos: categoria (para separar operativos de financieros en el Estado
-- de resultados), pago parcial (Cuentas por pagar) y credito fiscal (IGV
-- de compras).
-- ---------------------------------------------------------------------------
ALTER TABLE gastos ADD COLUMN IF NOT EXISTS categoria text NOT NULL DEFAULT 'operativo';
ALTER TABLE gastos ADD COLUMN IF NOT EXISTS monto_pagado numeric(10, 2);
UPDATE gastos SET monto_pagado = costo_total WHERE monto_pagado IS NULL;
ALTER TABLE gastos ALTER COLUMN monto_pagado SET NOT NULL;
ALTER TABLE gastos ADD COLUMN IF NOT EXISTS aplica_credito_fiscal boolean NOT NULL DEFAULT true;

-- ---------------------------------------------------------------------------
-- Los dos unicos campos de Cuentas que se ingresan a mano en vez de
-- calcularse desde ventas/gastos: saldo inicial de caja (Flujo de caja) e
-- impuesto (Estado de resultados), por empresa + periodo ('YYYY-MM').
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cuentas_parametros (
    empresa_id    uuid        NOT NULL REFERENCES empresas(id),
    periodo       text        NOT NULL,
    saldo_inicial numeric(12, 2) NOT NULL DEFAULT 0,
    impuesto      numeric(12, 2) NOT NULL DEFAULT 0,
    updated_at    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (empresa_id, periodo)
);

INSERT INTO schema_migrations (version) VALUES ('011_cuentas_y_soles');

COMMIT;
