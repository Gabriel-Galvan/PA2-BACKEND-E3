"""
CAPA: INFRASTRUCTURE (Infraestructura) - Persistencia
========================================================
Implementacion CONCRETA del puerto `RepositorioUsuarios` (definido en
domain/repositories.py) usando SQLite. Esta es la unica parte del
sistema que sabe escribir SQL.

La base de datos se crea con database/schema.sql, que ya inserta un
usuario administrador de prueba:
    usuario:     admin
    contrasena:  1234

(la contrasena se guarda hasheada, nunca en texto plano, ver
infrastructure/security/auth_service.py)
"""

import sqlite3
from datetime import datetime

from domain.entities import RolUsuario, Usuario
from domain.repositories import RepositorioUsuarios


class RepositorioUsuariosSQLite(RepositorioUsuarios):
    def __init__(self, ruta_db: str):
        self._ruta_db = ruta_db

    def _conectar(self) -> sqlite3.Connection:
        conexion = sqlite3.connect(self._ruta_db)
        conexion.row_factory = sqlite3.Row
        return conexion

    def obtener_por_nombre_usuario(self, nombre_usuario: str) -> Usuario | None:
        with self._conectar() as conexion:
            fila = conexion.execute(
                "SELECT id, nombre_usuario, password_hash, rol, activo, creado_en "
                "FROM usuarios WHERE nombre_usuario = ?",
                (nombre_usuario,),
            ).fetchone()
        return self._fila_a_entidad(fila) if fila else None

    def listar_todos(self) -> list[Usuario]:
        with self._conectar() as conexion:
            filas = conexion.execute(
                "SELECT id, nombre_usuario, password_hash, rol, activo, creado_en "
                "FROM usuarios ORDER BY id"
            ).fetchall()
        return [self._fila_a_entidad(f) for f in filas]

    def crear(self, nombre_usuario: str, password_hash: str, rol: RolUsuario) -> Usuario:
        creado_en = datetime.utcnow().isoformat()
        with self._conectar() as conexion:
            cursor = conexion.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, rol, activo, creado_en) "
                "VALUES (?, ?, ?, 1, ?)",
                (nombre_usuario, password_hash, rol.value, creado_en),
            )
            conexion.commit()
            nuevo_id = cursor.lastrowid
        return Usuario(
            id=nuevo_id,
            nombre_usuario=nombre_usuario,
            password_hash=password_hash,
            rol=rol,
            activo=True,
            creado_en=datetime.fromisoformat(creado_en),
        )

    def eliminar(self, usuario_id: int) -> bool:
        with self._conectar() as conexion:
            cursor = conexion.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
            conexion.commit()
        return cursor.rowcount > 0

    def cambiar_estado(self, usuario_id: int, activo: bool) -> bool:
        with self._conectar() as conexion:
            cursor = conexion.execute(
                "UPDATE usuarios SET activo = ? WHERE id = ?", (1 if activo else 0, usuario_id)
            )
            conexion.commit()
        return cursor.rowcount > 0

    @staticmethod
    def _fila_a_entidad(fila: sqlite3.Row) -> Usuario:
        return Usuario(
            id=fila["id"],
            nombre_usuario=fila["nombre_usuario"],
            password_hash=fila["password_hash"],
            rol=RolUsuario(fila["rol"]),
            activo=bool(fila["activo"]),
            creado_en=datetime.fromisoformat(fila["creado_en"]) if fila["creado_en"] else None,
        )