"""
CAPA: APPLICATION (Aplicacion) - Casos de uso: Gestion de usuarios
=====================================================================
Cubre el requerimiento del cronograma de Backend (Sesion 09-12):
"funcionalidades administrativas, como mantenimiento, gestion de
usuarios, permisos [...] al proyecto."

De momento estos casos de uso solo administran la tabla `usuarios`
de SQLite (login). La persistencia del HISTORIAL de analisis
(PB-12, base de datos relacional completa con historial por medico)
queda fuera de alcance por ahora, tal como se acordo: se
implementara en una siguiente iteracion del proyecto.
"""

from domain.entities import RolUsuario, Usuario
from domain.exceptions import UsuarioYaExisteError
from domain.repositories import RepositorioUsuarios, ServicioAutenticacion


class ListarUsuariosCasoDeUso:
    """Lista todos los usuarios registrados (vista de administracion)."""

    def __init__(self, repo_usuarios: RepositorioUsuarios):
        self._repo_usuarios = repo_usuarios

    def ejecutar(self) -> list[Usuario]:
        return self._repo_usuarios.listar_todos()


class CrearUsuarioCasoDeUso:
    """Crea un nuevo usuario (personal de salud o administrador)."""

    def __init__(self, repo_usuarios: RepositorioUsuarios, auth_service: ServicioAutenticacion):
        self._repo_usuarios = repo_usuarios
        self._auth_service = auth_service

    def ejecutar(self, nombre_usuario: str, password_plano: str, rol: RolUsuario) -> Usuario:
        if self._repo_usuarios.obtener_por_nombre_usuario(nombre_usuario) is not None:
            raise UsuarioYaExisteError(f"El usuario '{nombre_usuario}' ya existe")

        password_hash = self._auth_service.hashear_password(password_plano)
        return self._repo_usuarios.crear(nombre_usuario, password_hash, rol)


class EliminarUsuarioCasoDeUso:
    """Elimina un usuario (mantenimiento administrativo)."""

    def __init__(self, repo_usuarios: RepositorioUsuarios):
        self._repo_usuarios = repo_usuarios

    def ejecutar(self, usuario_id: int) -> bool:
        return self._repo_usuarios.eliminar(usuario_id)


class CambiarEstadoUsuarioCasoDeUso:
    """Activa o desactiva un usuario (control de permisos/acceso)."""

    def __init__(self, repo_usuarios: RepositorioUsuarios):
        self._repo_usuarios = repo_usuarios

    def ejecutar(self, usuario_id: int, activo: bool) -> bool:
        return self._repo_usuarios.cambiar_estado(usuario_id, activo)