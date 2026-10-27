"""Modelos de validación para pedidos."""
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class ArticuloPedido(BaseModel):
    producto_id: str = Field(min_length=1, examples=["producto_id"])
    cantidad: int = Field(gt=0, examples=[2])
    precio_unitario: float = Field(gt=0, allow_inf_nan=False, examples=[129900])

class Pedido(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    cliente: str = Field(min_length=2, max_length=120, examples=["Cliente de prueba"])
    articulos: list[ArticuloPedido] = Field(min_length=1)
    estado: Literal["pendiente", "pagado", "enviado", "entregado", "cancelado"] = "pendiente"
    creado_en: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notas: str | None = Field(default=None, max_length=1000)
    
class ArticuloPedidoEntrada(BaseModel):
    """Datos que el cliente envía para cada artículo del pedido."""

    model_config = ConfigDict(str_strip_whitespace=True)

    producto_id: str = Field(
        min_length=1,
        examples=["id_del_producto"],
    )

    cantidad: int = Field(
        gt=0,
        examples=[2],
    )


class PedidoCrear(BaseModel):
    """Datos que se reciben para crear un pedido."""

    model_config = ConfigDict(str_strip_whitespace=True)

    cliente: str = Field(
        min_length=2,
        max_length=120,
        examples=["Cliente de prueba"],
    )

    articulos: list[ArticuloPedidoEntrada] = Field(
        min_length=1,
    )

    notas: str | None = Field(
        default=None,
        max_length=1000,
    )
    
class ActualizarEstadoPedido(BaseModel):
    """Datos permitidos para actualizar el estado de un pedido."""

    model_config = ConfigDict(str_strip_whitespace=True)

    estado: Literal[
        "pagado",
        "enviado",
        "entregado",
        "cancelado",
    ]
