-- 002_empresas_tenant.sql
-- Multi-tenant: empresas (talleres clientes del SaaS) y asignacion de
-- usuarios a una empresa. super_admin no pertenece a ninguna empresa
-- (gestiona la plataforma); admin y mecanico si.

BEGIN;

CREATE TABLE empresas (
    id             uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo         text        NOT NULL UNIQUE,
    nombre         text        NOT NULL,
    ruc            text,
    direccion      text,
    logo_url       text,
    is_active      boolean     NOT NULL DEFAULT true,
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_empresas_codigo ON empresas(lower(codigo));

CREATE TRIGGER trg_empresas_updated_at
    BEFORE UPDATE ON empresas
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

ALTER TABLE users
    ADD COLUMN empresa_id uuid REFERENCES empresas(id);

CREATE INDEX idx_users_empresa_id ON users(empresa_id);

-- Invariante de tenancy: super_admin sin empresa; admin/mecanico con empresa.
CREATE OR REPLACE FUNCTION check_user_empresa() RETURNS trigger AS $$
DECLARE
    role_code text;
BEGIN
    SELECT code INTO role_code FROM roles WHERE id = NEW.role_id;
    IF role_code = 'super_admin' AND NEW.empresa_id IS NOT NULL THEN
        RAISE EXCEPTION 'super_admin no debe tener empresa_id asignado';
    END IF;
    IF role_code != 'super_admin' AND NEW.empresa_id IS NULL THEN
        RAISE EXCEPTION 'los usuarios con rol %% requieren empresa_id', role_code;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_empresa_check
    BEFORE INSERT OR UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION check_user_empresa();

INSERT INTO schema_migrations (version) VALUES ('002_empresas_tenant');

COMMIT;
