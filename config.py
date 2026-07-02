"""
CAPA: PRESENTATION / Configuracion transversal
=================================================
Configuracion centralizada del backend.
Lee variables de entorno si existen (recomendado en produccion).
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "clave-secreta-academica-cambiar-en-produccion")

    HORAS_EXPIRACION_TOKEN = int(os.environ.get("HORAS_EXPIRACION_TOKEN", "8"))

    RUTA_BASE_DE_DATOS = os.environ.get(
        "RUTA_BASE_DE_DATOS", os.path.join(BASE_DIR, "database", "cervix_app.db")
    )

    RUTA_MODELO_IA = os.environ.get(
        "RUTA_MODELO_IA", os.path.join(BASE_DIR, "modelo_cancer_cervical.keras")
    )

    # CORS: agrega aqui la URL de tu frontend en Vercel cuando la tengas.
    # Ejemplo: "https://mi-app.vercel.app,http://localhost:5500"
    ORIGENES_PERMITIDOS = os.environ.get(
        "ORIGENES_PERMITIDOS",
        "http://localhost:5500,http://127.0.0.1:5500,http://localhost:3000,null",
    ).split(",")

    DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    PUERTO = int(os.environ.get("PORT", os.environ.get("PUERTO", "5000")))
