"""
CAPA: INFRASTRUCTURE (Infraestructura) - Inteligencia Artificial
===================================================================
Implementacion CONCRETA del puerto `DetectorCelular`.

QUE PROBLEMA RESUELVE
----------------------
El clasificador MobileNetV2 (clasificador_mobilenet.py) fue entrenado
con imagenes YA RECORTADAS de una sola celula (dataset SIPaKMeD,
carpeta CROPPED). Si se le pasa una foto de campo completo del
microscopio (varias celulas, tomada tal cual sale del equipo), el
modelo recibe una distribucion de datos completamente distinta a la
de entrenamiento y predice practicamente a ciegas (verificado: sesgo
fuerte hacia "Superficiales/Intermedias" sin importar la celula real).

Este archivo agrega una ETAPA PREVIA: un detector YOLOv8 (una sola
clase "celula", exportado a TFLite) que localiza cada celula dentro
de la foto completa. Cada recorte que encuentra se le pasa al
clasificador existente sin modificarlo.

DOS DETALLES DE FORMATO QUE COSTARON VARIAS RONDAS DE DEBUG
--------------------------------------------------------------
1. El input del detector exportado puede venir en formato CHW
   (1, 3, H, W) en vez de HWC (1, H, W, 3). Se detecta automaticamente
   revisando la forma del tensor de entrada.
2. La salida cruda del detector (cx, cy, bw, bh) viene NORMALIZADA
   entre 0 y 1 (fraccion de la imagen), NO en pixeles de `imgsz`. Por
   eso las coordenadas se multiplican directo por el ancho/alto de la
   imagen, sin dividir entre `imgsz` (un bug real que se corrigio
   durante el desarrollo: dividir dos veces encogia las cajas a casi
   nada y el pipeline "no detectaba nada").

FALLBACK
--------
Si el detector no encuentra ninguna celula por encima del umbral de
confianza, se clasifica la imagen COMPLETA como si fuera una sola
celula (comportamiento identico al clasificador simple de antes). Esto
evita que el sistema se rompa con imagenes que YA vienen recortadas a
una sola celula (por ejemplo, pruebas manuales o integraciones viejas).
"""

import io
import logging

import numpy as np
from ai_edge_litert.interpreter import Interpreter
from PIL import Image, UnidentifiedImageError

from domain.entities import ResultadoClasificacion
from domain.exceptions import ImagenInvalidaError
from domain.repositories import ClasificadorCelular, DetectorCelular

logger = logging.getLogger(__name__)

# Margen extra alrededor de cada caja detectada antes de recortar, para
# no cortar el borde de la celula (mismo criterio usado al validar el
# pipeline en el notebook de entrenamiento).
MARGEN_RECORTE = 0.10


