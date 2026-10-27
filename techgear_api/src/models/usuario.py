"""Modelo de validación para usuarios."""

from pydantic import BaseModel, ConfigDict, Field


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