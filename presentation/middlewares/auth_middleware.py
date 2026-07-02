"""
CAPA: PRESENTATION (Presentacion) - Middleware de autenticacion
==================================================================
Decorador `@token_requerido` que protege los endpoints de la API.
Lee el header "Authorization: Bearer <token>", lo valida con el
ServicioAutenticacion (JWT) y, si es valido, inyecta los datos del
usuario autenticado en `request.usuario_actual` para que la ruta los
use (por ejemplo, para revisar el rol en `@rol_requerido`).
"""

from functools import wraps

from flask import g, jsonify, request

from domain.repositories import ServicioAutenticacion


def crear_decorador_token_requerido(auth_service: ServicioAutenticacion):
    """
    Fabrica del decorador. Se construye una vez en app.py pasandole el
    auth_service ya configurado (inyeccion de dependencias manual),
    y el resultado se reutiliza en todas las rutas protegidas.
    """

    def token_requerido(funcion):
        @wraps(funcion)
        def envoltura(*args, **kwargs):
            encabezado = request.headers.get("Authorization", "")

            if not encabezado.startswith("Bearer "):
                return jsonify({"error": "Falta el token de autenticacion (Authorization: Bearer <token>)"}), 401

            token = encabezado.split(" ", 1)[1].strip()
            payload = auth_service.validar_token(token)

            if payload is None:
                return jsonify({"error": "Token invalido o expirado. Vuelve a iniciar sesion."}), 401

            g.usuario_actual = payload  # disponible en la ruta via flask.g
            return funcion(*args, **kwargs)

        return envoltura

    return token_requerido


def crear_decorador_rol_requerido():
    """
    Fabrica del decorador `@rol_requerido("admin")` para endpoints que
    solo el administrador puede usar (gestion de usuarios). Debe usarse
    SIEMPRE despues de `@token_requerido` en la cadena de decoradores.
    """

    def rol_requerido(rol_esperado: str):
        def decorador(funcion):
            @wraps(funcion)
            def envoltura(*args, **kwargs):
                if g.usuario_actual.get("rol") != rol_esperado:
                    return jsonify({"error": "No tienes permisos para realizar esta accion"}), 403
                return funcion(*args, **kwargs)

            return envoltura

        return decorador

    return rol_requerido