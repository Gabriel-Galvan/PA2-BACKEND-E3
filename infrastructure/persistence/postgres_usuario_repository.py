"""
CAPA: INFRASTRUCTURE (Infraestructura) - Persistencia
========================================================
Implementacion CONCRETA del puerto `RepositorioUsuarios` (definido en
domain/repositories.py) usando PostgreSQL (Render Postgres).

Es un reemplazo directo de sqlite_usuario_repository.py: mismo
contrato, misma forma de uso desde app.py, solo cambia el motor de
base de datos. Gracias a la Clean Architecture, ningun caso de uso
(application/) ni ninguna ruta (presentation/) tuvo que cambiar.
"""

from datetime import datetime

import psycopg2
import psycopg2.extras

from domain.entities import RolUsuario, Usuario
from domain.repositories import RepositorioUsuarios


class RepositorioUsuariosPostgres(RepositorioUsuarios):
    def __init__(self, database_url: str):
        # Render entrega URLs tipo postgres://..., psycopg2 requiere postgresql://
        self._database_url = database_url.replace("postgres://", "postgresql://", 1)

    def _conectar(self):
        return psycopg2.connect(self._database_url)

    def obtener_por_nombre_usuario(self, nombre_usuario: str) -> Usuario | None:
        with self._conectar() as conexion:
            with conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    "SELECT id, nombre_usuario, password_hash, rol, activo, creado_en, correo, avatar_base64 "
                    "FROM usuarios WHERE nombre_usuario = %s",
                    (nombre_usuario,),
                )
                fila = cursor.fetchone()
        return self._fila_a_entidad(fila) if fila else None

    def obtener_por_id(self, usuario_id: int) -> Usuario | None:
        with self._conectar() as conexion:
            with conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    "SELECT id, nombre_usuario, password_hash, rol, activo, creado_en, correo, avatar_base64 "
                    "FROM usuarios WHERE id = %s",
                    (usuario_id,),
                )
                fila = cursor.fetchone()
        return self._fila_a_entidad(fila) if fila else None

    def listar_todos(self) -> list[Usuario]:
        with self._conectar() as conexion:
            with conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    "SELECT id, nombre_usuario, password_hash, rol, activo, creado_en, correo, avatar_base64 "
                    "FROM usuarios ORDER BY id"
                )
                filas = cursor.fetchall()
        return [self._fila_a_entidad(f) for f in filas]

    def crear(
        self,
        nombre_usuario: str,
        password_hash: str,
        rol: RolUsuario,
        correo: str | None = None,
    ) -> Usuario:
        creado_en = datetime.utcnow()
        with self._conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO usuarios (nombre_usuario, password_hash, rol, activo, creado_en, correo) "
                    "VALUES (%s, %s, %s, TRUE, %s, %s) RETURNING id",
                    (nombre_usuario, password_hash, rol.value, creado_en, correo),
                )
                nuevo_id = cursor.fetchone()[0]
            conexion.commit()
        return Usuario(
            id=nuevo_id,
            nombre_usuario=nombre_usuario,
            password_hash=password_hash,
            rol=rol,
            activo=True,
            creado_en=creado_en,
            correo=correo,
        )

    def eliminar(self, usuario_id: int) -> bool:
        with self._conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("DELETE FROM usuarios WHERE id = %s", (usuario_id,))
                filas_afectadas = cursor.rowcount
            conexion.commit()
        return filas_afectadas > 0

    def cambiar_estado(self, usuario_id: int, activo: bool) -> bool:
        with self._conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "UPDATE usuarios SET activo = %s WHERE id = %s", (activo, usuario_id)
                )
                filas_afectadas = cursor.rowcount
            conexion.commit()
        return filas_afectadas > 0

    def actualizar_correo(self, usuario_id: int, correo: str) -> bool:
        with self._conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "UPDATE usuarios SET correo = %s WHERE id = %s", (correo, usuario_id)
                )
                filas_afectadas = cursor.rowcount
            conexion.commit()
        return filas_afectadas > 0

    def actualizar_avatar(self, usuario_id: int, avatar_base64: str | None) -> bool:
        with self._conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "UPDATE usuarios SET avatar_base64 = %s WHERE id = %s", (avatar_base64, usuario_id)
                )
                filas_afectadas = cursor.rowcount
            conexion.commit()
        return filas_afectadas > 0

    def actualizar_nombre_usuario(self, usuario_id: int, nombre_usuario: str) -> bool:
        with self._conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "UPDATE usuarios SET nombre_usuario = %s WHERE id = %s", (nombre_usuario, usuario_id)
                )
                filas_afectadas = cursor.rowcount
            conexion.commit()
        return filas_afectadas > 0

    @staticmethod
    def _fila_a_entidad(fila) -> Usuario:
        return Usuario(
            id=fila["id"],
            nombre_usuario=fila["nombre_usuario"],
            password_hash=fila["password_hash"],
            rol=RolUsuario(fila["rol"]),
            activo=bool(fila["activo"]),
            creado_en=fila["creado_en"],
            correo=fila.get("correo"),
            avatar_base64=fila.get("avatar_base64"),
        )
