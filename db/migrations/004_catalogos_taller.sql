-- 004_catalogos_taller.sql
-- Catalogos por empresa que alimentan las listas de "cambios realizados"
-- (mantenimiento) y "reparaciones realizadas" (reparaciones) como checkboxes.
-- Equivalentes a las colecciones Firestore "lista_mantenimientos" y
-- "lista_reparaciones".

BEGIN;

CREATE TABLE tipos_mantenimiento (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id  uuid        NOT NULL REFERENCES empresas(id),
    categoria   text        NOT NULL,
    nombre      text        NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (empresa_id, categoria, nombre)
);

CREATE INDEX idx_tipos_mantenimiento_empresa_id ON tipos_mantenimiento(empresa_id);

CREATE TABLE tipos_reparacion (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id  uuid        NOT NULL REFERENCES empresas(id),
    nombre      text        NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (empresa_id, nombre)
);

CREATE INDEX idx_tipos_reparacion_empresa_id ON tipos_reparacion(empresa_id);

INSERT INTO schema_migrations (version) VALUES ('004_catalogos_taller');

COMMIT;
