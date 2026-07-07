"""
CAPA: APPLICATION (Aplicacion) - Casos de uso: Expedientes clinicos
======================================================================
Implementa PB-12 ("base de datos relacional completa de historial de
analisis por medico"), la iteracion que quedo pendiente en el modulo
de gestion de usuarios.

Regla de negocio central (control de accesos, PB-14): un medico solo
puede leer/editar/eliminar los expedientes que EL creo. El rol admin
tiene privilegio de supervision total: puede leer, editar y eliminar
CUALQUIER expediente (utilidad administrativa real: corregir datos
mal ingresados o depurar registros de prueba), tal como el resto del
sistema ya le permite gestionar usuarios sin restriccion.
"""

from __future__ import annotations

from domain.entities import Expediente, RolUsuario
from domain.exceptions import (
    AccesoNoAutorizadoError,
    DatosPacienteInvalidosError,
    ExpedienteNoEncontradoError,
    ImagenInvalidaError,
)
from domain.repositories import (
    ClasificadorCelular,
    RepositorioExpedientes,
    RepositorioUsuarios,
    ServicioCorreo,
)

EXTENSIONES_PERMITIDAS = {"png", "jpg", "jpeg", "tif", "tiff", "bmp"}
TAMANO_MAXIMO_BYTES = 20 * 1024 * 1024  # 20 MB, igual al limite del analisis simple
SEXOS_VALIDOS = {"femenino", "masculino", "otro"}


def _normalizar_sexo(valor: str | None) -> str | None:
    """El sexo es opcional (algunos registros historicos no lo tienen);
    si viene con un valor reconocido se normaliza a minusculas, si no
    se guarda como None en vez de fallar la creacion del expediente."""
    if not valor:
        return None
    valor = valor.strip().lower()
    return valor if valor in SEXOS_VALIDOS else None


def _validar_imagen(nombre_archivo: str, bytes_imagen: bytes) -> None:
    if not bytes_imagen:
        raise ImagenInvalidaError("El archivo recibido esta vacio")
    if len(bytes_imagen) > TAMANO_MAXIMO_BYTES:
        raise ImagenInvalidaError("La imagen supera el tamano maximo permitido (20 MB)")
    extension = nombre_archivo.rsplit(".", 1)[-1].lower() if "." in nombre_archivo else ""
    if extension not in EXTENSIONES_PERMITIDAS:
        raise ImagenInvalidaError(
            f"Formato '{extension}' no soportado. Formatos validos: {', '.join(sorted(EXTENSIONES_PERMITIDAS))}"
        )


def _mime_por_extension(nombre_archivo: str) -> str:
    extension = nombre_archivo.rsplit(".", 1)[-1].lower() if "." in nombre_archivo else "jpg"
    return {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "tif": "image/tiff",
        "tiff": "image/tiff",
        "bmp": "image/bmp",
    }.get(extension, "image/jpeg")


def _verificar_propiedad(expediente: Expediente, usuario_id: int, rol: str) -> None:
    """Un medico solo puede operar sobre SUS expedientes; el admin puede leer cualquiera."""
    if rol == RolUsuario.ADMIN.value:
        return
    if expediente.medico_id != usuario_id:
        raise AccesoNoAutorizadoError("Este expediente pertenece a otro medico")


class CrearExpedienteCasoDeUso:
    """
    Flujo completo al guardar una imagen ya analizada como expediente:
      1. Valida y clasifica la imagen con el modelo de IA (misma
         fuente de verdad que /api/analizar, para que el diagnostico
         guardado sea siempre el que realmente calculo el modelo, no
         uno que el cliente podria manipular).
      2. Persiste el expediente completo (datos del paciente + imagen
         + resultado de IA).
      3. Intenta notificar por correo al medico dueno del expediente
         (best-effort: si falla el envio, el expediente igual se crea).
    """

    def __init__(
        self,
        repo_expedientes: RepositorioExpedientes,
        repo_usuarios: RepositorioUsuarios,
        clasificador: ClasificadorCelular,
        servicio_correo: ServicioCorreo,
    ):
        self._repo_expedientes = repo_expedientes
        self._repo_usuarios = repo_usuarios
        self._clasificador = clasificador
        self._servicio_correo = servicio_correo

    def ejecutar(
        self,
        medico_id: int,
        nombre_archivo: str,
        bytes_imagen: bytes,
        nombre_paciente: str,
        numero_documento: str,
        fecha_nacimiento: str | None,
        sexo: str | None,
        historial_ginecologico: str,
        sintomas: str,
        observaciones: str,
    ) -> tuple[Expediente, bool]:
        if not nombre_paciente or not nombre_paciente.strip():
            raise DatosPacienteInvalidosError("El nombre del paciente es obligatorio")
        if not numero_documento or not numero_documento.strip():
            raise DatosPacienteInvalidosError("El numero de documento del paciente es obligatorio")

        _validar_imagen(nombre_archivo, bytes_imagen)
        resultado_ia = self._clasificador.predecir(bytes_imagen, nombre_archivo)

        expediente = Expediente(
            id=None,
            medico_id=medico_id,
            nombre_paciente=nombre_paciente.strip(),
            numero_documento=numero_documento.strip(),
            fecha_nacimiento=fecha_nacimiento or None,
            sexo=_normalizar_sexo(sexo),
            historial_ginecologico=(historial_ginecologico or "").strip(),
            sintomas=(sintomas or "").strip(),
            observaciones=(observaciones or "").strip(),
            diagnostico_ia=resultado_ia.tipo_celula.value,
            confianza_ia=resultado_ia.confianza,
            probabilidades_ia=resultado_ia.probabilidades,
            nombre_archivo_imagen=nombre_archivo,
            imagen_mime=_mime_por_extension(nombre_archivo),
            imagen_datos=bytes_imagen,
        )
        expediente_creado = self._repo_expedientes.crear(expediente)

        correo_enviado = False
        medico = self._repo_usuarios.obtener_por_id(medico_id)
        if medico and medico.correo:
            try:
                correo_enviado = self._servicio_correo.enviar_notificacion_analisis(
                    medico.correo, medico.nombre_usuario, expediente_creado
                )
            except Exception:  # noqa: BLE001 - un correo fallido nunca debe romper la creacion
                correo_enviado = False

        return expediente_creado, correo_enviado


