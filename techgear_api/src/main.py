"""Punto de entrada de la API TechGear."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from dotenv import load_dotenv
import os
from bson import ObjectId
from datetime import datetime, timezone

from techgear_api.data.database import (
    check_connection,
    close_db,
    get_database,
)
from techgear_api.src.models.producto import Producto
from techgear_api.src.models.pedido import (
    Pedido,
    PedidoCrear,
    ActualizarEstadoPedido,
)

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

@app.post(
    "/productos",
    status_code=status.HTTP_201_CREATED,
    tags=["Productos"],
)
async def crear_producto(producto: Producto):
    """Crea y guarda un producto en MongoDB Atlas."""
    db = get_database()

    datos_producto = producto.model_dump()

    resultado = await db["productos"].insert_one(datos_producto)

    return {
        "mensaje": "Producto creado correctamente",
        "id": str(resultado.inserted_id),
        "producto": producto.model_dump(),
    }

@app.get("/productos", tags=["Productos"])
async def listar_productos():
    """Devuelve los productos guardados en MongoDB."""
    db = get_database()

    documentos = await db["productos"].find().to_list(length=100)

    productos = []

    for documento in documentos:
        documento["id"] = str(documento.pop("_id"))
        productos.append(documento)

    return {
        "total": len(productos),
        "productos": productos,
    }  
@app.get("/productos/{producto_id}", tags=["Productos"])
async def obtener_producto(producto_id: str):
    """Busca un producto por su identificador de MongoDB."""
    if not ObjectId.is_valid(producto_id):
        raise HTTPException(
            status_code=400,
            detail="El ID del producto no es válido",
        )

    db = get_database()

    documento = await db["productos"].find_one(
        {"_id": ObjectId(producto_id)}
    )

    if documento is None:
        raise HTTPException(
            status_code=404,
            detail="Producto no encontrado",
        )

    documento["id"] = str(documento.pop("_id"))

    return documento

@app.put("/productos/{producto_id}", tags=["Productos"])
async def actualizar_producto(producto_id: str, producto: Producto):
    """Actualiza los datos de un producto existente."""

    if not ObjectId.is_valid(producto_id):
        raise HTTPException(
            status_code=400,
            detail="El ID del producto no es válido",
        )

    db = get_database()

    resultado = await db["productos"].update_one(
        {"_id": ObjectId(producto_id)},
        {"$set": producto.model_dump()},
    )

    if resultado.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Producto no encontrado",
        )

    documento = await db["productos"].find_one(
        {"_id": ObjectId(producto_id)}
    )

    documento["id"] = str(documento.pop("_id"))

    return {
        "mensaje": "Producto actualizado correctamente",
        "producto": documento,
    }   
@app.delete("/productos/{producto_id}", tags=["Productos"])
async def eliminar_producto(producto_id: str):
    """Elimina un producto por su identificador."""

    if not ObjectId.is_valid(producto_id):
        raise HTTPException(
            status_code=400,
            detail="El ID del producto no es válido",
        )

    db = get_database()

    resultado = await db["productos"].delete_one(
        {"_id": ObjectId(producto_id)}
    )

    if resultado.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Producto no encontrado",
        )

    return {
        "mensaje": "Producto eliminado correctamente",
        "id": producto_id,
    }  
@app.post("/pedidos/validar", tags=["Pedidos"])
async def validar_pedido(pedido: Pedido):
    """Valida un pedido recibido; no lo guarda todavía en MongoDB."""
    return {"mensaje": "Pedido válido", "pedido": pedido.model_dump(mode="json")}

@app.post(
    "/pedidos",
    status_code=status.HTTP_201_CREATED,
    tags=["Pedidos"],
)
async def crear_pedido(pedido: PedidoCrear):
    """Crea un pedido y actualiza el inventario en MongoDB."""

    db = get_database()

    # Validar los identificadores antes de consultar la base de datos.
    for articulo in pedido.articulos:
        if not ObjectId.is_valid(articulo.producto_id):
            raise HTTPException(
                status_code=400,
                detail=f"ID de producto inválido: {articulo.producto_id}",
            )

    articulos_pedido = []
    total = 0.0
    creado_en = datetime.now(timezone.utc)

    # La transacción permite guardar el pedido y descontar el stock
    # como una sola operación: si falla, los cambios se revierten.
    async with await db.client.start_session() as session:
        async with session.start_transaction():

            for articulo in pedido.articulos:
                producto_id = ObjectId(articulo.producto_id)

                producto = await db["productos"].find_one(
                    {"_id": producto_id},
                    session=session,
                )

                if producto is None:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Producto no encontrado: {articulo.producto_id}",
                    )

                if not producto.get("activo", True):
                    raise HTTPException(
                        status_code=409,
                        detail=f"El producto '{producto['nombre']}' no está disponible",
                    )

                if producto.get("stock", 0) < articulo.cantidad:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Stock insuficiente para '{producto['nombre']}'",
                    )

                # El precio siempre se obtiene de MongoDB.
                precio = float(producto["precio"])
                subtotal = round(precio * articulo.cantidad, 2)

                # Descontar stock solo si todavía es suficiente.
                resultado_stock = await db["productos"].update_one(
                    {
                        "_id": producto_id,
                        "activo": True,
                        "stock": {"$gte": articulo.cantidad},
                    },
                    {"$inc": {"stock": -articulo.cantidad}},
                    session=session,
                )

                if resultado_stock.modified_count == 0:
                    raise HTTPException(
                        status_code=409,
                        detail=f"No fue posible reservar el stock de '{producto['nombre']}'",
                    )

                articulos_pedido.append({
                    "producto_id": str(producto_id),
                    "nombre": producto["nombre"],
                    "cantidad": articulo.cantidad,
                    "precio_unitario": precio,
                    "subtotal": subtotal,
                })

                total += subtotal

            total = round(total, 2)

            documento_pedido = {
                "cliente": pedido.cliente,
                "articulos": articulos_pedido,
                "total": total,
                "estado": "pendiente",
                "creado_en": creado_en,
                "notas": pedido.notas,
            }

            resultado_pedido = await db["pedidos"].insert_one(
                documento_pedido,
                session=session,
            )
    documento_pedido.pop("_id", None)
        
    return {
        "mensaje": "Pedido creado correctamente",
        "id": str(resultado_pedido.inserted_id),
        "pedido": documento_pedido,
    }
    
@app.get("/pedidos", tags=["Pedidos"])
async def listar_pedidos():
    """Devuelve los pedidos guardados en MongoDB."""

    db = get_database()

    documentos = await db["pedidos"].find().sort(
        "creado_en", -1
    ).to_list(length=100)

    pedidos = []

    for documento in documentos:
        documento["id"] = str(documento.pop("_id"))
        pedidos.append(documento)

    return {
        "total": len(pedidos),
        "pedidos": pedidos,
    }
    
@app.get("/pedidos/{pedido_id}", tags=["Pedidos"])
async def obtener_pedido(pedido_id: str):
    """Busca un pedido por su identificador de MongoDB."""

    if not ObjectId.is_valid(pedido_id):
        raise HTTPException(
            status_code=400,
            detail="El ID del pedido no es válido",
        )

    db = get_database()

    documento = await db["pedidos"].find_one(
        {"_id": ObjectId(pedido_id)}
    )

    if documento is None:
        raise HTTPException(
            status_code=404,
            detail="Pedido no encontrado",
        )

    documento["id"] = str(documento.pop("_id"))

    return documento


@app.patch("/pedidos/{pedido_id}/estado", tags=["Pedidos"])
async def actualizar_estado_pedido(
    pedido_id: str,
    datos: ActualizarEstadoPedido,
):
    """Actualiza el estado de un pedido y gestiona su cancelación."""

    if not ObjectId.is_valid(pedido_id):
        raise HTTPException(
            status_code=400,
            detail="El ID del pedido no es válido",
        )

    db = get_database()
    nuevo_estado = datos.estado

    async with await db.client.start_session() as session:
        async with session.start_transaction():

            pedido = await db["pedidos"].find_one(
                {"_id": ObjectId(pedido_id)},
                session=session,
            )

            if pedido is None:
                raise HTTPException(
                    status_code=404,
                    detail="Pedido no encontrado",
                )

            estado_actual = pedido.get("estado", "pendiente")

            transiciones_permitidas = {
                "pendiente": {"pagado", "cancelado"},
                "pagado": {"enviado"},
                "enviado": {"entregado"},
                "entregado": set(),
                "cancelado": set(),
            }

            if nuevo_estado not in transiciones_permitidas.get(
                estado_actual, set()
            ):
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"No se puede cambiar el pedido de "
                        f"'{estado_actual}' a '{nuevo_estado}'"
                    ),
                )

            # Si se cancela un pedido pendiente, se recupera su stock.
            if nuevo_estado == "cancelado":

                for articulo in pedido["articulos"]:
                    producto_id = articulo.get("producto_id", "")
                    cantidad = articulo.get("cantidad", 0)

                    if (
                        not ObjectId.is_valid(producto_id)
                        or cantidad <= 0
                    ):
                        raise HTTPException(
                            status_code=409,
                            detail=(
                                "No se puede recuperar el inventario "
                                "por los datos de un artículo inválido"
                            ),
                        )

                    resultado_stock = await db["productos"].update_one(
                        {"_id": ObjectId(producto_id)},
                        {"$inc": {"stock": cantidad}},
                        session=session,
                    )

                    if resultado_stock.matched_count == 0:
                        raise HTTPException(
                            status_code=409,
                            detail=(
                                f"No se encontró el producto "
                                f"{producto_id} para recuperar el stock"
                            ),
                        )

            await db["pedidos"].update_one(
                {"_id": ObjectId(pedido_id)},
                {"$set": {"estado": nuevo_estado}},
                session=session,
            )

            documento_actualizado = await db["pedidos"].find_one(
                {"_id": ObjectId(pedido_id)},
                session=session,
            )

    documento_actualizado["id"] = str(
        documento_actualizado.pop("_id")
    )

    return {
        "mensaje": "Estado del pedido actualizado correctamente",
        "pedido": documento_actualizado,
    }