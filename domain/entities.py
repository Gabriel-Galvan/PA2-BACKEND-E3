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
    """
    id: int | None
    nombre_usuario: str
    password_hash: str
    rol: RolUsuario
    activo: bool = True
    creado_en: datetime | None = None


@dataclass
class ResultadoClasificacion:
    """
    Resultado devuelto por el clasificador de IA para una sola imagen
    citologica. Es la entidad central del Modulo II (Core de IA) y del
    endpoint de prediccion del Modulo III (PB-11).
    """
    tipo_celula: TipoCelula
    confianza: float  # porcentaje 0-100
    probabilidades: dict[str, float] = field(default_factory=dict)  # todas las clases con su probabilidad
    nombre_archivo: str = ""
    generado_en: datetime = field(default_factory=datetime.utcnow)

    def a_diccionario(self) -> dict:
        """Convierte la entidad a un dict serializable a JSON para la API."""
        return {
            "diagnostico": self.tipo_celula.value,
            "confianza": round(self.confianza, 2),
            "probabilidades": {k: round(v, 2) for k, v in self.probabilidades.items()},
            "archivo": self.nombre_archivo,
            "fecha": self.generado_en.isoformat(),
        }