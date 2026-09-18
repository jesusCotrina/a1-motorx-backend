-- 001_init.sql
-- Esquema base para PostgreSQL: control de migraciones + autenticacion y roles.
-- (En desarrollo con SQLite este script NO se usa: ver app/db/bootstrap.py.)

BEGIN;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version     text        PRIMARY KEY,
    applied_at  timestamptz NOT NULL DEFAULT now()
);

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- Roles
-- ---------------------------------------------------------------------------
CREATE TABLE roles (
    id    smallint PRIMARY KEY,
    code  text NOT NULL UNIQUE,
    name  text NOT NULL
);

INSERT INTO roles (id, code, name) VALUES
    (1, 'super_admin', 'Super Administrador'),
    (2, 'admin',       'Administrador'),
    (3, 'mecanico',    'Mecanico');

-- ---------------------------------------------------------------------------
-- Usuarios
-- ---------------------------------------------------------------------------
CREATE TABLE users (
    id             uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    email          text        NOT NULL UNIQUE,
    password_hash  text        NOT NULL,
    full_name      text        NOT NULL,
    role_id        smallint    NOT NULL REFERENCES roles(id),
    is_active      boolean     NOT NULL DEFAULT true,
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_users_role_id ON users(role_id);
CREATE INDEX idx_users_email   ON users(lower(email));

CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

INSERT INTO schema_migrations (version) VALUES ('001_init');

COMMIT;
