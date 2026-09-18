-- 005_historico_taller.sql
-- Historico de mantenimientos y reparaciones por vehiculo. Equivalentes a
-- las colecciones Firestore "historico_mantenimiento" y
-- "historico_reparaciones".

BEGIN;

CREATE TABLE historico_mantenimiento (
    id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id          uuid        NOT NULL REFERENCES empresas(id),
    vehiculo_id         uuid        NOT NULL REFERENCES vehiculos(id),
    fec_mantenimiento   date        NOT NULL,
    kilometraje         integer     NOT NULL,
    tipo_mantenimiento  text        NOT NULL,
    cambios_realizados  jsonb       NOT NULL DEFAULT '[]'::jsonb,
    costo               numeric(10, 2),
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_historico_mant_empresa_id ON historico_mantenimiento(empresa_id);
CREATE INDEX idx_historico_mant_vehiculo_fecha
    ON historico_mantenimiento(vehiculo_id, fec_mantenimiento DESC);

CREATE TRIGGER trg_historico_mant_updated_at
    BEFORE UPDATE ON historico_mantenimiento
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE historico_reparaciones (
    id                       uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id               uuid        NOT NULL REFERENCES empresas(id),
    vehiculo_id              uuid        NOT NULL REFERENCES vehiculos(id),
    fec_reparacion           date        NOT NULL,
    kilometraje              integer     NOT NULL,
    reparaciones_realizadas  jsonb       NOT NULL DEFAULT '[]'::jsonb,
    nota                     text,
    costo                    numeric(10, 2),
    created_at               timestamptz NOT NULL DEFAULT now(),
    updated_at               timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_historico_rep_empresa_id ON historico_reparaciones(empresa_id);
CREATE INDEX idx_historico_rep_vehiculo_fecha
    ON historico_reparaciones(vehiculo_id, fec_reparacion DESC);

CREATE TRIGGER trg_historico_rep_updated_at
    BEFORE UPDATE ON historico_reparaciones
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

INSERT INTO schema_migrations (version) VALUES ('005_historico_taller');

COMMIT;
