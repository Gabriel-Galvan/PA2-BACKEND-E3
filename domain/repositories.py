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

from domain.entities import Expediente, ResultadoClasificacion, RolUsuario, Usuario


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
    def obtener_por_id(self, usuario_id: int) -> Usuario | None:
        """Busca un usuario por id (usado para leer el correo del medico dueno de un expediente)."""
        raise NotImplementedError

    @abstractmethod
    def listar_todos(self) -> list[Usuario]:
        """Devuelve todos los usuarios registrados (para el panel administrativo)."""
        raise NotImplementedError

    @abstractmethod
    def crear(
        self,
        nombre_usuario: str,
        password_hash: str,
        rol: RolUsuario,
        correo: str | None = None,
    ) -> Usuario:
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

    @abstractmethod
    def actualizar_correo(self, usuario_id: int, correo: str) -> bool:
        """Actualiza el correo de notificaciones de un usuario (auto-servicio en Configuracion)."""
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


class RepositorioExpedientes(ABC):
    """
    Puerto (contrato) para la persistencia del Modulo de Expedientes
    (PB-12: historial clinico relacional). La implementacion concreta
    vive en infrastructure/persistence/sqlite_expediente_repository.py
    y postgres_expediente_repository.py.

    IMPORTANTE (control de accesos, PB-14): los metodos que reciben
    `medico_id` son responsabilidad de la capa de aplicacion para
    decidir SI deben filtrar por ese medico o no (un admin puede pedir
    todos); el repositorio simplemente ejecuta la consulta que se le
    pide.
    """

    @abstractmethod
    def crear(self, expediente: Expediente) -> Expediente:
        """Persiste un nuevo expediente (con su imagen) y lo devuelve con id asignado."""
        raise NotImplementedError

    @abstractmethod
    def listar_por_medico(self, medico_id: int) -> list[Expediente]:
        """Lista los expedientes de UN medico especifico (sin los bytes de imagen)."""
        raise NotImplementedError

    @abstractmethod
    def listar_todos(self) -> list[Expediente]:
        """Lista TODOS los expedientes del sistema (solo para el rol admin)."""
        raise NotImplementedError

    @abstractmethod
    def obtener_por_id(self, expediente_id: int) -> Expediente | None:
        """Obtiene un expediente completo (incluye los bytes de la imagen) por id."""
        raise NotImplementedError

    @abstractmethod
    def actualizar_datos_clinicos(
        self,
        expediente_id: int,
        nombre_paciente: str,
        numero_documento: str,
        fecha_nacimiento: str | None,
        sexo: str | None,
        historial_ginecologico: str,
        sintomas: str,
        observaciones: str,
    ) -> bool:
        """Actualiza SOLO los campos clinicos que ingresa el medico (nunca el resultado de IA)."""
        raise NotImplementedError

    @abstractmethod
    def eliminar(self, expediente_id: int) -> bool:
        """Elimina un expediente por id."""
        raise NotImplementedError


class ServicioCorreo(ABC):
    """
    Puerto (contrato) para el envio de notificaciones por correo al
    medico (por ejemplo: 'el analisis de tu imagen ha finalizado con
    exito'). La implementacion concreta (SMTP contra Gmail) vive en
    infrastructure/email/smtp_email_service.py.

    Si no hay credenciales SMTP configuradas en el entorno, la
    implementacion concreta cae a un "modo simulado" (solo registra el
    correo en los logs) para que el resto del sistema funcione igual
    sin necesitar credenciales reales durante el desarrollo/pruebas.
    """

    @abstractmethod
    def enviar_notificacion_analisis(
        self,
        destinatario: str,
        nombre_medico: str,
        expediente: Expediente,
    ) -> bool:
        """
        Envia (o simula) el correo de notificacion. Devuelve True si
        se envio realmente por SMTP, False si quedo en modo simulado
        o si el envio fallo (nunca lanza excepcion: un correo fallido
        no debe tumbar la creacion del expediente).
        """
        raise NotImplementedError