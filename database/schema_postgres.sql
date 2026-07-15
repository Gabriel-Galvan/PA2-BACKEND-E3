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
    creado_en       TIMESTAMP NOT NULL,
    correo          TEXT
);

-- Migracion aditiva: si la tabla `usuarios` ya existia (deploy previo
-- sin este modulo), esto agrega la columna sin romper nada.
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS correo TEXT;

-- Migracion aditiva: foto de perfil del usuario (se guarda como data URL
-- base64, igual criterio que imagen_datos/imagen_mime de expedientes pero
-- mas simple porque el avatar siempre se sirve entero, nunca se omite).
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS avatar_base64 TEXT;

INSERT INTO usuarios (nombre_usuario, password_hash, rol, activo, creado_en)
VALUES (
    'admin',
    'pbkdf2:sha256:1000000$2Gb4A6VQrOyADCyw$9c362d84f6aad4ecf47bc2342e3a0bd62b5b6408782925980cb0356c78ae8915',
    'admin',
    TRUE,
    '2026-01-01T00:00:00'
)
ON CONFLICT (nombre_usuario) DO NOTHING;

-- ============================================================
-- Modulo de Expedientes (PB-12): historial clinico relacional,
-- un expediente por analisis de imagen guardado por un medico.
-- ============================================================
CREATE TABLE IF NOT EXISTS expedientes (
    id                      SERIAL PRIMARY KEY,
    medico_id               INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    nombre_paciente         TEXT NOT NULL,
    numero_documento        TEXT NOT NULL,
    fecha_nacimiento        DATE,
    sexo                    TEXT,
    historial_ginecologico  TEXT,
    sintomas                TEXT,
    observaciones           TEXT,
    diagnostico_ia          TEXT NOT NULL,
    confianza_ia            DOUBLE PRECISION NOT NULL,
    probabilidades_ia       TEXT,
    nombre_archivo_imagen   TEXT,
    imagen_mime             TEXT,
    imagen_datos            BYTEA,
    creado_en               TIMESTAMP NOT NULL DEFAULT NOW(),
    actualizado_en          TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_expedientes_medico_id ON expedientes(medico_id);

-- Migracion aditiva: si la tabla `expedientes` ya existia de un deploy
-- anterior (sin el campo sexo), esto agrega la columna sin romper nada.
ALTER TABLE expedientes ADD COLUMN IF NOT EXISTS sexo TEXT;

-- Migracion aditiva: deteccion multi-celula (detector YOLO + clasificador).
-- Guarda TODAS las celulas que el detector encontro en la imagen de campo
-- completo (bbox, clase, confianza de cada una) como JSON, como informacion
-- de apoyo. diagnostico_ia/confianza_ia siguen siendo el hallazgo principal
-- (el mas severo entre todas las celulas detectadas).
ALTER TABLE expedientes ADD COLUMN IF NOT EXISTS celulas_detectadas TEXT;
