"""
CAPA: APPLICATION (Aplicacion) - Casos de uso: Notificaciones in-app
=======================================================================
Alimenta la 'campanita' de la interfaz: notificaciones para el medico
cuando un expediente propio termina de analizarse, y para los
administradores cuando se genera un codigo de invitacion.
"""

from __future__ import annotations

from domain.entities import Notificacion
from domain.repositories import RepositorioNotificaciones


class ListarNotificacionesCasoDeUso:
    def __init__(self, repo_notificaciones: RepositorioNotificaciones):
        self._repo_notificaciones = repo_notificaciones

    def ejecutar(self, usuario_id: int, limite: int = 30) -> tuple[list[Notificacion], int]:
        notificaciones = self._repo_notificaciones.listar_por_usuario(usuario_id, limite)
        no_leidas = self._repo_notificaciones.contar_no_leidas(usuario_id)
        return notificaciones, no_leidas


class MarcarNotificacionLeidaCasoDeUso:
    def __init__(self, repo_notificaciones: RepositorioNotificaciones):
        self._repo_notificaciones = repo_notificaciones

    def ejecutar(self, notificacion_id: int, usuario_id: int) -> bool:
        return self._repo_notificaciones.marcar_leida(notificacion_id, usuario_id)


class MarcarTodasNotificacionesLeidasCasoDeUso:
    def __init__(self, repo_notificaciones: RepositorioNotificaciones):
        self._repo_notificaciones = repo_notificaciones

    def ejecutar(self, usuario_id: int) -> bool:
        return self._repo_notificaciones.marcar_todas_leidas(usuario_id)
