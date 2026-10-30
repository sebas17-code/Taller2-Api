"""Funciones de seguridad y autenticación de TechGear."""

import os
from pathlib import Path
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from pwdlib import PasswordHash


# Cargar la configuración del archivo .env
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=ENV_FILE)


# Configuración JWT
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

try:
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(
        os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )
except ValueError as error:
    raise RuntimeError(
        "La duración del token JWT debe ser un número entero."
    ) from error


# Comprobar la configuración de seguridad
if not JWT_SECRET_KEY or len(JWT_SECRET_KEY) < 32:
    raise RuntimeError("La clave secreta JWT no está configurada correctamente.")

if JWT_ACCESS_TOKEN_EXPIRE_MINUTES <= 0:
    raise RuntimeError("La duración del token JWT debe ser positiva.")


# Configurar Argon2
password_hasher = PasswordHash.recommended()


def hash_password(contrasena: str) -> str:
    """Genera el hash de una contraseña mediante Argon2."""
    return password_hasher.hash(contrasena)


def verify_password(
    contrasena: str,
    contrasena_hash: str,
) -> bool:
    """Comprueba una contraseña frente a su hash."""
    return password_hasher.verify(contrasena, contrasena_hash)


def create_access_token(usuario_id: str) -> str:
    """Genera un JWT para el usuario autenticado."""

    ahora = datetime.now(timezone.utc)

    payload = {
        "sub": usuario_id,
        "iat": ahora,
        "exp": ahora + timedelta(
            minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        ),
    }

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    """Verifica el JWT y devuelve sus datos."""

    return jwt.decode(
        token,
        JWT_SECRET_KEY,
        algorithms=[JWT_ALGORITHM],
    )