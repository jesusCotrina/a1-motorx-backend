-- 006_super_admin_por_empresa.sql
-- Correccion de diseno: NO existe un super_admin "de plataforma" sin
-- empresa. Cada empresa tiene su propio super_admin (dueno del taller),
-- ademas de admin y mecanico. Los 3 roles requieren empresa_id.
--
-- (002_empresas_tenant.sql asumia que super_admin era un rol de plataforma
-- sin tenant; esa lectura era incorrecta.)

BEGIN;

DROP TRIGGER IF EXISTS trg_users_empresa_check ON users;
DROP FUNCTION IF EXISTS check_user_empresa();

-- Backfill: en este punto solo existe una empresa, asi que cualquier
-- usuario sin empresa_id (el super_admin de plataforma anterior) se asigna
-- a ella. Si en el futuro hubiera mas de una empresa esto no aplicaria,
-- pero es correcto para el estado actual de los datos.
UPDATE users
SET empresa_id = (SELECT id FROM empresas ORDER BY created_at LIMIT 1)
WHERE empresa_id IS NULL;

ALTER TABLE users
    ALTER COLUMN empresa_id SET NOT NULL;

INSERT INTO schema_migrations (version) VALUES ('006_super_admin_por_empresa');

COMMIT;
