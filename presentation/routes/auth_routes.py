"""
CAPA: PRESENTATION (Presentacion) - Rutas de autenticacion
=============================================================
Endpoint REST de login exigido por el cronograma (Sesion 08):
POST /api/auth/login

Esta capa SOLO se encarga de:
  1. Leer la peticion HTTP (JSON).
  2. Llamar al caso de uso de application/.
  3. Traducir el resultado (o la excepcion de dominio) a JSON + codigo HTTP.
NUNCA contiene logica de negocio: eso vive en application/use_cases.
"""

from flask import Blueprint, jsonify, request

from application.use_cases.autenticar_usuario import AutenticarUsuarioCasoDeUso
from application.use_cases.gestionar_codigos import RegistrarUsuarioConCodigoCasoDeUso
from domain.exceptions import (
    CodigoInvitacionInvalidoError,
    CorreoInvalidoError,
    CredencialesInvalidasError,
    NombreUsuarioInvalidoError,
    UsuarioInactivoError,
    UsuarioYaExisteError,
)


def crear_blueprint_auth(
    caso_de_uso_autenticar: AutenticarUsuarioCasoDeUso,
    caso_de_uso_registrar: RegistrarUsuarioConCodigoCasoDeUso,
) -> Blueprint:
    blueprint = Blueprint("auth", __name__, url_prefix="/api/auth")

    @blueprint.route("/login", methods=["POST"])
    def login():
        datos = request.get_json(silent=True) or {}
        nombre_usuario = (datos.get("usuario") or "").strip()
        password = datos.get("contrasena") or ""

        if not nombre_usuario or not password:
            return jsonify({"error": "Usuario y contrasena son obligatorios"}), 400

        try:
            usuario, token = caso_de_uso_autenticar.ejecutar(nombre_usuario, password)
        except CredencialesInvalidasError as error:
            return jsonify({"error": str(error)}), 401
        except UsuarioInactivoError as error:
            return jsonify({"error": str(error)}), 403

        return jsonify({
            "token": token,
            "usuario": {
                "id": usuario.id,
                "nombre_usuario": usuario.nombre_usuario,
                "rol": usuario.rol.value,
                "correo": usuario.correo,
                "avatar_base64": usuario.avatar_base64,
            },
        }), 200

    @blueprint.route("/registro", methods=["POST"])
    def registro():
        """
        Auto-registro publico de un nuevo medico, protegido por un
        codigo de invitacion de un solo uso (ver Configuracion > Gestion
        de Usuarios, donde un admin genera el codigo). El usuario
        siempre queda con rol 'medico'.
        """
        datos = request.get_json(silent=True) or {}
        nombre_usuario = datos.get("nombre_usuario") or ""
        password = datos.get("contrasena") or ""
        correo = datos.get("correo") or ""
        codigo = datos.get("codigo") or ""

        try:
            usuario = caso_de_uso_registrar.ejecutar(nombre_usuario, password, correo, codigo)
        except (NombreUsuarioInvalidoError, CorreoInvalidoError) as error:
            return jsonify({"error": str(error)}), 400
        except CodigoInvitacionInvalidoError as error:
            return jsonify({"error": str(error)}), 400
        except UsuarioYaExisteError as error:
            return jsonify({"error": str(error)}), 409

        return jsonify({
            "mensaje": "Cuenta creada correctamente. Ya puedes iniciar sesion.",
            "usuario": {
                "id": usuario.id,
                "nombre_usuario": usuario.nombre_usuario,
                "rol": usuario.rol.value,
            },
        }), 201

    return blueprint