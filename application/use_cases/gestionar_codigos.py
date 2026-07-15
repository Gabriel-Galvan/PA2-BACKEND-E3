"""
CAPA: APPLICATION (Aplicacion) - Casos de uso: Codigos de invitacion
=======================================================================
Permite que un administrador genere codigos de invitacion de un solo
uso, y que un nuevo medico se auto-registre canjeando uno de esos
codigos (POST /api/auth/registro, publico). El codigo generado se
entrega al administrador como una Notificacion in-app (la 'campanita'),
no por correo: es el propio administrador quien luego se lo comparte
al nuevo medico por el canal que prefiera.
"""

from __future__ import annotations

import re
import secrets
import string

from domain.entities import CodigoInvitacion, RolUsuario, Usuario
from domain.exceptions import (
    CodigoInvitacionInvalidoError,
    CorreoInvalidoError,
    NombreUsuarioInvalidoError,
    UsuarioYaExisteError,
)
from domain.repositories import (
    RepositorioCodigosInvitacion,
    RepositorioNotificaciones,
    RepositorioUsuarios,
    ServicioAutenticacion,
)

_ALFABETO_CODIGO = string.ascii_uppercase.replace("O", "").replace("I", "") + "".join(
    d for d in string.digits if d not in "01"
)  # sin O/0/I/1 para que no se confundan al leerlos/tipearlos a mano
_LONGITUD_CODIGO = 8
_PATRON_NOMBRE_USUARIO = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
_PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _generar_codigo_aleatorio() -> str:
    return "".join(secrets.choice(_ALFABETO_CODIGO) for _ in range(_LONGITUD_CODIGO))


class GenerarCodigoInvitacionCasoDeUso:
    """Genera un codigo de invitacion nuevo y notifica al/los administrador(es)."""

    def __init__(
        self,
        repo_codigos: RepositorioCodigosInvitacion,
        repo_notificaciones: RepositorioNotificaciones,
    ):
        self._repo_codigos = repo_codigos
        self._repo_notificaciones = repo_notificaciones

    def ejecutar(self, admin_id: int) -> CodigoInvitacion:
        codigo = _generar_codigo_aleatorio()
        # Coincidencia practicamente imposible con este alfabeto/longitud,
        # pero por las dudas se reintenta si el codigo ya existiera.
        while self._repo_codigos.obtener_por_codigo(codigo) is not None:
            codigo = _generar_codigo_aleatorio()

        codigo_creado = self._repo_codigos.crear(codigo, admin_id)

        self._repo_notificaciones.crear_para_admins(
            tipo="codigo_invitacion",
            titulo="Nuevo codigo de invitacion generado",
            mensaje=(
                f"Codigo: {codigo_creado.codigo}. Entregaselo al nuevo medico para que "
                "pueda crear su cuenta desde la pantalla de registro."
            ),
            referencia_id=codigo_creado.id,
        )
        return codigo_creado


class RegistrarUsuarioConCodigoCasoDeUso:
    """
    Auto-registro publico de un nuevo medico, protegido por un codigo
    de invitacion de un solo uso generado previamente por un admin.
    El usuario creado siempre queda con rol 'medico' (nunca 'admin':
    para dar de alta administradores sigue existiendo el panel de
    Gestion de Usuarios, que requiere ya estar autenticado como admin).
    """

    def __init__(
        self,
        repo_usuarios: RepositorioUsuarios,
        repo_codigos: RepositorioCodigosInvitacion,
        auth_service: ServicioAutenticacion,
    ):
        self._repo_usuarios = repo_usuarios
        self._repo_codigos = repo_codigos
        self._auth_service = auth_service

    def ejecutar(
        self,
        nombre_usuario: str,
        password_plano: str,
        correo: str,
        codigo: str,
    ) -> Usuario:
        nombre_usuario = (nombre_usuario or "").strip()
        correo = (correo or "").strip()
        codigo = (codigo or "").strip().upper()

        if not _PATRON_NOMBRE_USUARIO.match(nombre_usuario):
            raise NombreUsuarioInvalidoError(
                "El nombre de usuario debe tener entre 3 y 32 caracteres "
                "(letras, numeros, puntos, guiones o guion bajo, sin espacios)"
            )
        if not password_plano or len(password_plano) < 4:
            raise NombreUsuarioInvalidoError("La contrasena debe tener al menos 4 caracteres")
        if not _PATRON_CORREO.match(correo):
            raise CorreoInvalidoError("El correo ingresado no tiene un formato valido")
        if not codigo:
            raise CodigoInvitacionInvalidoError("El codigo de invitacion es obligatorio")

        codigo_entidad = self._repo_codigos.obtener_por_codigo(codigo)
        if codigo_entidad is None:
            raise CodigoInvitacionInvalidoError("El codigo de invitacion no existe")
        if codigo_entidad.usado:
            raise CodigoInvitacionInvalidoError("Este codigo de invitacion ya fue utilizado")

        if self._repo_usuarios.obtener_por_nombre_usuario(nombre_usuario) is not None:
            raise UsuarioYaExisteError(f"El usuario '{nombre_usuario}' ya existe")

        password_hash = self._auth_service.hashear_password(password_plano)
        usuario_creado = self._repo_usuarios.crear(
            nombre_usuario, password_hash, RolUsuario.MEDICO, correo or None
        )
        self._repo_codigos.marcar_usado(codigo_entidad.id, usuario_creado.id)
        return usuario_creado
