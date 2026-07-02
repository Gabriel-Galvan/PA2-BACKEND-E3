"""
CAPA: DOMAIN (Dominio) - Contratos / Puertos
=============================================
Aqui se definen las INTERFACES ABSTRACTAS que la capa de Aplicacion
(application/use_cases) necesita para funcionar, pero SIN saber como
se implementan realmente.

Esto es el corazon del "Principio de Inversion de Dependencias" de la
Clean Architecture: el dominio define el contrato (el "que"), y la
capa de infraestructura (infrastructure/) lo implementa con tecnologia
concreta (el "como": SQLite, TensorFlow, JWT, etc.).

Gracias a esto, en el futuro se podria cambiar SQLite por PostgreSQL,
o MobileNetV2 por otra arquitectura de red neuronal, sin tener que
tocar ni una linea de los casos de uso.
"""

from abc import ABC, abstractmethod

from domain.entities import ResultadoClasificacion, RolUsuario, Usuario


class RepositorioUsuarios(ABC):
    """
    Puerto (contrato) para cualquier mecanismo de persistencia de
    usuarios. La implementacion concreta vive en
    infrastructure/persistence/sqlite_usuario_repository.py
    """

    @abstractmethod
    def obtener_por_nombre_usuario(self, nombre_usuario: str) -> Usuario | None:
        """Busca un usuario por su nombre de usuario. Devuelve None si no existe."""
        raise NotImplementedError

    @abstractmethod
    def listar_todos(self) -> list[Usuario]:
        """Devuelve todos los usuarios registrados (para el panel administrativo)."""
        raise NotImplementedError

    @abstractmethod
    def crear(self, nombre_usuario: str, password_hash: str, rol: RolUsuario) -> Usuario:
        """Crea un nuevo usuario y lo devuelve ya persistido (con su id)."""
        raise NotImplementedError

    @abstractmethod
    def eliminar(self, usuario_id: int) -> bool:
        """Elimina un usuario por id. Devuelve True si se elimino algo."""
        raise NotImplementedError

    @abstractmethod
    def cambiar_estado(self, usuario_id: int, activo: bool) -> bool:
        """Activa/desactiva un usuario (permiso administrativo de mantenimiento)."""
        raise NotImplementedError


class ClasificadorCelular(ABC):
    """
    Puerto (contrato) para el modelo de Inteligencia Artificial.
    La implementacion concreta (que carga el .h5 con TensorFlow/Keras
    y aplica el preprocesamiento de MobileNetV2) vive en
    infrastructure/ml/clasificador_mobilenet.py

    Los casos de uso de application/ solo conocen este metodo
    `predecir`, jamas import an TensorFlow directamente.
    """

    @abstractmethod
    def predecir(self, bytes_imagen: bytes, nombre_archivo: str = "") -> ResultadoClasificacion:
        """
        Recibe los bytes crudos de una imagen citologica (JPG/PNG) y
        devuelve la entidad ResultadoClasificacion con la clase
        predicha y el nivel de confianza.
        """
        raise NotImplementedError


class ServicioAutenticacion(ABC):
    """
    Puerto (contrato) para hashear/verificar contrasenas y para
    generar/validar tokens de sesion (JWT). Implementado en
    infrastructure/security/auth_service.py
    """

    @abstractmethod
    def hashear_password(self, password_plano: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def verificar_password(self, password_plano: str, password_hash: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def generar_token(self, usuario: Usuario) -> str:
        raise NotImplementedError

    @abstractmethod
    def validar_token(self, token: str) -> dict | None:
        """Devuelve el payload decodificado si el token es valido, o None si no lo es / expiro."""
        raise NotImplementedError