"""
CAPA: PRESENTATION (Presentacion) - Ruta de salud del servicio
==================================================================
Endpoint simple para verificar que el backend esta arriba (util para
el frontend, para Postman/Insomnia, o para un futuro despliegue en la
nube de Sesion 15-16 del cronograma).
"""

from flask import Blueprint, jsonify

blueprint_salud = Blueprint("salud", __name__, url_prefix="/api")


@blueprint_salud.route("/salud", methods=["GET"])
def salud():
    return jsonify({"estado": "ok", "servicio": "API Clasificacion Cancer Cervical"}), 200