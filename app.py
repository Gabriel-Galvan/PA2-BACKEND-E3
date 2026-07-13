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
from application.use_cases.gestionar_expedientes import (
    ActualizarExpedienteCasoDeUso,
    CrearExpedienteCasoDeUso,
    EliminarExpedienteCasoDeUso,
    ListarExpedientesCasoDeUso,
    ObtenerExpedienteCasoDeUso,
)
from application.use_cases.gestionar_perfil import ActualizarCorreoUsuarioCasoDeUso
from application.use_cases.gestionar_usuarios import (
    CambiarEstadoUsuarioCasoDeUso,
    CrearUsuarioCasoDeUso,
    EliminarUsuarioCasoDeUso,
    ListarUsuariosCasoDeUso,
)
from config import Config
from infrastructure.email.smtp_email_service import SMTPEmailService
from infrastructure.ml.clasificador_mobilenet import ClasificadorMobileNetV2
from infrastructure.ml.detector_yolo import DetectorYOLOCelulas
from infrastructure.persistence.postgres_expediente_repository import RepositorioExpedientesPostgres
from infrastructure.persistence.postgres_usuario_repository import RepositorioUsuariosPostgres
from infrastructure.persistence.sqlite_expediente_repository import RepositorioExpedientesSQLite
from infrastructure.persistence.sqlite_usuario_repository import RepositorioUsuariosSQLite
from infrastructure.security.auth_service import JWTAuthService
from presentation.middlewares.auth_middleware import (
    crear_decorador_rol_requerido,
    crear_decorador_token_requerido,
)
from presentation.routes.admin_routes import crear_blueprint_admin
from presentation.routes.analysis_routes import crear_blueprint_analisis
from presentation.routes.auth_routes import crear_blueprint_auth
from presentation.routes.expediente_routes import crear_blueprint_expedientes
from presentation.routes.health_routes import blueprint_salud
from presentation.routes.perfil_routes import crear_blueprint_perfil

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
    # Si DATABASE_URL esta definida (Postgres vinculado en Render), se
    # usa Postgres. Si no, se cae a SQLite (util para correr local sin
    # tener que levantar un Postgres).
    if config.DATABASE_URL:
        repo_usuarios = RepositorioUsuariosPostgres(config.DATABASE_URL)
        repo_expedientes = RepositorioExpedientesPostgres(config.DATABASE_URL)
    else:
        repo_usuarios = RepositorioUsuariosSQLite(config.RUTA_BASE_DE_DATOS)
        repo_expedientes = RepositorioExpedientesSQLite(config.RUTA_BASE_DE_DATOS)
    auth_service = JWTAuthService(config.SECRET_KEY, config.HORAS_EXPIRACION_TOKEN)
    clasificador_ia = ClasificadorMobileNetV2(config.RUTA_MODELO_IA)
    # El detector reutiliza el clasificador de arriba por composicion:
    # localiza cada celula en la foto de campo completo, y cada recorte
    # se lo pasa al mismo `clasificador_ia` para clasificarlo.
    detector_celulas = DetectorYOLOCelulas(
        config.RUTA_MODELO_DETECTOR,
        clasificador_ia,
        tamano_entrada=config.DETECTOR_IMGSZ,
        umbral_confianza=config.DETECTOR_UMBRAL_CONFIANZA,
        umbral_iou=config.DETECTOR_UMBRAL_IOU,
    )
    servicio_correo = SMTPEmailService(
        config.SMTP_HOST, config.SMTP_PORT, config.SMTP_USER, config.SMTP_PASSWORD, config.SMTP_FROM_NAME
    )

    # ----- CASOS DE USO -----
    caso_autenticar = AutenticarUsuarioCasoDeUso(repo_usuarios, auth_service)
    caso_listar_usuarios = ListarUsuariosCasoDeUso(repo_usuarios)
    caso_crear_usuario = CrearUsuarioCasoDeUso(repo_usuarios, auth_service)
    caso_eliminar_usuario = EliminarUsuarioCasoDeUso(repo_usuarios)
    caso_cambiar_estado_usuario = CambiarEstadoUsuarioCasoDeUso(repo_usuarios)
    caso_analizar_imagen = AnalizarImagenCasoDeUso(clasificador_ia)
    caso_actualizar_correo = ActualizarCorreoUsuarioCasoDeUso(repo_usuarios)
    caso_crear_expediente = CrearExpedienteCasoDeUso(
        repo_expedientes, repo_usuarios, detector_celulas, servicio_correo
    )
    caso_listar_expedientes = ListarExpedientesCasoDeUso(repo_expedientes)
    caso_obtener_expediente = ObtenerExpedienteCasoDeUso(repo_expedientes)
    caso_actualizar_expediente = ActualizarExpedienteCasoDeUso(repo_expedientes)
    caso_eliminar_expediente = EliminarExpedienteCasoDeUso(repo_expedientes)

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
    app.register_blueprint(
        crear_blueprint_expedientes(
            caso_crear_expediente,
            caso_listar_expedientes,
            caso_obtener_expediente,
            caso_actualizar_expediente,
            caso_eliminar_expediente,
            token_requerido,
        )
    )
    app.register_blueprint(crear_blueprint_perfil(caso_actualizar_correo, token_requerido))
    app.register_blueprint(blueprint_salud)
    # NOTA: blueprint_vistas se elimino. El frontend ahora es estatico en Vercel.

    return app


app = crear_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=Config.PUERTO, debug=Config.DEBUG, use_reloader=False)
