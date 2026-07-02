"""
CAPA: INFRASTRUCTURE (Infraestructura) - Seguridad
=====================================================
Implementacion CONCRETA del puerto `ServicioAutenticacion`. Aqui SI se
importan librerias externas (werkzeug para hashear contrasenas, PyJWT
para los tokens de sesion). Ninguna otra capa del backend conoce estos
detalles tecnicos.

- Hash de contrasenas: PBKDF2-SHA256 (via werkzeug.security), nunca se
  guarda ni se compara la contrasena en texto plano.
- Sesion: JWT (JSON Web Token) firmado con SECRET_KEY. El frontend
  debe enviarlo en cada peticion protegida como:
      Authorization: Bearer <token>
  Esto es lo que el cronograma llama "validado mediante una API o
  endpoint" para el modulo de inicio de sesion.
"""

from datetime import datetime, timedelta, timezone

import jwt
from werkzeug.security import check_password_hash, generate_password_hash

from domain.entities import Usuario
from domain.repositories import ServicioAutenticacion


class JWTAuthService(ServicioAutenticacion):
    def __init__(self, secret_key: str, horas_expiracion: int = 8, algoritmo: str = "HS256"):
        self._secret_key = secret_key
        self._horas_expiracion = horas_expiracion
        self._algoritmo = algoritmo

    def hashear_password(self, password_plano: str) -> str:
        return generate_password_hash(password_plano, method="pbkdf2:sha256")

    def verificar_password(self, password_plano: str, password_hash: str) -> bool:
        return check_password_hash(password_hash, password_plano)

    def generar_token(self, usuario: Usuario) -> str:
        ahora = datetime.now(timezone.utc)
        payload = {
            "sub": str(usuario.id),
            "nombre_usuario": usuario.nombre_usuario,
            "rol": usuario.rol.value,
            "iat": ahora,
            "exp": ahora + timedelta(hours=self._horas_expiracion),
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algoritmo)

    def validar_token(self, token: str) -> dict | None:
        try:
            return jwt.decode(token, self._secret_key, algorithms=[self._algoritmo])
        except jwt.PyJWTError:
            return None