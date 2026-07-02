"""
PUNTO DE ENTRADA / "Composition Root" — BACKEND PURO (API REST)
================================================================
En esta version el frontend esta separado (Vercel) y el backend
solo expone la API REST en JSON. Ya no sirve HTML.

Para correr localmente:
    python app.py
El servidor queda escuchando en http://localhost:5000
"""

import logging

from flask import Flask
from flask_cors import CORS

from application.use_cases.analizar_imagen import AnalizarImagenCasoDeUso
from application.use_cases.autenticar_usuario import AutenticarUsuarioCasoDeUso
from application.use_cases.gestionar_usuarios import (
    CambiarEstadoUsuarioCasoDeUso,
    CrearUsuarioCasoDeUso,
    EliminarUsuarioCasoDeUso,
    ListarUsuariosCasoDeUso,
)
from config import Config
from infrastructure.ml.clasificador_mobilenet import ClasificadorMobileNetV2
from infrastructure.persistence.sqlite_usuario_repository import RepositorioUsuariosSQLite
from infrastructure.security.auth_service import JWTAuthService
from presentation.middlewares.auth_middleware import (
    crear_decorador_rol_requerido,
    crear_decorador_token_requerido,
)
from presentation.routes.admin_routes import crear_blueprint_admin
from presentation.routes.analysis_routes import crear_blueprint_analisis
from presentation.routes.auth_routes import crear_blueprint_auth
from presentation.routes.health_routes import blueprint_salud

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def crear_app(config: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config)

    # CORS: permite peticiones desde el frontend en Vercel.
    # En produccion, reemplaza "*" por tu URL real de Vercel:
    # ej: "https://tu-proyecto.vercel.app"
    CORS(app, origins=config.ORIGENES_PERMITIDOS, supports_credentials=True)

    # ----- INFRAESTRUCTURA -----
    repo_usuarios = RepositorioUsuariosSQLite(config.RUTA_BASE_DE_DATOS)
    auth_service = JWTAuthService(config.SECRET_KEY, config.HORAS_EXPIRACION_TOKEN)
    clasificador_ia = ClasificadorMobileNetV2(config.RUTA_MODELO_IA)

    # ----- CASOS DE USO -----
    caso_autenticar = AutenticarUsuarioCasoDeUso(repo_usuarios, auth_service)
    caso_listar_usuarios = ListarUsuariosCasoDeUso(repo_usuarios)
    caso_crear_usuario = CrearUsuarioCasoDeUso(repo_usuarios, auth_service)
    caso_eliminar_usuario = EliminarUsuarioCasoDeUso(repo_usuarios)
    caso_cambiar_estado_usuario = CambiarEstadoUsuarioCasoDeUso(repo_usuarios)
    caso_analizar_imagen = AnalizarImagenCasoDeUso(clasificador_ia)

    # ----- MIDDLEWARES -----
    token_requerido = crear_decorador_token_requerido(auth_service)
    rol_requerido = crear_decorador_rol_requerido()

    # ----- RUTAS (solo API JSON, sin vistas HTML) -----
    app.register_blueprint(crear_blueprint_auth(caso_autenticar))
    app.register_blueprint(
        crear_blueprint_admin(
            caso_listar_usuarios,
            caso_crear_usuario,
            caso_eliminar_usuario,
            caso_cambiar_estado_usuario,
            token_requerido,
            rol_requerido,
        )
    )
    app.register_blueprint(crear_blueprint_analisis(caso_analizar_imagen, token_requerido))
    app.register_blueprint(blueprint_salud)
    # NOTA: blueprint_vistas se elimino. El frontend ahora es estatico en Vercel.

    return app


app = crear_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=Config.PUERTO, debug=Config.DEBUG, use_reloader=False)
