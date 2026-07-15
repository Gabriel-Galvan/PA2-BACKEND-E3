"""
CAPA: INFRASTRUCTURE (Infraestructura) - Persistencia
========================================================
Implementacion CONCRETA del puerto `RepositorioNotificaciones` usando
PostgreSQL (Render Postgres). Espejo de
sqlite_notificacion_repository.py.
"""

import psycopg2
import psycopg2.extras

from domain.entities import Notificacion
from domain.repositories import RepositorioNotificaciones

_COLUMNAS = "id, usuario_id, tipo, titulo, mensaje, leida, referencia_id, creado_en"


class RepositorioNotificacionesPostgres(RepositorioNotificaciones):
    def __init__(self, database_url: str):
        self._database_url = database_url.replace("postgres://", "postgresql://", 1)

    def _conectar(self):
        return psycopg2.connect(self._database_url)

    def crear(self, notificacion: Notificacion) -> Notificacion:
        with self._conectar() as conexion:
            with conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    f"INSERT INTO notificaciones (usuario_id, tipo, titulo, mensaje, leida, referencia_id, creado_en) "
                    f"VALUES (%s, %s, %s, %s, FALSE, %s, NOW()) RETURNING {_COLUMNAS}",
                    (
                        notificacion.usuario_id,
                        notificacion.tipo,
                        notificacion.titulo,
                        notificacion.mensaje,
                        notificacion.referencia_id,
                    ),
                )
                fila = cursor.fetchone()
            conexion.commit()
        return self._fila_a_entidad(fila)

    def crear_para_admins(self, tipo: str, titulo: str, mensaje: str, referencia_id: int | None = None) -> None:
        with self._conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("SELECT id FROM usuarios WHERE rol = 'admin' AND activo = TRUE")
                ids_admins = [fila[0] for fila in cursor.fetchall()]
                for admin_id in ids_admins:
                    cursor.execute(
                        "INSERT INTO notificaciones (usuario_id, tipo, titulo, mensaje, leida, referencia_id, creado_en) "
                        "VALUES (%s, %s, %s, %s, FALSE, %s, NOW())",
                        (admin_id, tipo, titulo, mensaje, referencia_id),
                    )
            conexion.commit()

    def listar_por_usuario(self, usuario_id: int, limite: int = 30) -> list[Notificacion]:
        with self._conectar() as conexion:
            with conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    f"SELECT {_COLUMNAS} FROM notificaciones WHERE usuario_id = %s "
                    "ORDER BY creado_en DESC LIMIT %s",
                    (usuario_id, limite),
                )
                filas = cursor.fetchall()
        return [self._fila_a_entidad(f) for f in filas]

    def contar_no_leidas(self, usuario_id: int) -> int:
        with self._conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) FROM notificaciones WHERE usuario_id = %s AND leida = FALSE",
                    (usuario_id,),
                )
                total = cursor.fetchone()[0]
        return total

    def marcar_leida(self, notificacion_id: int, usuario_id: int) -> bool:
        with self._conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "UPDATE notificaciones SET leida = TRUE WHERE id = %s AND usuario_id = %s",
                    (notificacion_id, usuario_id),
                )
                filas_afectadas = cursor.rowcount
            conexion.commit()
        return filas_afectadas > 0

    def marcar_todas_leidas(self, usuario_id: int) -> bool:
        with self._conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "UPDATE notificaciones SET leida = TRUE WHERE usuario_id = %s AND leida = FALSE",
                    (usuario_id,),
                )
                filas_afectadas = cursor.rowcount
            conexion.commit()
        return filas_afectadas > 0

    @staticmethod
    def _fila_a_entidad(fila) -> Notificacion:
        return Notificacion(
            id=fila["id"],
            usuario_id=fila["usuario_id"],
            tipo=fila["tipo"],
            titulo=fila["titulo"],
            mensaje=fila["mensaje"],
            leida=bool(fila["leida"]),
            referencia_id=fila.get("referencia_id"),
            creado_en=fila["creado_en"],
        )
