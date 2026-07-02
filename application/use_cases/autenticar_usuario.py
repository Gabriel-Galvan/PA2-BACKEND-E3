"""
CAPA: APPLICATION (Aplicacion) - Caso de uso: Autenticacion
=============================================================
Los "casos de uso" orquestan al Dominio para cumplir una accion
concreta que pide el usuario final. Aqui se implementa el login que
exige el cronograma en Sesion 08:
  "Implementar un modulo de inicio de sesion con usuario y
   contrasena, validado mediante una API o endpoint. Si el acceso es
   correcto, se mostrara la interfaz principal [...] caso contrario,
   el mensaje: 'Usuario y clave incorrectos'."

Este caso de uso SOLO depende de las interfaces abstractas definidas
en domain/repositories.py (RepositorioUsuarios, ServicioAutenticacion),
nunca de SQLite o JWT directamente. Eso es lo que permite testearlo
con un "mock" sin necesitar una base de datos real.
"""

from domain.entities import Usuario
from domain.exceptions import CredencialesInvalidasError, UsuarioInactivoError
from domain.repositories import RepositorioUsuarios, ServicioAutenticacion


class AutenticarUsuarioCasoDeUso:
    def __init__(self, repo_usuarios: RepositorioUsuarios, auth_service: ServicioAutenticacion):
        self._repo_usuarios = repo_usuarios
        self._auth_service = auth_service

    def ejecutar(self, nombre_usuario: str, password: str) -> tuple[Usuario, str]:
        """
        Valida usuario y contrasena. Si son correctos, devuelve la
        entidad Usuario y un token JWT firmado para que el frontend lo
        use en las siguientes peticiones (Authorization: Bearer <token>).

        Lanza CredencialesInvalidasError o UsuarioInactivoError si la
        validacion falla, para que la capa de presentacion responda
        con el mensaje y codigo HTTP apropiados.
        """
        usuario = self._repo_usuarios.obtener_por_nombre_usuario(nombre_usuario)

        if usuario is None:
            raise CredencialesInvalidasError("Usuario y clave incorrectos")

        if not self._auth_service.verificar_password(password, usuario.password_hash):
            raise CredencialesInvalidasError("Usuario y clave incorrectos")

        if not usuario.activo:
            raise UsuarioInactivoError("El usuario esta desactivado. Contacte al administrador.")

        token = self._auth_service.generar_token(usuario)
        return usuario, token