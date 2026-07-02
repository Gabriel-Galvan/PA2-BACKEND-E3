"""
Script de inicializacion de la base de datos PostgreSQL a partir de
schema_postgres.sql. Pensado para correr como Pre-Deploy Command en
Render (se ejecuta en cada deploy, es idempotente gracias a
CREATE TABLE IF NOT EXISTS / ON CONFLICT DO NOTHING).

Uso local:
    DATABASE_URL=postgresql://... python database/init_db_postgres.py
"""

import os
import sys

import psycopg2

DIRECTORIO_ACTUAL = os.path.dirname(os.path.abspath(__file__))
RUTA_SCHEMA = os.path.join(DIRECTORIO_ACTUAL, "schema_postgres.sql")


def inicializar_base_de_datos() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: no se encontro la variable de entorno DATABASE_URL")
        sys.exit(1)

    database_url = database_url.replace("postgres://", "postgresql://", 1)

    with open(RUTA_SCHEMA, "r", encoding="utf-8") as archivo_sql:
        script_sql = archivo_sql.read()

    conexion = psycopg2.connect(database_url)
    try:
        with conexion.cursor() as cursor:
            cursor.execute(script_sql)
        conexion.commit()
        print("Base de datos PostgreSQL creada/actualizada correctamente.")
        print("Usuario de prueba -> usuario: admin | contrasena: 1234")
    finally:
        conexion.close()


if __name__ == "__main__":
    inicializar_base_de_datos()
