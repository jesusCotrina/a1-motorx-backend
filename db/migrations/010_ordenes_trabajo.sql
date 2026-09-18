-- 010_ordenes_trabajo.sql
-- Introduce las "ordenes de trabajo": una orden agrupa varios mantenimientos
-- y/o reparaciones de un mismo vehiculo, registrados juntos. historico_mant-
-- enimiento e historico_reparaciones siguen siendo la tabla de cada item (no
-- se reemplazan), solo se les agrega la FK orden_trabajo_id y el pago que
-- dejo el cliente por ese item puntual (pago_cliente, para el estado
-- pagado/pendiente, igual que en ventas).

BEGIN;

CREATE TABLE ordenes_trabajo (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id  uuid        NOT NULL REFERENCES empresas(id),
    vehiculo_id uuid        NOT NULL REFERENCES vehiculos(id),
    usuario_id  uuid        NOT NULL REFERENCES users(id),
    fecha       date        NOT NULL DEFAULT CURRENT_DATE,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_ordenes_trabajo_empresa_id ON ordenes_trabajo(empresa_id);
CREATE INDEX idx_ordenes_trabajo_empresa_fecha ON ordenes_trabajo(empresa_id, fecha DESC);
CREATE INDEX idx_ordenes_trabajo_vehiculo_id ON ordenes_trabajo(vehiculo_id);

ALTER TABLE historico_mantenimiento ADD COLUMN orden_trabajo_id uuid REFERENCES ordenes_trabajo(id);
ALTER TABLE historico_reparaciones  ADD COLUMN orden_trabajo_id uuid REFERENCES ordenes_trabajo(id);
ALTER TABLE historico_mantenimiento ADD COLUMN pago_cliente numeric(10, 2) NOT NULL DEFAULT 0;
ALTER TABLE historico_reparaciones  ADD COLUMN pago_cliente numeric(10, 2) NOT NULL DEFAULT 0;

-- Backfill: el concepto de "orden de trabajo" no existia antes de esta
-- migracion, asi que cada mantenimiento/reparacion ya registrado no
-- pertenece a ninguna en comun con otro. Se le crea su propia orden de
-- trabajo (1 a 1) para no perder el historico existente.
DO $$
DECLARE
    r RECORD;
    nueva_orden uuid;
BEGIN
    FOR r IN
        SELECT id, empresa_id, vehiculo_id, usuario_id, fec_mantenimiento, created_at
        FROM historico_mantenimiento
        WHERE orden_trabajo_id IS NULL
    LOOP
        INSERT INTO ordenes_trabajo (id, empresa_id, vehiculo_id, usuario_id, fecha, created_at)
        VALUES (gen_random_uuid(), r.empresa_id, r.vehiculo_id, r.usuario_id, r.fec_mantenimiento, r.created_at)
        RETURNING id INTO nueva_orden;

        UPDATE historico_mantenimiento SET orden_trabajo_id = nueva_orden WHERE id = r.id;
    END LOOP;

    FOR r IN
        SELECT id, empresa_id, vehiculo_id, usuario_id, fec_reparacion, created_at
        FROM historico_reparaciones
        WHERE orden_trabajo_id IS NULL
    LOOP
        INSERT INTO ordenes_trabajo (id, empresa_id, vehiculo_id, usuario_id, fecha, created_at)
        VALUES (gen_random_uuid(), r.empresa_id, r.vehiculo_id, r.usuario_id, r.fec_reparacion, r.created_at)
        RETURNING id INTO nueva_orden;

        UPDATE historico_reparaciones SET orden_trabajo_id = nueva_orden WHERE id = r.id;
    END LOOP;
END $$;

ALTER TABLE historico_mantenimiento ALTER COLUMN orden_trabajo_id SET NOT NULL;
ALTER TABLE historico_reparaciones  ALTER COLUMN orden_trabajo_id SET NOT NULL;

CREATE INDEX idx_historico_mant_orden_id ON historico_mantenimiento(orden_trabajo_id);
CREATE INDEX idx_historico_rep_orden_id ON historico_reparaciones(orden_trabajo_id);

INSERT INTO schema_migrations (version) VALUES ('010_ordenes_trabajo');

COMMIT;
