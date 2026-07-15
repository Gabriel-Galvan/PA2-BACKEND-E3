"""
CAPA: DOMAIN (Dominio) - Excepciones de negocio
=================================================
Excepciones propias del dominio. Permiten que la capa de presentacion
(presentation/routes) traduzca errores de negocio a codigos HTTP
adecuados, sin que el dominio sepa nada de HTTP.
"""


class ErrorDominio(Exception):
    """Excepcion base para todos los errores de reglas de negocio."""


class CredencialesInvalidasError(ErrorDominio):
    """Se lanza cuando el usuario o la contrasena no son correctos."""


class UsuarioInactivoError(ErrorDominio):
    """Se lanza cuando un usuario existe pero esta desactivado por un administrador."""


class UsuarioYaExisteError(ErrorDominio):
    """Se lanza al intentar crear un usuario con un nombre_usuario duplicado."""


class ImagenInvalidaError(ErrorDominio):
    """Se lanza cuando el archivo recibido no es una imagen valida o esta corrupto."""


class TokenInvalidoError(ErrorDominio):
    """Se lanza cuando el token JWT enviado no es valido o expiro."""


class ExpedienteNoEncontradoError(ErrorDominio):
    """Se lanza cuando se busca un expediente por id y no existe."""


class AccesoNoAutorizadoError(ErrorDominio):
    """
    Se lanza cuando un medico intenta ver/editar/eliminar un
    expediente que pertenece a otro medico (control de accesos:
    'cada doctor tiene acceso solo a sus propios expedientes').
    El rol admin esta exento de esta regla.
    """


class DatosPacienteInvalidosError(ErrorDominio):
    """Se lanza cuando los datos clinicos del paciente son invalidos o incompletos."""


class CorreoInvalidoError(ErrorDominio):
    """Se lanza cuando el correo de notificaciones ingresado no tiene un formato valido."""


class NombreUsuarioInvalidoError(ErrorDominio):
    """Se lanza cuando el nuevo nombre de usuario no cumple el formato esperado."""