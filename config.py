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

    # Si DATABASE_URL esta presente (Render la inyecta al vincular un
    # Postgres al servicio), se usa Postgres en vez de SQLite.
    DATABASE_URL = os.environ.get("DATABASE_URL")

    RUTA_MODELO_IA = os.environ.get(
        "RUTA_MODELO_IA", os.path.join(BASE_DIR, "modelo_cancer_cervical.tflite")
    )

    # Detector de celulas (YOLOv8, etapa previa al clasificador). Debe
    # coincidir con el imgsz usado al entrenar/exportar el detector
    # (notebook detector_celulas_YOLOv8.ipynb, Bloque 5 y 8).
    RUTA_MODELO_DETECTOR = os.environ.get(
        "RUTA_MODELO_DETECTOR", os.path.join(BASE_DIR, "detector_celulas.tflite")
    )
    DETECTOR_IMGSZ = int(os.environ.get("DETECTOR_IMGSZ", "960"))
    DETECTOR_UMBRAL_CONFIANZA = float(os.environ.get("DETECTOR_UMBRAL_CONFIANZA", "0.25"))
    DETECTOR_UMBRAL_IOU = float(os.environ.get("DETECTOR_UMBRAL_IOU", "0.5"))

    # CORS: agrega aqui la URL de tu frontend en Vercel cuando la tengas.
    # Ejemplo: "https://mi-app.vercel.app,http://localhost:5500"
    ORIGENES_PERMITIDOS = os.environ.get(
        "ORIGENES_PERMITIDOS",
        "http://localhost:5500,http://127.0.0.1:5500,http://localhost:3000,null",
    ).split(",")

    DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    PUERTO = int(os.environ.get("PORT", os.environ.get("PUERTO", "5000")))

    # Notificaciones por correo (modulo de Expedientes). Si SMTP_USER o
    # SMTP_PASSWORD no estan definidas, el servicio cae automaticamente
    # a "modo simulado" (solo registra el correo en los logs, no falla).
    # Para activar el envio real con Gmail:
    #   1. Habilita verificacion en 2 pasos en la cuenta de Gmail.
    #   2. Genera una "contrasena de aplicacion" en myaccount.google.com/apppasswords
    #   3. Define en Render: SMTP_USER=tu_correo@gmail.com, SMTP_PASSWORD=<esa contrasena>
    SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
    SMTP_USER = os.environ.get("SMTP_USER")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
    SMTP_FROM_NAME = os.environ.get("SMTP_FROM_NAME", "Sistema de Diagnostico Cervical")
