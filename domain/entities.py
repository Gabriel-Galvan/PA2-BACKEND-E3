"""
CAPA: DOMAIN (Dominio)
======================
Esta es la capa MAS INTERNA de la Clean Architecture (Arquitectura Limpia).

Regla de dependencia de Clean Architecture: el Dominio NO IMPORTA NADA
de Flask, SQLite, TensorFlow ni de ninguna otra capa externa. Aqui solo
vive el "lenguaje del negocio": las entidades y las reglas que tendria
el sistema aunque cambiemos el framework web, la base de datos o el
modelo de IA.

Corresponde al Modulo II (Core de IA) y Modulo III (Backend) del
Product Backlog del articulo cientifico (PB-04 a PB-12), y a los
requerimientos de Sesion 09-11 del cronograma (funcionalidades
administrativas y modelo de IA integrado).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class TipoCelula(str, Enum):
    """
    Las 5 clases de celulas cervicales del dataset SIPaKMeD que el
    modelo de aprendizaje por transferencia es capaz de reconocer.

    IMPORTANTE: el orden de este Enum debe coincidir EXACTAMENTE con
    el orden de las carpetas/clases usado durante el entrenamiento
    (normalmente el orden alfabetico que usa Keras con
    `flow_from_directory` o `image_dataset_from_directory`). Si el
    modelo entrega resultados incoherentes, lo primero que hay que
    revisar es que este orden siga siendo el correcto.
    """
    DISQUERATOSICAS = "Disqueratosicas"
    KOILOCITOTICAS = "Koilocitoticas"
    METAPLASICAS = "Metaplasicas"
    PARABASALES = "Parabasales"
    SUPERFICIALES_INTERMEDIAS = "Superficiales/Intermedias"


class RolUsuario(str, Enum):
    """Roles soportados para el modulo de gestion de usuarios (PB-12 /
    'funcionalidades administrativas: mantenimiento, gestion de
    usuarios, permisos' exigido en el cronograma)."""
    ADMIN = "admin"
    MEDICO = "medico"


@dataclass
class Usuario:
    """
    Entidad de Usuario. Representa al personal de salud que usa el
    sistema (PB-14: 'modulo de autenticacion y control de accesos
    para el personal de salud').

    Notese que esta entidad NUNCA contiene la contrasena en texto
    plano, solo su hash. Calcular/verificar el hash es responsabilidad
    de la capa de infraestructura (infrastructure/security), no del
    dominio.

    El campo `correo` es opcional: se usa para enviarle al medico una
    notificacion cuando el analisis de una imagen de su expediente
    termina con exito (ver ServicioCorreo / infrastructure/email).
    """
    id: int | None
    nombre_usuario: str
    password_hash: str
    rol: RolUsuario
    activo: bool = True
    creado_en: datetime | None = None
    correo: str | None = None
    avatar_base64: str | None = None  # foto de perfil, como data URL (image/...;base64,...)


@dataclass
class ResultadoClasificacion:
    """
    Resultado devuelto por el clasificador de IA para UNA celula
    citologica (un recorte). Es la entidad central del Modulo II
    (Core de IA) y del endpoint de prediccion del Modulo III (PB-11).

    `bbox` es opcional: [x1, y1, x2, y2] en pixeles de la imagen
    ORIGINAL de campo completo que subio el medico. Lo llena el
    detector (infrastructure/ml/detector_yolo.py) cuando la
    clasificacion viene de un pipeline de deteccion + clasificacion;
    queda en None cuando se clasifica una imagen ya recortada
    directamente (comportamiento legado / endpoint simple).
    """
    tipo_celula: TipoCelula
    confianza: float  # porcentaje 0-100
    probabilidades: dict[str, float] = field(default_factory=dict)  # todas las clases con su probabilidad
    nombre_archivo: str = ""
    generado_en: datetime = field(default_factory=datetime.utcnow)
    bbox: list[int] | None = None  # [x1, y1, x2, y2] en pixeles de la imagen original, o None

    def a_diccionario(self) -> dict:
        """Convierte la entidad a un dict serializable a JSON para la API."""
        datos = {
            "diagnostico": self.tipo_celula.value,
            "confianza": round(self.confianza, 2),
            "probabilidades": {k: round(v, 2) for k, v in self.probabilidades.items()},
            "archivo": self.nombre_archivo,
            "fecha": self.generado_en.isoformat(),
        }
        if self.bbox is not None:
            datos["bbox"] = self.bbox
        return datos


# Orden de severidad clinica (de menor a mayor) usado para elegir, entre
# varias celulas detectadas en una misma imagen, cual es el "hallazgo
# principal" que se guarda como diagnostico del expediente (PB-12).
# Mismo criterio que _SEVERIDAD_POR_CLASE mas abajo, pero a nivel de
# clase de celula para poder comparar.
_ORDEN_SEVERIDAD_CLASE: dict[str, int] = {
    TipoCelula.SUPERFICIALES_INTERMEDIAS.value: 0,
    TipoCelula.PARABASALES.value: 0,
    TipoCelula.METAPLASICAS.value: 1,
    TipoCelula.KOILOCITOTICAS.value: 1,
    TipoCelula.DISQUERATOSICAS.value: 2,
}


def seleccionar_hallazgo_principal(
    resultados: list[ResultadoClasificacion],
) -> ResultadoClasificacion:
    """
    Dada la lista de celulas detectadas y clasificadas en una imagen de
    campo completo, elige cual se reporta como EL diagnostico del
    expediente: la de mayor severidad clinica (Disqueratosicas > Koilo/
    Metaplasicas > Superficiales/Parabasales); si hay empate en
    severidad, la de mayor confianza. Asi el expediente nunca "esconde"
    el hallazgo mas grave detras de celulas normales.

    Se asume que `resultados` no esta vacio (el caso de uso que llama
    a esto es responsable de garantizarlo).
    """
    return max(
        resultados,
        key=lambda r: (_ORDEN_SEVERIDAD_CLASE.get(r.tipo_celula.value, 1), r.confianza),
    )


# Clasificacion clinica de apoyo visual (criterio Bethesda / SIPaKMeD),
# usada tanto para pintar el "badge" del expediente como para decidir
# el tono del correo de notificacion. NO es un diagnostico definitivo.
_SEVERIDAD_POR_CLASE: dict[str, str] = {
    TipoCelula.SUPERFICIALES_INTERMEDIAS.value: "normal",
    TipoCelula.PARABASALES.value: "normal",
    TipoCelula.METAPLASICAS.value: "revisar",
    TipoCelula.KOILOCITOTICAS.value: "revisar",
    TipoCelula.DISQUERATOSICAS.value: "positivo",
}


@dataclass
class Expediente:
    """
    Entidad central del Modulo de Historial Clinico (PB-12): agrupa,
    para una imagen citologica ya analizada por el modelo de IA, los
    datos del paciente y las observaciones clinicas que ingresa el
    medico, junto con el resultado de IA y la imagen original.

    Cada expediente pertenece a un unico medico (`medico_id`): un
    medico solo puede ver/editar/eliminar sus propios expedientes; el
    rol admin puede ver todos (control de accesos, PB-14).

    La imagen se guarda como bytes crudos (columna BLOB/BYTEA) para
    que el expediente sea autocontenido y no dependa de un disco local
    efimero (Render free tier no garantiza almacenamiento persistente
    en el filesystem del servicio web).
    """
    id: int | None
    medico_id: int
    nombre_paciente: str
    numero_documento: str
    fecha_nacimiento: str | None  # ISO 'YYYY-MM-DD', la edad se calcula al vuelo
    sexo: str | None  # 'femenino' | 'masculino' | 'otro' | None, usado en el informe descargable
    historial_ginecologico: str
    sintomas: str
    observaciones: str
    diagnostico_ia: str
    confianza_ia: float
    probabilidades_ia: dict[str, float]
    nombre_archivo_imagen: str
    imagen_mime: str
    imagen_datos: bytes | None = None  # se omite al listar, solo viaja en el detalle
    creado_en: datetime | None = None
    actualizado_en: datetime | None = None
    correo_paciente: str | None = None  # para avisarle por email cuando su resultado este listo
    # Lista de TODAS las celulas que el detector encontro en la imagen de
    # campo completo (no solo la que se reporta como diagnostico_ia),
    # cada una como {"bbox": [x1,y1,x2,y2], "clase": str, "confianza": float}.
    # Informacion de apoyo para el medico; el diagnostico_ia/confianza_ia
    # siguen siendo la fuente de verdad (el hallazgo mas severo, ver
    # `seleccionar_hallazgo_principal`). Puede quedar None en expedientes
    # antiguos creados antes de este campo, o si el detector no encontro
    # ninguna celula y se uso el flujo de respaldo (imagen completa como
    # una sola celula).
    celulas_detectadas: list[dict] | None = None

    @property
    def severidad(self) -> str:
        """'normal' | 'revisar' | 'positivo', usado para el badge visual."""
        return _SEVERIDAD_POR_CLASE.get(self.diagnostico_ia, "revisar")

    @property
    def codigo_expediente(self) -> str:
        """Codigo tipo 'EXP-000123', solo cosmetico para que la UI se
        sienta como un sistema clinico real."""
        return f"EXP-{self.id:06d}" if self.id else "EXP-PENDIENTE"

    def a_diccionario(self, incluir_imagen: bool = False) -> dict:
        """
        Serializa a JSON. Por defecto NO incluye la imagen (para que
        el listado de expedientes sea liviano); el detalle de un
        expediente individual si la incluye, codificada en base64.
        """
        datos = {
            "id": self.id,
            "codigo": self.codigo_expediente,
            "medico_id": self.medico_id,
            "nombre_paciente": self.nombre_paciente,
            "numero_documento": self.numero_documento,
            "fecha_nacimiento": self.fecha_nacimiento,
            "sexo": self.sexo,
            "historial_ginecologico": self.historial_ginecologico,
            "sintomas": self.sintomas,
            "observaciones": self.observaciones,
            "correo_paciente": self.correo_paciente,
            "diagnostico_ia": self.diagnostico_ia,
            "confianza_ia": round(self.confianza_ia, 2),
            "probabilidades_ia": {k: round(v, 2) for k, v in self.probabilidades_ia.items()},
            "severidad": self.severidad,
            "nombre_archivo_imagen": self.nombre_archivo_imagen,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
            "actualizado_en": self.actualizado_en.isoformat() if self.actualizado_en else None,
            "celulas_detectadas": self.celulas_detectadas or [],
            "total_celulas_detectadas": len(self.celulas_detectadas) if self.celulas_detectadas else 0,
        }
        if incluir_imagen and self.imagen_datos:
            import base64

            datos["imagen_base64"] = (
                f"data:{self.imagen_mime};base64," + base64.b64encode(self.imagen_datos).decode("ascii")
            )
        return datos


@dataclass
class CodigoInvitacion:
    """
    Codigo de un solo uso que un administrador genera para permitir que
    un nuevo medico se auto-registre (POST /api/auth/registro). Sin un
    codigo valido y sin usar, el endpoint de registro publico rechaza
    la creacion de la cuenta: asi se mantiene el control de accesos
    (PB-14) sin que cualquiera pueda crearse una cuenta libremente.
    """
    id: int | None
    codigo: str
    creado_por: int  # id del administrador que lo genero
    usado: bool = False
    usado_por: int | None = None  # id del usuario que lo canjeo, una vez usado
    creado_en: datetime | None = None
    usado_en: datetime | None = None

    def a_diccionario(self) -> dict:
        return {
            "id": self.id,
            "codigo": self.codigo,
            "usado": self.usado,
            "usado_por": self.usado_por,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
            "usado_en": self.usado_en.isoformat() if self.usado_en else None,
        }


@dataclass
class Notificacion:
    """
    Notificacion in-app (la 'campanita' de la interfaz). Dos usos
    concretos en este sistema:
      - tipo 'expediente_listo': se crea para el medico dueno de un
        expediente apenas el analisis de IA termina.
      - tipo 'codigo_invitacion': se crea para el/los administradores
        cada vez que se genera un codigo de invitacion, para que lo
        tengan a mano y se lo puedan entregar al nuevo medico.
    """
    id: int | None
    usuario_id: int
    tipo: str
    titulo: str
    mensaje: str
    leida: bool = False
    referencia_id: int | None = None  # id del expediente o del codigo relacionado, segun el tipo
    creado_en: datetime | None = None

    def a_diccionario(self) -> dict:
        return {
            "id": self.id,
            "tipo": self.tipo,
            "titulo": self.titulo,
            "mensaje": self.mensaje,
            "leida": self.leida,
            "referencia_id": self.referencia_id,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
        }