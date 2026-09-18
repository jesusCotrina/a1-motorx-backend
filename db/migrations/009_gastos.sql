-- 009_gastos.sql
-- Modulo de Gastos (tarjeta "Gastos" dentro de Ventas/Inventario): tipos de
-- gasto configurables por empresa (planilla, alquiler, servicios...) y los
-- gastos registrados.

BEGIN;

CREATE TABLE tipos_gasto (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id  uuid        NOT NULL REFERENCES empresas(id),
    nombre      text        NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (empresa_id, nombre)
);

CREATE INDEX idx_tipos_gasto_empresa_id ON tipos_gasto(empresa_id);

CREATE TABLE gastos (
    id                    uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id            uuid        NOT NULL REFERENCES empresas(id),
    tipo_gasto_id         uuid        NOT NULL REFERENCES tipos_gasto(id),
    usuario_id            uuid        NOT NULL REFERENCES users(id),
    fecha                 date        NOT NULL,
    moneda                text        NOT NULL,
    comprobante           text,
    proveedor_colaborador text,
    metodo_pago           text        NOT NULL,
    costo_total           numeric(10, 2) NOT NULL,
    created_at            timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_gastos_empresa_id ON gastos(empresa_id);
CREATE INDEX idx_gastos_empresa_fecha ON gastos(empresa_id, fecha DESC);

INSERT INTO schema_migrations (version) VALUES ('009_gastos');

COMMIT;
