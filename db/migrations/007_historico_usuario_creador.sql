-- 007_historico_usuario_creador.sql
-- Registra quien creo cada mantenimiento/reparacion (admin, super_admin o
-- mecanico): el modulo de Mantenimiento/Servicio ahora lo muestra en el
-- historico.

BEGIN;

ALTER TABLE historico_mantenimiento ADD COLUMN usuario_id uuid REFERENCES users(id);
ALTER TABLE historico_reparaciones ADD COLUMN usuario_id uuid REFERENCES users(id);

-- Backfill de registros existentes: no se guardo quien los creo antes de
-- esta migracion, asi que se les asigna el super_admin de su propia
-- empresa como mejor aproximacion disponible.
UPDATE historico_mantenimiento hm
SET usuario_id = (
    SELECT u.id FROM users u
    WHERE u.empresa_id = hm.empresa_id
      AND u.role_id = (SELECT id FROM roles WHERE code = 'super_admin')
    ORDER BY u.created_at
    LIMIT 1
)
WHERE hm.usuario_id IS NULL;

UPDATE historico_reparaciones hr
SET usuario_id = (
    SELECT u.id FROM users u
    WHERE u.empresa_id = hr.empresa_id
      AND u.role_id = (SELECT id FROM roles WHERE code = 'super_admin')
    ORDER BY u.created_at
    LIMIT 1
)
WHERE hr.usuario_id IS NULL;

ALTER TABLE historico_mantenimiento ALTER COLUMN usuario_id SET NOT NULL;
ALTER TABLE historico_reparaciones ALTER COLUMN usuario_id SET NOT NULL;

CREATE INDEX idx_historico_mant_usuario_id ON historico_mantenimiento(usuario_id);
CREATE INDEX idx_historico_rep_usuario_id ON historico_reparaciones(usuario_id);

INSERT INTO schema_migrations (version) VALUES ('007_historico_usuario_creador');

COMMIT;
