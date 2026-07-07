"""
CAPA: PRESENTATION (Presentacion) - Rutas de Perfil
=======================================================
Permite que el usuario autenticado (cualquier rol) configure su
propio correo de notificaciones desde la pantalla de Configuracion,
sin depender de un administrador.
"""

from flask import Blueprint, g, jsonify, request

from application.use_cases.gestionar_perfil import ActualizarCorreoUsuarioCasoDeUso
from domain.exceptions import CorreoInvalidoError


def crear_blueprint_perfil(caso_actualizar_correo: ActualizarCorreoUsuarioCasoDeUso, token_requerido) -> Blueprint:
    blueprint = Blueprint("perfil", __name__, url_prefix="/api/perfil")

    @blueprint.route("/correo", methods=["PATCH"])
    @token_requerido
    def actualizar_correo():
        usuario_id = int(g.usuario_actual["sub"])
        datos = request.get_json(silent=True) or {}
        correo = datos.get("correo", "")

        try:
            caso_actualizar_correo.ejecutar(usuario_id, correo)
        except CorreoInvalidoError as error:
            return jsonify({"error": str(error)}), 400

        return jsonify({"mensaje": "Correo de notificaciones actualizado correctamente", "correo": correo.strip()}), 200

    return blueprint
