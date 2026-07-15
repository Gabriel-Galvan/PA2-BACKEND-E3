"""
CAPA: INFRASTRUCTURE (Infraestructura) - Persistencia
========================================================
Implementacion CONCRETA del puerto `RepositorioCodigosInvitacion`
usando SQLite. La tabla `codigos_invitacion` se crea en
database/schema.sql.
"""

import sqlite3
from datetime import datetime

from domain.entities import CodigoInvitacion
from domain.repositories import RepositorioCodigosInvitacion

_COLUMNAS = "id, codigo, creado_por, usado, usado_por, creado_en, usado_en"


class RepositorioCodigosInvitacionSQLite(RepositorioCodigosInvitacion):
    def __init__(self, ruta_db: str):
        self._ruta_db = ruta_db

    def _conectar(self) -> sqlite3.Connection:
        conexion = sqlite3.connect(self._ruta_db)
        conexion.row_factory = sqlite3.Row
        return conexion

    def crear(self, codigo: str, creado_por: int) -> CodigoInvitacion:
        ahora = datetime.utcnow().isoformat()
        with self._conectar() as conexion:
            cursor = conexion.execute(
                f"INSERT INTO codigos_invitacion (codigo, creado_por, usado, creado_en) "
                f"VALUES (?, ?, 0, ?)",
                (codigo, creado_por, ahora),
            )
            conexion.commit()
            nuevo_id = cursor.lastrowid
        return CodigoInvitacion(
            id=nuevo_id, codigo=codigo, creado_por=creado_por, usado=False, creado_en=datetime.fromisoformat(ahora)
        )

    def obtener_por_codigo(self, codigo: str) -> CodigoInvitacion | None:
        with self._conectar() as conexion:
            fila = conexion.execute(
                f"SELECT {_COLUMNAS} FROM codigos_invitacion WHERE codigo = ?", (codigo,)
            ).fetchone()
        return self._fila_a_entidad(fila) if fila else None

    def marcar_usado(self, codigo_id: int, usuario_id: int) -> bool:
        with self._conectar() as conexion:
            cursor = conexion.execute(
                "UPDATE codigos_invitacion SET usado = 1, usado_por = ?, usado_en = ? "
                "WHERE id = ? AND usado = 0",
                (usuario_id, datetime.utcnow().isoformat(), codigo_id),
            )
            conexion.commit()
        return cursor.rowcount > 0

    def listar_todos(self) -> list[CodigoInvitacion]:
        with self._conectar() as conexion:
            filas = conexion.execute(
                f"SELECT {_COLUMNAS} FROM codigos_invitacion ORDER BY creado_en DESC"
            ).fetchall()
        return [self._fila_a_entidad(f) for f in filas]

    @staticmethod
    def _fila_a_entidad(fila: sqlite3.Row) -> CodigoInvitacion:
        return CodigoInvitacion(
            id=fila["id"],
            codigo=fila["codigo"],
            creado_por=fila["creado_por"],
            usado=bool(fila["usado"]),
            usado_por=fila["usado_por"],
            creado_en=datetime.fromisoformat(fila["creado_en"]) if fila["creado_en"] else None,
            usado_en=datetime.fromisoformat(fila["usado_en"]) if fila["usado_en"] else None,
        )
