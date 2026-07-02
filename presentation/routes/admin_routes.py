"""
CAPA: PRESENTATION (Presentacion) - Rutas administrativas
=============================================================
Cubre el requerimiento del cronograma: "El backend debera incluir
funcionalidades administrativas, como mantenimiento, gestion de
usuarios, permisos u otras funciones pertinentes al proyecto."

Todas las rutas de este blueprint requieren estar autenticado
(@token_requerido) y tener el rol "admin" (@rol_requerido("admin")).
"""

from flask import Blueprint, jsonify, request

from application.use_cases.gestionar_usuarios import (
    CambiarEstadoUsuarioCasoDeUso,
    CrearUsuarioCasoDeUso,
    EliminarUsuarioCasoDeUso,
    ListarUsuariosCasoDeUso,
)
from domain.entities import RolUsuario
from domain.exceptions import UsuarioYaExisteError


def crear_blueprint_admin(
    caso_listar: ListarUsuariosCasoDeUso,
    caso_crear: CrearUsuarioCasoDeUso,
    caso_eliminar: EliminarUsuarioCasoDeUso,
    caso_cambiar_estado: CambiarEstadoUsuarioCasoDeUso,
    token_requerido,
    rol_requerido,
) -> Blueprint:
    blueprint = Blueprint("admin", __name__, url_prefix="/api/admin")

    @blueprint.route("/usuarios", methods=["GET"])
    @token_requerido
    @rol_requerido("admin")
    def listar_usuarios():
        usuarios = caso_listar.ejecutar()
        return jsonify([
            {
                "id": u.id,
                "nombre_usuario": u.nombre_usuario,
                "rol": u.rol.value,
                "activo": u.activo,
                "creado_en": u.creado_en.isoformat() if u.creado_en else None,
            }
            for u in usuarios
        ]), 200

    @blueprint.route("/usuarios", methods=["POST"])
    @token_requerido
    @rol_requerido("admin")
    def crear_usuario():
        datos = request.get_json(silent=True) or {}
        nombre_usuario = (datos.get("nombre_usuario") or "").strip()
        password = datos.get("contrasena") or ""
        rol_str = datos.get("rol", RolUsuario.MEDICO.value)

        if not nombre_usuario or not password:
            return jsonify({"error": "nombre_usuario y contrasena son obligatorios"}), 400

        try:
            rol = RolUsuario(rol_str)
        except ValueError:
            return jsonify({"error": f"Rol invalido: {rol_str}"}), 400

        try:
            usuario = caso_crear.ejecutar(nombre_usuario, password, rol)
        except UsuarioYaExisteError as error:
            return jsonify({"error": str(error)}), 409

        return jsonify({
            "id": usuario.id,
            "nombre_usuario": usuario.nombre_usuario,
            "rol": usuario.rol.value,
            "activo": usuario.activo,
        }), 201

    @blueprint.route("/usuarios/<int:usuario_id>", methods=["DELETE"])
    @token_requerido
    @rol_requerido("admin")
    def eliminar_usuario(usuario_id: int):
        eliminado = caso_eliminar.ejecutar(usuario_id)
        if not eliminado:
            return jsonify({"error": "Usuario no encontrado"}), 404
        return jsonify({"mensaje": "Usuario eliminado correctamente"}), 200

    @blueprint.route("/usuarios/<int:usuario_id>/estado", methods=["PATCH"])
    @token_requerido
    @rol_requerido("admin")
    def cambiar_estado_usuario(usuario_id: int):
        datos = request.get_json(silent=True) or {}
        activo = bool(datos.get("activo", True))
        actualizado = caso_cambiar_estado.ejecutar(usuario_id, activo)
        if not actualizado:
            return jsonify({"error": "Usuario no encontrado"}), 404
        return jsonify({"mensaje": "Estado actualizado correctamente", "activo": activo}), 200

    return blueprint