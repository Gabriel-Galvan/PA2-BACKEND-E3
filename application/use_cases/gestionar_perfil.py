"""
CAPA: APPLICATION (Aplicacion) - Caso de uso: Perfil del usuario
===================================================================
Permite que cada medico (o admin) configure su propio correo de
notificaciones desde la pantalla de Configuracion, sin necesitar
intervencion de un administrador. Ese correo es el que se usa para
avisar que un analisis de expediente termino con exito.
"""

from __future__ import annotations

import re

from domain.exceptions import CorreoInvalidoError
from domain.repositories import RepositorioUsuarios

_PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ActualizarCorreoUsuarioCasoDeUso:
    def __init__(self, repo_usuarios: RepositorioUsuarios):
        self._repo_usuarios = repo_usuarios

    def ejecutar(self, usuario_id: int, correo: str) -> bool:
        correo = (correo or "").strip()
        if not _PATRON_CORREO.match(correo):
            raise CorreoInvalidoError("El correo ingresado no tiene un formato valido")
        return self._repo_usuarios.actualizar_correo(usuario_id, correo)