class ListarExpedientesCasoDeUso:
    """Lista los expedientes visibles para el usuario autenticado (propios, o todos si es admin)."""

    def __init__(self, repo_expedientes: RepositorioExpedientes):
        self._repo_expedientes = repo_expedientes

    def ejecutar(self, usuario_id: int, rol: str, solo_propios: bool = False) -> list[Expediente]:
        if rol == RolUsuario.ADMIN.value and not solo_propios:
            return self._repo_expedientes.listar_todos()
        return self._repo_expedientes.listar_por_medico(usuario_id)


class ObtenerExpedienteCasoDeUso:
    """Obtiene el detalle completo (con imagen) de un expediente, validando propiedad."""

    def __init__(self, repo_expedientes: RepositorioExpedientes):
        self._repo_expedientes = repo_expedientes

    def ejecutar(self, expediente_id: int, usuario_id: int, rol: str) -> Expediente:
        expediente = self._repo_expedientes.obtener_por_id(expediente_id)
        if expediente is None:
            raise ExpedienteNoEncontradoError(f"No existe el expediente #{expediente_id}")
        _verificar_propiedad(expediente, usuario_id, rol)
        return expediente


class ActualizarExpedienteCasoDeUso:
    """Actualiza los campos clinicos (nunca el resultado de IA ni la imagen) de un expediente propio."""

    def __init__(self, repo_expedientes: RepositorioExpedientes):
        self._repo_expedientes = repo_expedientes

    def ejecutar(
        self,
        expediente_id: int,
        usuario_id: int,
        rol: str,
        nombre_paciente: str,
        numero_documento: str,
        fecha_nacimiento: str | None,
        sexo: str | None,
        historial_ginecologico: str,
        sintomas: str,
        observaciones: str,
    ) -> Expediente:
        expediente = self._repo_expedientes.obtener_por_id(expediente_id)
        if expediente is None:
            raise ExpedienteNoEncontradoError(f"No existe el expediente #{expediente_id}")
        _verificar_propiedad(expediente, usuario_id, rol)

        if not nombre_paciente or not nombre_paciente.strip():
            raise DatosPacienteInvalidosError("El nombre del paciente es obligatorio")
        if not numero_documento or not numero_documento.strip():
            raise DatosPacienteInvalidosError("El numero de documento del paciente es obligatorio")

        self._repo_expedientes.actualizar_datos_clinicos(
            expediente_id,
            nombre_paciente.strip(),
            numero_documento.strip(),
            fecha_nacimiento or None,
            _normalizar_sexo(sexo),
            (historial_ginecologico or "").strip(),
            (sintomas or "").strip(),
            (observaciones or "").strip(),
        )
        return self._repo_expedientes.obtener_por_id(expediente_id)


class EliminarExpedienteCasoDeUso:
    """Elimina un expediente propio (o cualquiera, si el usuario es admin)."""

    def __init__(self, repo_expedientes: RepositorioExpedientes):
        self._repo_expedientes = repo_expedientes

    def ejecutar(self, expediente_id: int, usuario_id: int, rol: str) -> bool:
        expediente = self._repo_expedientes.obtener_por_id(expediente_id)
        if expediente is None:
            raise ExpedienteNoEncontradoError(f"No existe el expediente #{expediente_id}")
        _verificar_propiedad(expediente, usuario_id, rol)
        return self._repo_expedientes.eliminar(expediente_id)
