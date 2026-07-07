"""
CAPA: PRESENTATION (Presentacion) - Rutas de Expedientes
=============================================================
Implementa PB-12 (historial clinico relacional por medico) del lado
HTTP. Todas las rutas requieren estar autenticado (@token_requerido).
El control de "un medico solo ve sus propios expedientes" se aplica
en la capa de aplicacion (application/use_cases/gestionar_expedientes.py),
esta capa solo traduce HTTP <-> casos de uso.
"""

from flask import Blueprint, g, jsonify, request

from application.use_cases.gestionar_expedientes import (
    ActualizarExpedienteCasoDeUso,
    CrearExpedienteCasoDeUso,
    EliminarExpedienteCasoDeUso,
    ListarExpedientesCasoDeUso,
    ObtenerExpedienteCasoDeUso,
)
from domain.exceptions import (
    AccesoNoAutorizadoError,
    DatosPacienteInvalidosError,
    ExpedienteNoEncontradoError,
    ImagenInvalidaError,
)


def crear_blueprint_expedientes(
    caso_crear: CrearExpedienteCasoDeUso,
    caso_listar: ListarExpedientesCasoDeUso,
    caso_obtener: ObtenerExpedienteCasoDeUso,
    caso_actualizar: ActualizarExpedienteCasoDeUso,
    caso_eliminar: EliminarExpedienteCasoDeUso,
    token_requerido,
) -> Blueprint:
    blueprint = Blueprint("expedientes", __name__, url_prefix="/api/expedientes")

    @blueprint.route("", methods=["GET"])
    @token_requerido
    def listar_expedientes():
        usuario_id = int(g.usuario_actual["sub"])
        rol = g.usuario_actual["rol"]
        # ?todos=true le permite a un admin pedir explicitamente solo los
        # suyos si quisiera (por defecto el admin ve todos los expedientes).
        solo_propios = request.args.get("solo_propios", "false").lower() == "true"
        expedientes = caso_listar.ejecutar(usuario_id, rol, solo_propios)
        return jsonify([e.a_diccionario(incluir_imagen=False) for e in expedientes]), 200

    @blueprint.route("", methods=["POST"])
    @token_requerido
    def crear_expediente():
        usuario_id = int(g.usuario_actual["sub"])

        if "imagen" not in request.files:
            return jsonify({"error": "No se recibio ninguna imagen"}), 400
        archivo = request.files["imagen"]
        if archivo.filename == "":
            return jsonify({"error": "No se selecciono ningun archivo"}), 400

        datos = request.form

        try:
            expediente, correo_enviado = caso_crear.ejecutar(
                medico_id=usuario_id,
                nombre_archivo=archivo.filename,
                bytes_imagen=archivo.read(),
                nombre_paciente=datos.get("nombre_paciente", ""),
                numero_documento=datos.get("numero_documento", ""),
                fecha_nacimiento=datos.get("fecha_nacimiento") or None,
                sexo=datos.get("sexo") or None,
                historial_ginecologico=datos.get("historial_ginecologico", ""),
                sintomas=datos.get("sintomas", ""),
                observaciones=datos.get("observaciones", ""),
            )
        except (ImagenInvalidaError, DatosPacienteInvalidosError) as error:
            return jsonify({"error": str(error)}), 400
        except Exception as error:  # noqa: BLE001
            return jsonify({"error": f"Error al procesar el expediente: {error}"}), 500

        respuesta = expediente.a_diccionario(incluir_imagen=False)
        respuesta["correo_enviado"] = correo_enviado
        return jsonify(respuesta), 201

    @blueprint.route("/<int:expediente_id>", methods=["GET"])
    @token_requerido
    def obtener_expediente(expediente_id: int):
        usuario_id = int(g.usuario_actual["sub"])
        rol = g.usuario_actual["rol"]
        try:
            expediente = caso_obtener.ejecutar(expediente_id, usuario_id, rol)
        except ExpedienteNoEncontradoError as error:
            return jsonify({"error": str(error)}), 404
        except AccesoNoAutorizadoError as error:
            return jsonify({"error": str(error)}), 403
        return jsonify(expediente.a_diccionario(incluir_imagen=True)), 200

    @blueprint.route("/<int:expediente_id>", methods=["PATCH"])
    @token_requerido
    def actualizar_expediente(expediente_id: int):
        usuario_id = int(g.usuario_actual["sub"])
        rol = g.usuario_actual["rol"]
        datos = request.get_json(silent=True) or {}

        try:
            expediente = caso_actualizar.ejecutar(
                expediente_id,
                usuario_id,
                rol,
                nombre_paciente=datos.get("nombre_paciente", ""),
                numero_documento=datos.get("numero_documento", ""),
                fecha_nacimiento=datos.get("fecha_nacimiento") or None,
                sexo=datos.get("sexo") or None,
                historial_ginecologico=datos.get("historial_ginecologico", ""),
                sintomas=datos.get("sintomas", ""),
                observaciones=datos.get("observaciones", ""),
            )
        except ExpedienteNoEncontradoError as error:
            return jsonify({"error": str(error)}), 404
        except AccesoNoAutorizadoError as error:
            return jsonify({"error": str(error)}), 403
        except DatosPacienteInvalidosError as error:
            return jsonify({"error": str(error)}), 400

        return jsonify(expediente.a_diccionario(incluir_imagen=False)), 200

    @blueprint.route("/<int:expediente_id>", methods=["DELETE"])
    @token_requerido
    def eliminar_expediente(expediente_id: int):
        usuario_id = int(g.usuario_actual["sub"])
        rol = g.usuario_actual["rol"]
        try:
            eliminado = caso_eliminar.ejecutar(expediente_id, usuario_id, rol)
        except ExpedienteNoEncontradoError as error:
            return jsonify({"error": str(error)}), 404
        except AccesoNoAutorizadoError as error:
            return jsonify({"error": str(error)}), 403

        if not eliminado:
            return jsonify({"error": "Expediente no encontrado"}), 404
        return jsonify({"mensaje": "Expediente eliminado correctamente"}), 200

    return blueprint
