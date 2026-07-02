"""
CAPA: APPLICATION (Aplicacion) - Caso de uso: Analizar imagen citologica
===========================================================================
Implementa PB-11 del Product Backlog del articulo:
"Integracion del modelo de IA exportado para procesar imagenes en
tiempo real y retornar resultados en JSON [...] la API recibe la
imagen, invoca al modelo y devuelve el diagnostico estructurado."

Este caso de uso NO sabe que el modelo es un MobileNetV2 entrenado con
Keras: solo conoce la interfaz abstracta ClasificadorCelular. Quien
sepa de TensorFlow es infrastructure/ml/clasificador_mobilenet.py
"""

from domain.entities import ResultadoClasificacion
from domain.exceptions import ImagenInvalidaError
from domain.repositories import ClasificadorCelular

EXTENSIONES_PERMITIDAS = {"png", "jpg", "jpeg", "tif", "tiff", "bmp"}
TAMANO_MAXIMO_BYTES = 20 * 1024 * 1024  # 20 MB, igual al limite que ya anuncia el frontend


class AnalizarImagenCasoDeUso:
    def __init__(self, clasificador: ClasificadorCelular):
        self._clasificador = clasificador

    def ejecutar(self, nombre_archivo: str, bytes_imagen: bytes) -> ResultadoClasificacion:
        self._validar_archivo(nombre_archivo, bytes_imagen)
        return self._clasificador.predecir(bytes_imagen, nombre_archivo)

    @staticmethod
    def _validar_archivo(nombre_archivo: str, bytes_imagen: bytes) -> None:
        if not bytes_imagen:
            raise ImagenInvalidaError("El archivo recibido esta vacio")

        if len(bytes_imagen) > TAMANO_MAXIMO_BYTES:
            raise ImagenInvalidaError("La imagen supera el tamano maximo permitido (20 MB)")

        extension = nombre_archivo.rsplit(".", 1)[-1].lower() if "." in nombre_archivo else ""
        if extension not in EXTENSIONES_PERMITIDAS:
            raise ImagenInvalidaError(
                f"Formato '{extension}' no soportado. Formatos validos: {', '.join(sorted(EXTENSIONES_PERMITIDAS))}"
            )