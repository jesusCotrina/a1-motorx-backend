-- 003_clientes_vehiculos.sql
-- Clientes y vehiculos de cada empresa (equivalentes a las colecciones
-- Firestore "clientes" y "vehiculos").

BEGIN;

CREATE TABLE clientes (
    id             uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id     uuid        NOT NULL REFERENCES empresas(id),
    tip_documento  text        NOT NULL DEFAULT 'DNI',
    num_documento  text        NOT NULL,
    nombres        text        NOT NULL,
    apellidos      text        NOT NULL,
    correo         text,
    telefono       text,
    fec_nacimiento date,
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE (empresa_id, num_documento)
);

CREATE INDEX idx_clientes_empresa_id ON clientes(empresa_id);

CREATE TRIGGER trg_clientes_updated_at
    BEFORE UPDATE ON clientes
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE vehiculos (
    id             uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id     uuid        NOT NULL REFERENCES empresas(id),
    cliente_id     uuid        NOT NULL REFERENCES clientes(id),
    placa          text        NOT NULL,
    marca          text,
    modelo         text,
    carroceria     text,
    num_motor      text,
    vin_serie      text,
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE (empresa_id, placa)
);

CREATE INDEX idx_vehiculos_empresa_id ON vehiculos(empresa_id);
CREATE INDEX idx_vehiculos_cliente_id ON vehiculos(cliente_id);

CREATE TRIGGER trg_vehiculos_updated_at
    BEFORE UPDATE ON vehiculos
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

INSERT INTO schema_migrations (version) VALUES ('003_clientes_vehiculos');

COMMIT;