class DetectorYOLOCelulas(DetectorCelular):
    """
    Carga el modelo YOLO-TFLite UNA SOLA VEZ al iniciar el servidor.
    Reutiliza (por composicion, no herencia) el `ClasificadorCelular`
    ya existente para clasificar cada celula que encuentra.
    """

    def __init__(
        self,
        ruta_modelo_detector: str,
        clasificador: ClasificadorCelular,
        tamano_entrada: int = 960,
        umbral_confianza: float = 0.25,
        umbral_iou: float = 0.5,
    ):
        logger.info("Cargando modelo detector TFLite desde %s ...", ruta_modelo_detector)
        self._interprete = Interpreter(model_path=ruta_modelo_detector)
        self._interprete.allocate_tensors()
        self._detalle_entrada = self._interprete.get_input_details()[0]
        self._detalle_salida = self._interprete.get_output_details()[0]
        self._clasificador = clasificador
        self._tamano_entrada = tamano_entrada
        self._umbral_confianza = umbral_confianza
        self._umbral_iou = umbral_iou
        logger.info(
            "Detector de celulas (TFLite) cargado con exito. imgsz=%s, conf=%s",
            tamano_entrada,
            umbral_confianza,
        )

    def detectar_y_clasificar(
        self, bytes_imagen: bytes, nombre_archivo: str = ""
    ) -> list[ResultadoClasificacion]:
        imagen = self._abrir_imagen(bytes_imagen)
        cajas = self._detectar_cajas(imagen)

        if len(cajas) == 0:
            # Fallback: no se detecto ninguna celula -> clasificar la
            # imagen completa como una sola celula (comportamiento
            # legado, util para imagenes ya recortadas).
            logger.info(
                "Detector no encontro celulas en '%s'; usando la imagen completa como fallback.",
                nombre_archivo,
            )
            resultado = self._clasificador.predecir(bytes_imagen, nombre_archivo)
            return [resultado]

        resultados: list[ResultadoClasificacion] = []
        ancho_img, alto_img = imagen.size

        for (x1, y1, x2, y2) in cajas:
            x1 = max(0, int(x1))
            y1 = max(0, int(y1))
            x2 = min(ancho_img, int(x2))
            y2 = min(alto_img, int(y2))
            if x2 - x1 < 5 or y2 - y1 < 5:
                continue  # caja degenerada, se descarta

            recorte = imagen.crop((x1, y1, x2, y2))
            buffer = io.BytesIO()
            recorte.save(buffer, format="PNG")
            resultado = self._clasificador.predecir(buffer.getvalue(), nombre_archivo)
            resultado.bbox = [x1, y1, x2, y2]
            resultados.append(resultado)

        if not resultados:
            # Todas las cajas detectadas eran degeneradas (raro, pero
            # por robustez caemos al mismo fallback de arriba).
            resultado = self._clasificador.predecir(bytes_imagen, nombre_archivo)
            return [resultado]

        return resultados

    # ------------------------------------------------------------------
    # Deteccion (YOLO)
    # ------------------------------------------------------------------

    def _detectar_cajas(self, imagen: Image.Image) -> np.ndarray:
        ancho_img, alto_img = imagen.size
        tam = self._tamano_entrada

        redimensionada = imagen.resize((tam, tam))
        arreglo = np.array(redimensionada).astype(np.float32) / 255.0  # (H, W, 3)

        # El modelo puede esperar CHW (1, 3, H, W) en vez de HWC -- se
        # detecta automaticamente revisando la forma del input.
        if self._detalle_entrada["shape"][1] == 3:
            arreglo = np.transpose(arreglo, (2, 0, 1))  # (3, H, W)
        entrada = np.expand_dims(arreglo, axis=0)

        self._interprete.set_tensor(self._detalle_entrada["index"], entrada)
        self._interprete.invoke()
        salida = self._interprete.get_tensor(self._detalle_salida["index"])[0]

        salida = salida.T  # -> (num_cajas, 4 + num_clases)
        cajas_cxcywh = salida[:, :4]
        puntajes = salida[:, 4]  # una sola clase ("celula")

        mantener = puntajes > self._umbral_confianza
        cajas_cxcywh = cajas_cxcywh[mantener]
        puntajes = puntajes[mantener]

        if len(cajas_cxcywh) == 0:
            return np.empty((0, 4))

        # cx, cy, bw, bh vienen normalizados [0,1] (fraccion de la
        # imagen) -- NO son pixeles de `tam`, por eso se multiplica
        # directo por ancho_img/alto_img (sin dividir entre `tam`).
        cx, cy, bw, bh = (
            cajas_cxcywh[:, 0],
            cajas_cxcywh[:, 1],
            cajas_cxcywh[:, 2],
            cajas_cxcywh[:, 3],
        )
        # margen extra para no cortar el borde de la celula
        bw = bw * (1 + MARGEN_RECORTE)
        bh = bh * (1 + MARGEN_RECORTE)

        x1 = (cx - bw / 2) * ancho_img
        y1 = (cy - bh / 2) * alto_img
        x2 = (cx + bw / 2) * ancho_img
        y2 = (cy + bh / 2) * alto_img

        cajas_px = np.stack([x1, y1, x2, y2], axis=1)

        indices = self._non_max_suppression(cajas_px, puntajes, self._umbral_iou)
        return cajas_px[indices]

    @staticmethod
    def _non_max_suppression(cajas_px: np.ndarray, puntajes: np.ndarray, umbral_iou: float) -> np.ndarray:
        """NMS simple con numpy puro (sin depender de tensorflow.image,
        que no esta disponible con el interprete liviano ai-edge-litert)."""
        x1, y1, x2, y2 = cajas_px[:, 0], cajas_px[:, 1], cajas_px[:, 2], cajas_px[:, 3]
        areas = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
        orden = puntajes.argsort()[::-1]

        mantenidos = []
        while orden.size > 0:
            i = orden[0]
            mantenidos.append(i)

            xx1 = np.maximum(x1[i], x1[orden[1:]])
            yy1 = np.maximum(y1[i], y1[orden[1:]])
            xx2 = np.minimum(x2[i], x2[orden[1:]])
            yy2 = np.minimum(y2[i], y2[orden[1:]])

            inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
            union = areas[i] + areas[orden[1:]] - inter
            iou = np.where(union > 0, inter / union, 0)

            orden = orden[1:][iou <= umbral_iou]

        return np.array(mantenidos, dtype=int)

    @staticmethod
    def _abrir_imagen(bytes_imagen: bytes) -> Image.Image:
        try:
            return Image.open(io.BytesIO(bytes_imagen)).convert("RGB")
        except UnidentifiedImageError as error:
            raise ImagenInvalidaError("El archivo no es una imagen valida o esta corrupto") from error
