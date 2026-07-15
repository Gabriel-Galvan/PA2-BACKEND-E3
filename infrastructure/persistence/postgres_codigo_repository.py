"""
CAPA: INFRASTRUCTURE (Infraestructura) - Persistencia
========================================================
Implementacion CONCRETA del puerto `RepositorioCodigosInvitacion`
usando PostgreSQL (Render Postgres). Espejo de
sqlite_codigo_repository.py.
"""

import psycopg2
import psycopg2.extras

from domain.entities import CodigoInvitacion
from domain.repositories import RepositorioCodigosInvitacion

_COLUMNAS = "id, codigo, creado_por, usado, usado_por, creado_en, usado_en"


class RepositorioCodigosInvitacionPostgres(RepositorioCodigosInvitacion):
    def __init__(self, database_url: str):
        self._database_url = database_url.replace("postgres://", "postgresql://", 1)

    def _conectar(self):
        return psycopg2.connect(self._database_url)

    def crear(self, codigo: str, creado_por: int) -> CodigoInvitacion:
        with self._conectar() as conexion:
            with conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    f"INSERT INTO codigos_invitacion (codigo, creado_por, usado, creado_en) "
                    f"VALUES (%s, %s, FALSE, NOW()) RETURNING {_COLUMNAS}",
                    (codigo, creado_por),
                )
                fila = cursor.fetchone()
            conexion.commit()
        return self._fila_a_entidad(fila)

    def obtener_por_codigo(self, codigo: str) -> CodigoInvitacion | None:
        with self._conectar() as conexion:
            with conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(f"SELECT {_COLUMNAS} FROM codigos_invitacion WHERE codigo = %s", (codigo,))
                fila = cursor.fetchone()
        return self._fila_a_entidad(fila) if fila else None

    def marcar_usado(self, codigo_id: int, usuario_id: int) -> bool:
        with self._conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "UPDATE codigos_invitacion SET usado = TRUE, usado_por = %s, usado_en = NOW() "
                    "WHERE id = %s AND usado = FALSE",
                    (usuario_id, codigo_id),
                )
                filas_afectadas = cursor.rowcount
            conexion.commit()
        return filas_afectadas > 0

    def listar_todos(self) -> list[CodigoInvitacion]:
        with self._conectar() as conexion:
            with conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(f"SELECT {_COLUMNAS} FROM codigos_invitacion ORDER BY creado_en DESC")
                filas = cursor.fetchall()
        return [self._fila_a_entidad(f) for f in filas]

    @staticmethod
    def _fila_a_entidad(fila) -> CodigoInvitacion:
        return CodigoInvitacion(
            id=fila["id"],
            codigo=fila["codigo"],
            creado_por=fila["creado_por"],
            usado=bool(fila["usado"]),
            usado_por=fila.get("usado_por"),
            creado_en=fila["creado_en"],
            usado_en=fila.get("usado_en"),
        )
