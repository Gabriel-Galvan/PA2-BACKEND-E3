"""
CAPA: INFRASTRUCTURE (Infraestructura) - Inteligencia Artificial
===================================================================
Implementacion CONCRETA del puerto `ClasificadorCelular`.

VERSION TFLITE (liviana en RAM)
--------------------------------
El Free tier de Render solo da 512 MB de RAM. Cargar TensorFlow
completo (tensorflow-cpu) + el grafo del modelo facilmente se pasaba
de ese limite durante la inferencia, matando el proceso sin avisar
(por eso las peticiones a /api/analizar se quedaban "colgadas").

La solucion: convertir el modelo .keras a .tflite (formato liviano,
pensado para dispositivos con poca RAM) y servirlo con
`ai-edge-litert`, el interprete oficial de Google para TFLite, que
pesa una fraccion de lo que pesa TensorFlow completo. Misma
arquitectura, mismos pesos, mismo resultado numerico (con una perdida
de precision minima e irrelevante por la cuantizacion por defecto).
"""

import io
import logging

import numpy as np
from ai_edge_litert.interpreter import Interpreter
from PIL import Image, UnidentifiedImageError

from domain.entities import ResultadoClasificacion, TipoCelula
from domain.exceptions import ImagenInvalidaError
from domain.repositories import ClasificadorCelular

logger = logging.getLogger(__name__)

ORDEN_CLASES: list[TipoCelula] = [
    TipoCelula.DISQUERATOSICAS,
    TipoCelula.KOILOCITOTICAS,
    TipoCelula.METAPLASICAS,
    TipoCelula.PARABASALES,
    TipoCelula.SUPERFICIALES_INTERMEDIAS,
]

TAMANO_ENTRADA = (160, 160)


class ClasificadorMobileNetV2(ClasificadorCelular):
    """
    Carga el modelo TFLite UNA SOLA VEZ al iniciar el servidor y lo
    reutiliza en cada peticion.
    """

    def __init__(self, ruta_modelo: str):
        logger.info("Cargando modelo TFLite desde %s ...", ruta_modelo)
        self._interprete = Interpreter(model_path=ruta_modelo)
        self._interprete.allocate_tensors()
        self._detalle_entrada = self._interprete.get_input_details()[0]
        self._detalle_salida = self._interprete.get_output_details()[0]
        logger.info("Modelo de IA (TFLite) cargado con exito.")

    def predecir(self, bytes_imagen: bytes, nombre_archivo: str = "") -> ResultadoClasificacion:
        imagen = self._abrir_imagen(bytes_imagen)
        tensor_entrada = self._preprocesar_imagen(imagen)

        self._interprete.set_tensor(self._detalle_entrada["index"], tensor_entrada)
        self._interprete.invoke()
        predicciones = self._interprete.get_tensor(self._detalle_salida["index"])[0]

        indice_ganador = int(np.argmax(predicciones))
        tipo_celula = ORDEN_CLASES[indice_ganador]
        confianza = float(predicciones[indice_ganador]) * 100

        probabilidades = {
            ORDEN_CLASES[i].value: float(p) * 100 for i, p in enumerate(predicciones)
        }

        return ResultadoClasificacion(
            tipo_celula=tipo_celula,
            confianza=confianza,
            probabilidades=probabilidades,
            nombre_archivo=nombre_archivo,
        )

    @staticmethod
    def _abrir_imagen(bytes_imagen: bytes) -> Image.Image:
        try:
            return Image.open(io.BytesIO(bytes_imagen)).convert("RGB")
        except UnidentifiedImageError as error:
            raise ImagenInvalidaError("El archivo no es una imagen valida o esta corrupto") from error

    @staticmethod
    def _preprocesar_imagen(imagen: Image.Image) -> np.ndarray:
        imagen = imagen.resize(TAMANO_ENTRADA)
        array_imagen = np.asarray(imagen, dtype=np.float32)
        array_imagen = np.expand_dims(array_imagen, axis=0)  # (1, 160, 160, 3)

        # El modelo fue entrenado con rescale=1./255
        array_imagen = array_imagen / 255.0

        return array_imagen

