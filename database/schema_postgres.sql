-- ============================================================
-- schema_postgres.sql
-- ============================================================
-- Version PostgreSQL de schema.sql, para el Postgres gratuito de
-- Render. Mismo modulo de autenticacion, mismas credenciales de
-- prueba:
--   usuario:    admin
--   contrasena: 1234
-- (hash PBKDF2-SHA256 identico al de schema.sql, compatible con
--  werkzeug.security.check_password_hash)
-- ============================================================

CREATE TABLE IF NOT EXISTS usuarios (
    id              SERIAL PRIMARY KEY,
    nombre_usuario  TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    rol             TEXT NOT NULL DEFAULT 'medico' CHECK (rol IN ('admin', 'medico')),
    activo          BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en       TIMESTAMP NOT NULL
);

INSERT INTO usuarios (nombre_usuario, password_hash, rol, activo, creado_en)
VALUES (
    'admin',
    'pbkdf2:sha256:1000000$2Gb4A6VQrOyADCyw$9c362d84f6aad4ecf47bc2342e3a0bd62b5b6408782925980cb0356c78ae8915',
    'admin',
    TRUE,
    '2026-01-01T00:00:00'
)
ON CONFLICT (nombre_usuario) DO NOTHING;
