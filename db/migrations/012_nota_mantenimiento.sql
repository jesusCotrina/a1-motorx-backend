-- 012_nota_mantenimiento.sql
-- Un mantenimiento no tenia campo de nota libre (solo la reparacion),
-- pero el usuario pidio poder anotar algo opcional tambien al registrar
-- un mantenimiento (p. ej. detalles del cambio que no caben en el
-- desplegable de "cambio realizado").

BEGIN;

ALTER TABLE historico_mantenimiento ADD COLUMN IF NOT EXISTS nota VARCHAR(2000);

INSERT INTO schema_migrations (version) VALUES ('012_nota_mantenimiento')
ON CONFLICT DO NOTHING;

COMMIT;
