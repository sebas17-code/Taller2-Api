"""Modelo de validación para usuarios."""
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Usuario(BaseModel):
    """Define y valida los datos básicos de un usuario."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    nombre: str = Field(
        min_length=2,
        max_length=100,
        examples=["Usuario de prueba"],
    )

    correo: str = Field(
        min_length=5,
        max_length=254,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        examples=["usuario@ejemplo.com"],
    )

class UsuarioCrear(BaseModel):
    """Datos necesarios para registrar un usuario."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=2, max_length=100)
    correo: str = Field(
        min_length=5,
        max_length=254,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )
    contrasena: str = Field(
        min_length=8,
        max_length=128,
        repr=False,
    )

    @field_validator("nombre", "correo", mode="before")
    @classmethod
    def limpiar_texto(cls, valor):
        if isinstance(valor, str):
            return valor.strip()
        return valor


class UsuarioLogin(BaseModel):
    """Credenciales para iniciar sesión."""

    model_config = ConfigDict(extra="forbid")

    correo: str = Field(
        min_length=5,
        max_length=254,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )
    contrasena: str = Field(
        min_length=1,
        max_length=128,
        repr=False,
    )


class UsuarioPublico(BaseModel):
    """Datos del usuario que se pueden devolver en las respuestas."""

    id: str
    nombre: str
    correo: str