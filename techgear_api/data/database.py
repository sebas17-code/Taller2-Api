"""Conexión asíncrona con MongoDB mediante Motor."""
import os
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path
from dotenv import load_dotenv

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=ENV_FILE)
MONGODB_URI = os.getenv("MONGODB_URI", "").strip()
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "techgear")

_client = None

def connect_db():
    """Inicializa el cliente si hay URI configurada."""
    global _client
    if MONGODB_URI and _client is None:
        _client = AsyncIOMotorClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    return _client

def get_database():
    """Devuelve la base de datos; requiere MONGODB_URI en .env."""
    client = connect_db()
    if client is None:
        raise RuntimeError("Configura MONGODB_URI en el archivo .env.")
    return client[MONGODB_DATABASE]

async def check_connection() -> bool:
    """Comprueba si MongoDB responde."""
    client = connect_db()
    if client is None:
        return False
    try:
        await client.admin.command("ping")
        return True
    except Exception:
        return False

def close_db():
    """Cierra el cliente de MongoDB."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
