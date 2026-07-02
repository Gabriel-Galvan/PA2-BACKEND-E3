"""
CAPA: PRESENTATION (Presentacion) - Rutas de analisis de imagenes
=====================================================================
Implementa PB-10 ("Creacion de endpoints (API REST) seguros para la
recepcion de imagenes citologicas (JPG/PNG)") y PB-11 ("Integracion
del modelo de IA exportado para procesar imagenes en tiempo real y
retornar resultados en JSON") del Product Backlog.

Este es el reemplazo, ya integrado a la arquitectura, de tu script
original `analizar_imagen()`. La logica de IA en si vive en
infrastructure/ml/clasificador_mobilenet.py; aqui solo se conecta el
HTTP con el caso de uso.
"""

from flask import Blueprint, jsonify, request

from application.use_cases.analizar_imagen import AnalizarImagenCasoDeUso
from domain.exceptions import ImagenInvalidaError


def crear_blueprint_analisis(caso_de_uso_analizar: AnalizarImagenCasoDeUso, token_requerido) -> Blueprint:
    blueprint = Blueprint("analisis", __name__, url_prefix="/api")

    @blueprint.route("/analizar", methods=["POST"])
    @token_requerido
    def analizar_imagen():
        # Verificamos si el frontend envio una imagen (mismo nombre de
        # campo que tu script original: 'imagen')
        if "imagen" not in request.files:
            return jsonify({"error": "No se recibio ninguna imagen"}), 400

        archivo = request.files["imagen"]
        if archivo.filename == "":
            return jsonify({"error": "No se selecciono ningun archivo"}), 400

        try:
            resultado = caso_de_uso_analizar.ejecutar(archivo.filename, archivo.read())
        except ImagenInvalidaError as error:
            return jsonify({"error": str(error)}), 400
        except Exception as error:  # noqa: BLE001 - se reporta cualquier fallo inesperado del modelo
            return jsonify({"error": f"Error al procesar la imagen: {error}"}), 500

        return jsonify(resultado.a_diccionario()), 200

    return blueprint