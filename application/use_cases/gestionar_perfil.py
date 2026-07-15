"""
CAPA: APPLICATION (Aplicacion) - Caso de uso: Perfil del usuario
===================================================================
Permite que cada medico (o admin) configure su propio correo de
notificaciones desde la pantalla de Configuracion, sin necesitar
intervencion de un administrador. Ese correo es el que se usa para
avisar que un analisis de expediente termino con exito.
"""

from __future__ import annotations

import base64
import re

from domain.exceptions import (
    CorreoInvalidoError,
    ImagenInvalidaError,
    NombreUsuarioInvalidoError,
    UsuarioYaExisteError,
)
from domain.repositories import RepositorioUsuarios

_PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PATRON_NOMBRE_USUARIO = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
_TIPOS_MIME_PERMITIDOS = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_TAMANO_MAXIMO_AVATAR_BYTES = 2 * 1024 * 1024  # 2 MB, de sobra para una foto de perfil


class ActualizarCorreoUsuarioCasoDeUso:
    def __init__(self, repo_usuarios: RepositorioUsuarios):
        self._repo_usuarios = repo_usuarios

    def ejecutar(self, usuario_id: int, correo: str) -> bool:
        correo = (correo or "").strip()
        if not _PATRON_CORREO.match(correo):
            raise CorreoInvalidoError("El correo ingresado no tiene un formato valido")
        return self._repo_usuarios.actualizar_correo(usuario_id, correo)


class ActualizarAvatarUsuarioCasoDeUso:
    """
    Guarda la foto de perfil del usuario para que persista entre
    sesiones y dispositivos (antes solo vivia como blob local en el
    navegador y se perdia al recargar la pagina o cerrar sesion).
    Se guarda como data URL base64 en la propia tabla `usuarios`,
    igual criterio que la imagen de un expediente.
    """

    def __init__(self, repo_usuarios: RepositorioUsuarios):
        self._repo_usuarios = repo_usuarios

    def ejecutar(self, usuario_id: int, bytes_imagen: bytes, mime_type: str) -> str:
        if not bytes_imagen:
            raise ImagenInvalidaError("No se recibio ninguna imagen")
        if mime_type not in _TIPOS_MIME_PERMITIDOS:
            raise ImagenInvalidaError("El archivo debe ser una imagen JPG, PNG, WEBP o GIF")
        if len(bytes_imagen) > _TAMANO_MAXIMO_AVATAR_BYTES:
            raise ImagenInvalidaError("La imagen es demasiado pesada (maximo 2 MB)")

        avatar_base64 = f"data:{mime_type};base64," + base64.b64encode(bytes_imagen).decode("ascii")
        self._repo_usuarios.actualizar_avatar(usuario_id, avatar_base64)
        return avatar_base64

    def eliminar(self, usuario_id: int) -> None:
        self._repo_usuarios.actualizar_avatar(usuario_id, None)


class ActualizarNombreUsuarioCasoDeUso:
    """Permite que el propio usuario cambie su nombre de usuario desde Configuracion."""

    def __init__(self, repo_usuarios: RepositorioUsuarios):
        self._repo_usuarios = repo_usuarios

    def ejecutar(self, usuario_id: int, nuevo_nombre_usuario: str) -> str:
        nuevo_nombre_usuario = (nuevo_nombre_usuario or "").strip()
        if not _PATRON_NOMBRE_USUARIO.match(nuevo_nombre_usuario):
            raise NombreUsuarioInvalidoError(
                "El nombre de usuario debe tener entre 3 y 32 caracteres "
                "(letras, numeros, puntos, guiones o guion bajo, sin espacios)"
            )

        existente = self._repo_usuarios.obtener_por_nombre_usuario(nuevo_nombre_usuario)
        if existente is not None and existente.id != usuario_id:
            raise UsuarioYaExisteError(f"El usuario '{nuevo_nombre_usuario}' ya existe")

        self._repo_usuarios.actualizar_nombre_usuario(usuario_id, nuevo_nombre_usuario)
        return nuevo_nombre_usuario
