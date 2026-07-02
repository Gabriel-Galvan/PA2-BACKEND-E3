"""
CAPA: INFRASTRUCTURE (Infraestructura) - Inteligencia Artificial
===================================================================
Implementacion CONCRETA del puerto `ClasificadorCelular`. Aqui vive
(y se corrige) el script original que enviaste.

QUE ESTABA MAL EN TU CODIGO ORIGINAL (por que "no te salia"):
----------------------------------------------------------------
Tu modelo es una red MobileNetV2 (lo confirma el .h5: la primera capa
es "mobilenetv2_1.00_224" cargada con pesos de ImageNet, congelada, y
luego GlobalAveragePooling2D + Dropout + Dense(128) + Dense(5,softmax)
-> exactamente lo que describe PB-04/PB-05 del articulo).

Las redes de la familia MobileNetV2 de Keras NO reciben los pixeles
"crudos" en el rango [0, 255]. Cuando se entrenan, las imagenes pasan
primero por una normalizacion (lo mas comun y recomendado, igual a la
que usa `tf.keras.applications.MobileNetV2` con pesos de ImageNet, es
escalar los pixeles al rango [-1, 1] con
`tf.keras.applications.mobilenet_v2.preprocess_input`).

Tu codigo original hacia esto:
    img_array = tf.keras.utils.img_to_array(img)      # valores 0-255
    img_array = tf.expand_dims(img_array, 0)          # <-- se enviaba asi, SIN normalizar
    predicciones = model.predict(img_array)

Al entrar pixeles en el rango [0, 255] a una red que "espera" el rango
[-1, 1], la red no reconoce ningun patron real: la salida del softmax
queda practicamente aleatoria / sesgada siempre a la misma clase. Esa
es la causa mas probable de que el modelo "no te saliera".

LA CORRECCION (ver `_preprocesar_imagen` mas abajo):
    img_array = tf.keras.applications.mobilenet_v2.preprocess_input(img_array)

IMPORTANTE: si tu notebook de entrenamiento normalizo las imagenes de
otra forma (por ejemplo con `ImageDataGenerator(rescale=1./255)`),
hay que cambiar esta linea para que sea EXACTAMENTE el mismo
preprocesamiento usado al entrenar. La regla de oro en aprendizaje por
transferencia es: "el preprocesamiento en produccion debe ser idéntico
al preprocesamiento usado en entrenamiento".
"""

"""
CAPA: INFRASTRUCTURE (Infraestructura) - Inteligencia Artificial
"""

import io
import logging

import numpy as np
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

# Corregido de 224x224 a 160x160 para coincidir con el modelo entrenado
TAMANO_ENTRADA = (160, 160)


class ClasificadorMobileNetV2(ClasificadorCelular):
    """
    Carga el modelo UNA SOLA VEZ al iniciar el servidor y lo reutiliza
    en cada peticion.
    """

    def __init__(self, ruta_modelo: str):
        import tensorflow as tf

        self._tf = tf
        logger.info("Cargando modelo de IA desde %s ...", ruta_modelo)
        self._modelo = tf.keras.models.load_model(ruta_modelo)
        logger.info("Modelo de IA cargado con exito.")

    def predecir(self, bytes_imagen: bytes, nombre_archivo: str = "") -> ResultadoClasificacion:
        imagen = self._abrir_imagen(bytes_imagen)
        tensor_entrada = self._preprocesar_imagen(imagen)

        predicciones = self._modelo.predict(tensor_entrada, verbose=0)[0]

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

    def _preprocesar_imagen(self, imagen: Image.Image) -> np.ndarray:
        imagen = imagen.resize(TAMANO_ENTRADA)
        array_imagen = self._tf.keras.utils.img_to_array(imagen)
        array_imagen = np.expand_dims(array_imagen, axis=0)  # (1, 160, 160, 3)

        # El modelo fue entrenado con rescale=1./255
        array_imagen = array_imagen / 255.0

        return array_imagen
