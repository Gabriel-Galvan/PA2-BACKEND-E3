"""
Script de conveniencia para crear/actualizar la base de datos SQLite
a partir de schema.sql. Util para no depender de tener instalado el
cliente `sqlite3` de linea de comandos.

Uso:
    cd backend
    python database/init_db.py
"""

import os
import sqlite3

DIRECTORIO_ACTUAL = os.path.dirname(os.path.abspath(__file__))
RUTA_SCHEMA = os.path.join(DIRECTORIO_ACTUAL, "schema.sql")
RUTA_DB = os.path.join(DIRECTORIO_ACTUAL, "cervix_app.db")


def inicializar_base_de_datos() -> None:
    with open(RUTA_SCHEMA, "r", encoding="utf-8") as archivo_sql:
        script_sql = archivo_sql.read()

    conexion = sqlite3.connect(RUTA_DB)
    try:
        conexion.executescript(script_sql)
        conexion.commit()
        print(f"Base de datos creada/actualizada correctamente en: {RUTA_DB}")
        print("Usuario de prueba -> usuario: admin | contrasena: 1234")
    finally:
        conexion.close()


if __name__ == "__main__":
    inicializar_base_de_datos()