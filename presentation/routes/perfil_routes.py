"""
CAPA: PRESENTATION (Presentacion) - Rutas de Perfil
=======================================================
Permite que el usuario autenticado (cualquier rol) configure su
propio correo de notificaciones, foto de perfil y nombre de usuario
desde la pantalla de Configuracion, sin depender de un administrador.
"""

from flask import Blueprint, g, jsonify, request

from application.use_cases.gestionar_perfil import (
    ActualizarAvatarUsuarioCasoDeUso,
    ActualizarCorreoUsuarioCasoDeUso,
    ActualizarNombreUsuarioCasoDeUso,
)
from domain.exceptions import CorreoInvalidoError, ImagenInvalidaError, NombreUsuarioInvalidoError, UsuarioYaExisteError


def crear_blueprint_perfil(
    caso_actualizar_correo: ActualizarCorreoUsuarioCasoDeUso,
    caso_actualizar_avatar: ActualizarAvatarUsuarioCasoDeUso,
    caso_actualizar_nombre_usuario: ActualizarNombreUsuarioCasoDeUso,
    token_requerido,
) -> Blueprint:
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

    @blueprint.route("/avatar", methods=["POST"])
    @token_requerido
    def actualizar_avatar():
        usuario_id = int(g.usuario_actual["sub"])
        if "avatar" not in request.files:
            return jsonify({"error": "No se recibio ninguna imagen"}), 400

        archivo = request.files["avatar"]
        try:
            avatar_base64 = caso_actualizar_avatar.ejecutar(
                usuario_id, archivo.read(), archivo.mimetype or ""
            )
        except ImagenInvalidaError as error:
            return jsonify({"error": str(error)}), 400

        return jsonify({"mensaje": "Foto de perfil actualizada correctamente", "avatar_base64": avatar_base64}), 200

    @blueprint.route("/avatar", methods=["DELETE"])
    @token_requerido
    def eliminar_avatar():
        usuario_id = int(g.usuario_actual["sub"])
        caso_actualizar_avatar.eliminar(usuario_id)
        return jsonify({"mensaje": "Foto de perfil eliminada correctamente"}), 200

    @blueprint.route("/nombre-usuario", methods=["PATCH"])
    @token_requerido
    def actualizar_nombre_usuario():
        usuario_id = int(g.usuario_actual["sub"])
        datos = request.get_json(silent=True) or {}
        nuevo_nombre_usuario = datos.get("nombre_usuario", "")

        try:
            nombre_final = caso_actualizar_nombre_usuario.ejecutar(usuario_id, nuevo_nombre_usuario)
        except NombreUsuarioInvalidoError as error:
            return jsonify({"error": str(error)}), 400
        except UsuarioYaExisteError as error:
            return jsonify({"error": str(error)}), 409

        return jsonify({
            "mensaje": "Nombre de usuario actualizado correctamente",
            "nombre_usuario": nombre_final,
        }), 200

    return blueprint
