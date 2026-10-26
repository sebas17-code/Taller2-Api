"""Punto de entrada de la API TechGear."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv
import os

from techgear_api.data.database import check_connection, close_db
from techgear_api.src.models.producto import Producto
from techgear_api.src.models.pedido import Pedido

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    close_db()

app = FastAPI(
    title=os.getenv("APP_NAME", "TechGear API"),
    description="API inicial de TechGear con modelos Pydantic y conexión a MongoDB.",
    version="0.1.0",
    lifespan=lifespan,
)

@app.get("/", tags=["Inicio"])
async def inicio():
    return {"mensaje": "TechGear API funcionando", "documentacion": "/docs", "salud": "/health"}

@app.get("/health", tags=["Salud"])
async def health():
    return {"status": "ok", "mongodb_conectado": await check_connection()}

@app.post("/productos/validar", tags=["Productos"])
async def validar_producto(producto: Producto):
    """Valida un producto recibido; no lo guarda todavía en MongoDB."""
    return {"mensaje": "Producto válido", "producto": producto.model_dump()}

@app.post("/pedidos/validar", tags=["Pedidos"])
async def validar_pedido(pedido: Pedido):
    """Valida un pedido recibido; no lo guarda todavía en MongoDB."""
    return {"mensaje": "Pedido válido", "pedido": pedido.model_dump(mode="json")}
