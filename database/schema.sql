-- ============================================================
-- schema.sql
-- ============================================================
-- Base de datos SQLite SOLO para el modulo de inicio de sesion
-- (PB-14: "Implementacion del modulo de autenticacion y control
-- de accesos para el personal de salud").
--
-- A proposito NO se crea aqui la base de datos relacional completa
-- de historial de analisis (PB-12), porque se acordo dejarla para
-- una siguiente iteracion del proyecto.
--
-- Como usarlo:
--   sqlite3 cervix_app.db < schema.sql
-- (o simplemente ejecuta `python init_db.py` desde la carpeta backend,
--  que llama a este mismo archivo).
--
-- Credenciales de prueba creadas por este script:
--   usuario:    admin
--   contrasena: 1234
-- (la contrasena NUNCA se guarda en texto plano: la columna
--  password_hash contiene un hash PBKDF2-SHA256 generado con
--  werkzeug.security.generate_password_hash, compatible con el
--  metodo `verificar_password` de infrastructure/security/auth_service.py)
-- ============================================================

CREATE TABLE IF NOT EXISTS usuarios (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_usuario  TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    rol             TEXT NOT NULL DEFAULT 'medico' CHECK (rol IN ('admin', 'medico')),
    activo          INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    creado_en       TEXT NOT NULL
);

-- Usuario administrador de prueba: admin / 1234
INSERT OR IGNORE INTO usuarios (nombre_usuario, password_hash, rol, activo, creado_en)
VALUES (
    'admin',
    'pbkdf2:sha256:1000000$2Gb4A6VQrOyADCyw$9c362d84f6aad4ecf47bc2342e3a0bd62b5b6408782925980cb0356c78ae8915',
    'admin',
    1,
    '2026-01-01T00:00:00'
);