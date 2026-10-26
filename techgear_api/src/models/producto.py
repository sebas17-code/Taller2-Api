"""Modelo de validación para productos."""
from pydantic import BaseModel, ConfigDict, Field

class Producto(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    nombre: str = Field(min_length=2, max_length=120, examples=["Teclado mecánico"])
    descripcion: str | None = Field(default=None, max_length=1000)
    precio: float = Field(gt=0, allow_inf_nan=False, examples=[129900])
    stock: int = Field(default=0, ge=0, examples=[10])
    activo: bool = True
