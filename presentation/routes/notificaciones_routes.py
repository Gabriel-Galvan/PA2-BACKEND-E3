"""
CAPA: PRESENTATION (Presentacion) - Rutas de Notificaciones
===============================================================
Alimenta la 'campanita' de la interfaz: cada usuario autenticado ve
SOLO sus propias notificaciones (control de accesos igual que
Expedientes: el repositorio ya filtra por usuario_id).
"""

from flask import Blueprint, g, jsonify, request

from application.use_cases.gestionar_notificaciones import (
    ListarNotificacionesCasoDeUso,
    MarcarNotificacionLeidaCasoDeUso,
    MarcarTodasNotificacionesLeidasCasoDeUso,
)


def crear_blueprint_notificaciones(
    caso_listar: ListarNotificacionesCasoDeUso,
    caso_marcar_leida: MarcarNotificacionLeidaCasoDeUso,
    caso_marcar_todas_leidas: MarcarTodasNotificacionesLeidasCasoDeUso,
    token_requerido,
) -> Blueprint:
    blueprint = Blueprint("notificaciones", __name__, url_prefix="/api/notificaciones")

    @blueprint.route("", methods=["GET"])
    @token_requerido
    def listar():
        usuario_id = int(g.usuario_actual["sub"])
        limite = request.args.get("limite", default=30, type=int)
        notificaciones, no_leidas = caso_listar.ejecutar(usuario_id, limite)
        return jsonify({
            "notificaciones": [n.a_diccionario() for n in notificaciones],
            "no_leidas": no_leidas,
        }), 200

    @blueprint.route("/<int:notificacion_id>/leer", methods=["PATCH"])
    @token_requerido
    def marcar_leida(notificacion_id: int):
        usuario_id = int(g.usuario_actual["sub"])
        actualizado = caso_marcar_leida.ejecutar(notificacion_id, usuario_id)
        if not actualizado:
            return jsonify({"error": "Notificacion no encontrada"}), 404
        return jsonify({"mensaje": "Notificacion marcada como leida"}), 200

    @blueprint.route("/leer-todas", methods=["PATCH"])
    @token_requerido
    def marcar_todas_leidas():
        usuario_id = int(g.usuario_actual["sub"])
        caso_marcar_todas_leidas.ejecutar(usuario_id)
        return jsonify({"mensaje": "Todas las notificaciones marcadas como leidas"}), 200

    return blueprint
