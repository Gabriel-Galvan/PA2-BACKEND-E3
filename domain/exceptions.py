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