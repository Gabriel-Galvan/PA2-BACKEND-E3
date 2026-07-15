"""
CAPA: INFRASTRUCTURE (Infraestructura) - Persistencia
========================================================
Implementacion CONCRETA del puerto `RepositorioNotificaciones` usando
SQLite. La tabla `notificaciones` se crea en database/schema.sql.
"""

import sqlite3
from datetime import datetime

from domain.entities import Notificacion
from domain.repositories import RepositorioNotificaciones

_COLUMNAS = "id, usuario_id, tipo, titulo, mensaje, leida, referencia_id, creado_en"


class RepositorioNotificacionesSQLite(RepositorioNotificaciones):
    def __init__(self, ruta_db: str):
        self._ruta_db = ruta_db

    def _conectar(self) -> sqlite3.Connection:
        conexion = sqlite3.connect(self._ruta_db)
        conexion.row_factory = sqlite3.Row
        return conexion

    def crear(self, notificacion: Notificacion) -> Notificacion:
        ahora = datetime.utcnow().isoformat()
        with self._conectar() as conexion:
            cursor = conexion.execute(
                "INSERT INTO notificaciones (usuario_id, tipo, titulo, mensaje, leida, referencia_id, creado_en) "
                "VALUES (?, ?, ?, ?, 0, ?, ?)",
                (
                    notificacion.usuario_id,
                    notificacion.tipo,
                    notificacion.titulo,
                    notificacion.mensaje,
                    notificacion.referencia_id,
                    ahora,
                ),
            )
            conexion.commit()
            nuevo_id = cursor.lastrowid
        return Notificacion(
            id=nuevo_id,
            usuario_id=notificacion.usuario_id,
            tipo=notificacion.tipo,
            titulo=notificacion.titulo,
            mensaje=notificacion.mensaje,
            leida=False,
            referencia_id=notificacion.referencia_id,
            creado_en=datetime.fromisoformat(ahora),
        )

    def crear_para_admins(self, tipo: str, titulo: str, mensaje: str, referencia_id: int | None = None) -> None:
        ahora = datetime.utcnow().isoformat()
        with self._conectar() as conexion:
            admins = conexion.execute("SELECT id FROM usuarios WHERE rol = 'admin' AND activo = 1").fetchall()
            for fila in admins:
                conexion.execute(
                    "INSERT INTO notificaciones (usuario_id, tipo, titulo, mensaje, leida, referencia_id, creado_en) "
                    "VALUES (?, ?, ?, ?, 0, ?, ?)",
                    (fila["id"], tipo, titulo, mensaje, referencia_id, ahora),
                )
            conexion.commit()

    def listar_por_usuario(self, usuario_id: int, limite: int = 30) -> list[Notificacion]:
        with self._conectar() as conexion:
            filas = conexion.execute(
                f"SELECT {_COLUMNAS} FROM notificaciones WHERE usuario_id = ? "
                "ORDER BY creado_en DESC LIMIT ?",
                (usuario_id, limite),
            ).fetchall()
        return [self._fila_a_entidad(f) for f in filas]

    def contar_no_leidas(self, usuario_id: int) -> int:
        with self._conectar() as conexion:
            fila = conexion.execute(
                "SELECT COUNT(*) AS total FROM notificaciones WHERE usuario_id = ? AND leida = 0",
                (usuario_id,),
            ).fetchone()
        return fila["total"] if fila else 0

    def marcar_leida(self, notificacion_id: int, usuario_id: int) -> bool:
        with self._conectar() as conexion:
            cursor = conexion.execute(
                "UPDATE notificaciones SET leida = 1 WHERE id = ? AND usuario_id = ?",
                (notificacion_id, usuario_id),
            )
            conexion.commit()
        return cursor.rowcount > 0

    def marcar_todas_leidas(self, usuario_id: int) -> bool:
        with self._conectar() as conexion:
            cursor = conexion.execute(
                "UPDATE notificaciones SET leida = 1 WHERE usuario_id = ? AND leida = 0",
                (usuario_id,),
            )
            conexion.commit()
        return cursor.rowcount > 0

    @staticmethod
    def _fila_a_entidad(fila: sqlite3.Row) -> Notificacion:
        return Notificacion(
            id=fila["id"],
            usuario_id=fila["usuario_id"],
            tipo=fila["tipo"],
            titulo=fila["titulo"],
            mensaje=fila["mensaje"],
            leida=bool(fila["leida"]),
            referencia_id=fila["referencia_id"],
            creado_en=datetime.fromisoformat(fila["creado_en"]) if fila["creado_en"] else None,
        )
