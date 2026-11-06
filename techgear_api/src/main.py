from contextlib import asynccontextmanager

from fastapi import (
    FastAPI,
    HTTPException,
    status,
    Depends,
    File,
    UploadFile,
    Response,
)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from dotenv import load_dotenv
from jwt.exceptions import InvalidTokenError
from pymongo.errors import DuplicateKeyError

import os

from bson import ObjectId
from bson.binary import Binary
from datetime import datetime, timezone

from techgear_api.src.models.usuario import (
    UsuarioCrear,
    UsuarioLogin,
    UsuarioPublico,
)

from techgear_api.src.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)

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

# Configuración de imágenes de productos
MAX_IMAGE_SIZE = 2 * 1024 * 1024

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}


# Configuración

bearer_scheme = HTTPBearer(auto_error=False)

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    close_db()


app = FastAPI(
    title=os.getenv("APP_NAME", "TechGear API"),
    description="API de TechGear",
    version="0.1.0",
    lifespan=lifespan,
)


# Rutas de inicio

@app.get("/", tags=["Inicio"])
async def inicio():
    return {
        "mensaje": "TechGear API funcionando",
        "documentacion": "/docs",
        "salud": "/health",
    }


@app.get("/health", tags=["Salud"])
async def health():
    return {
        "status": "ok",
        "mongodb_conectado": await check_connection(),
    }


# Usuarios

@app.post(
    "/usuarios",
    response_model=UsuarioPublico,
    status_code=status.HTTP_201_CREATED,
    tags=["Usuarios"],
)
async def registrar_usuario(usuario: UsuarioCrear):
    """Registra un usuario."""

    db = get_database()
    coleccion = db["usuarios"]

    await coleccion.create_index("correo", unique=True)

    correo = usuario.correo.lower()

    documento = {
        "nombre": usuario.nombre,
        "correo": correo,
        "contrasena_hash": hash_password(usuario.contrasena),
        "rol": "cliente",
        "creado_en": datetime.now(timezone.utc),
    }

    try:
        resultado = await coleccion.insert_one(documento)

    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario registrado con ese correo.",
        )

    return UsuarioPublico(
        id=str(resultado.inserted_id),
        nombre=usuario.nombre,
        correo=correo,
        rol="cliente",
    )


# Login

@app.post("/usuarios/login", tags=["Usuarios"])
async def iniciar_sesion(credenciales: UsuarioLogin):
    """Inicia sesión."""

    db = get_database()

    usuario = await db["usuarios"].find_one(
        {"correo": credenciales.correo.lower()}
    )

    if usuario is None or not verify_password(
        credenciales.contrasena,
        usuario["contrasena_hash"],
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(str(usuario["_id"]))

    return {
        "mensaje": "Inicio de sesión correcto",
        "access_token": token,
        "token_type": "bearer",
        "usuario": {
            "id": str(usuario["_id"]),
            "nombre": usuario["nombre"],
            "correo": usuario["correo"],
            "rol": usuario.get("rol", "cliente"),
        },
    }


# Autenticación

async def obtener_usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
):
    """Obtiene el usuario actual."""

    if credenciales is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionó un token de autenticación.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        datos_token = decode_access_token(
            credenciales.credentials
        )

    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token es inválido o ha expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    usuario_id = datos_token.get("sub")

    if not usuario_id or not ObjectId.is_valid(usuario_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token no contiene un identificador válido.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    db = get_database()

    usuario = await db["usuarios"].find_one(
        {"_id": ObjectId(usuario_id)}
    )

    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El usuario autenticado ya no existe.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return usuario


# Roles

async def obtener_admin_actual(
    usuario: dict = Depends(obtener_usuario_actual),
):
    """Verifica si es admin."""

    if usuario.get("rol") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos de administrador.",
        )

    return usuario


async def obtener_cliente_actual(
    usuario: dict = Depends(obtener_usuario_actual),
):
    """Verifica si es cliente."""

    if usuario.get("rol", "cliente") != "cliente":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta operación está disponible únicamente para clientes.",
        )

    return usuario


# Consultar usuario

@app.get(
    "/usuarios/me",
    response_model=UsuarioPublico,
    tags=["Usuarios"],
)
async def consultar_usuario_actual(
    usuario: dict = Depends(obtener_usuario_actual),
):
    """Devuelve el usuario actual."""

    return UsuarioPublico(
        id=str(usuario["_id"]),
        nombre=usuario["nombre"],
        correo=usuario["correo"],
        rol=usuario.get("rol", "cliente"),
    )


# Productos

@app.post("/productos/validar", tags=["Productos"])
async def validar_producto(producto: Producto):
    """Valida un producto."""

    return {
        "mensaje": "Producto válido",
        "producto": producto.model_dump(),
    }


@app.post(
    "/productos",
    status_code=status.HTTP_201_CREATED,
    tags=["Productos"],
)
async def crear_producto(
    producto: Producto,
    usuario: dict = Depends(obtener_admin_actual),
):
    """Crea un producto."""

    db = get_database()

    datos_producto = producto.model_dump()

    resultado = await db["productos"].insert_one(
        datos_producto
    )

    return {
        "mensaje": "Producto creado correctamente",
        "id": str(resultado.inserted_id),
        "producto": producto.model_dump(),
    }


@app.get("/productos", tags=["Productos"])
async def listar_productos():
    """Lista los productos y sus imágenes disponibles."""

    db = get_database()

    documentos = await db["productos"].find().to_list(
        length=100
    )

    # Consultar qué productos tienen imágenes.
    ids_productos = [
        documento["_id"]
        for documento in documentos
    ]

    imagenes = await db["imagenes_productos"].find(
        {
            "producto_id": {
                "$in": ids_productos
            }
        },
        {
            "producto_id": 1
        }
    ).to_list(length=100)

    productos_con_imagen = {
        str(imagen["producto_id"])
        for imagen in imagenes
    }

    productos = []

    for documento in documentos:
        producto_id = str(documento.pop("_id"))

        documento["id"] = producto_id

        documento["imagen_url"] = (
            f"/productos/{producto_id}/imagen"
            if producto_id in productos_con_imagen
            else None
        )

        productos.append(documento)

    return {
        "total": len(productos),
        "productos": productos,
    }

# Consultar un producto por su ID
@app.get("/productos/{producto_id}", tags=["Productos"])
async def obtener_producto(producto_id: str):
    """Busca un producto por su identificador."""

    if not ObjectId.is_valid(producto_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El ID del producto no es válido.",
        )

    db = get_database()

    documento = await db["productos"].find_one(
        {"_id": ObjectId(producto_id)}
    )

    if documento is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado.",
        )

    documento["id"] = str(documento.pop("_id"))

    return documento

@app.put("/productos/{producto_id}", tags=["Productos"])
async def actualizar_producto(
    producto_id: str,
    producto: Producto,
    usuario: dict = Depends(obtener_admin_actual)
):
    """Actualiza un producto."""

    if not ObjectId.is_valid(producto_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El ID del producto no es válido.",
        )

    db = get_database()

    resultado = await db["productos"].update_one(
        {"_id": ObjectId(producto_id)},
        {"$set": producto.model_dump()},
    )

    if resultado.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado.",
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
async def eliminar_producto(
    producto_id: str,
    usuario: dict = Depends(obtener_admin_actual),
):
    """Elimina un producto."""

    if not ObjectId.is_valid(producto_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El ID del producto no es válido.",
        )

    db = get_database()

    resultado = await db["productos"].delete_one(
        {"_id": ObjectId(producto_id)}
    )

    if resultado.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado.",
        )

    return {
        "mensaje": "Producto eliminado correctamente",
        "id": producto_id,
    }

# Subir o reemplazar imagen de un producto
@app.post("/productos/{producto_id}/imagen", tags=["Productos"])
async def subir_imagen_producto(
    producto_id: str,
    imagen: UploadFile = File(...),
    usuario: dict = Depends(obtener_admin_actual),
):
    """Almacena una imagen de producto en MongoDB."""

    if not ObjectId.is_valid(producto_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El ID del producto no es válido.",
        )

    db = get_database()

    producto = await db["productos"].find_one(
        {"_id": ObjectId(producto_id)}
    )

    if producto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado.",
        )

    try:
        contenido = await imagen.read(MAX_IMAGE_SIZE + 1)
    finally:
        await imagen.close()

    if not contenido:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La imagen está vacía.",
        )

    if len(contenido) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="La imagen no puede superar los 2 MB.",
        )

    # Verificar el formato real del archivo.
    if contenido.startswith(b"\xff\xd8\xff"):
        content_type = "image/jpeg"

    elif contenido.startswith(b"\x89PNG\r\n\x1a\n"):
        content_type = "image/png"

    elif (
        len(contenido) >= 12
        and contenido[:4] == b"RIFF"
        and contenido[8:12] == b"WEBP"
    ):
        content_type = "image/webp"

    else:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Formato no permitido. Utiliza JPG, PNG o WebP.",
        )

    await db["imagenes_productos"].replace_one(
        {"producto_id": ObjectId(producto_id)},
        {
            "producto_id": ObjectId(producto_id),
            "contenido": Binary(contenido),
            "content_type": content_type,
            "nombre_archivo": imagen.filename or "producto",
            "actualizado_en": datetime.now(timezone.utc),
        },
        upsert=True,
    )

    return {
        "mensaje": "Imagen del producto guardada correctamente.",
        "producto_id": producto_id,
        "imagen_url": f"/productos/{producto_id}/imagen",
    }


# Consultar imagen de un producto
@app.get(
    "/productos/{producto_id}/imagen",
    response_class=Response,
    tags=["Productos"],
)
async def obtener_imagen_producto(producto_id: str):
    """Devuelve la imagen almacenada de un producto."""

    if not ObjectId.is_valid(producto_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El ID del producto no es válido.",
        )

    db = get_database()

    imagen = await db["imagenes_productos"].find_one(
        {"producto_id": ObjectId(producto_id)}
    )

    if imagen is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El producto todavía no tiene una imagen.",
        )

    return Response(
        content=bytes(imagen["contenido"]),
        media_type=imagen["content_type"],
        headers={
            "Cache-Control": "public, max-age=300",
        },
    )
    
# Pedidos

@app.post("/pedidos/validar", tags=["Pedidos"])
async def validar_pedido(pedido: Pedido):
    """Valida un pedido."""

    return {
        "mensaje": "Pedido válido",
        "pedido": pedido.model_dump(mode="json"),
    }


@app.post(
    "/pedidos",
    status_code=status.HTTP_201_CREATED,
    tags=["Pedidos"],
)
async def crear_pedido(
    pedido: PedidoCrear,
    usuario: dict = Depends(obtener_cliente_actual),
):
    """Crea un pedido."""

    db = get_database()

    # Validar IDs
    for articulo in pedido.articulos:
        if not ObjectId.is_valid(articulo.producto_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"ID de producto inválido: "
                    f"{articulo.producto_id}"
                ),
            )

    articulos_pedido = []
    total = 0.0
    creado_en = datetime.now(timezone.utc)

    # Transacción para el pedido e inventario
    async with await db.client.start_session() as session:
        async with session.start_transaction():

            for articulo in pedido.articulos:

                producto_id = ObjectId(
                    articulo.producto_id
                )

                producto = await db["productos"].find_one(
                    {"_id": producto_id},
                    session=session,
                )

                if producto is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=(
                            f"Producto no encontrado: "
                            f"{articulo.producto_id}"
                        ),
                    )

                if not producto.get("activo", True):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"El producto '{producto['nombre']}' "
                            "no está disponible."
                        ),
                    )

                if producto.get("stock", 0) < articulo.cantidad:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"Stock insuficiente para "
                            f"'{producto['nombre']}'."
                        ),
                    )

                # Obtener precio de la BD
                precio = float(producto["precio"])

                subtotal = round(
                    precio * articulo.cantidad,
                    2,
                )

                # Descontar stock
                resultado_stock = await db["productos"].update_one(
                    {
                        "_id": producto_id,
                        "activo": True,
                        "stock": {"$gte": articulo.cantidad},
                    },
                    {
                        "$inc": {
                            "stock": -articulo.cantidad,
                        }
                    },
                    session=session,
                )

                if resultado_stock.modified_count == 0:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "No fue posible reservar el stock "
                            f"de '{producto['nombre']}'."
                        ),
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

            # Datos del pedido
            documento_pedido = {
                "cliente_id": str(usuario["_id"]),
                "cliente": usuario["nombre"],
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
async def listar_pedidos(
    usuario: dict = Depends(obtener_usuario_actual),
):
    """Lista pedidos según el rol."""

    db = get_database()

    rol = usuario.get("rol", "cliente")

    if rol == "admin":
        filtro = {}

    elif rol == "cliente":
        filtro = {
            "cliente_id": str(usuario["_id"]),
        }

    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para consultar pedidos.",
        )

    documentos = await db["pedidos"].find(
        filtro
    ).sort(
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
async def obtener_pedido(
    pedido_id: str,
    usuario: dict = Depends(obtener_usuario_actual),
):
    """Consulta un pedido."""

    if not ObjectId.is_valid(pedido_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El ID del pedido no es válido.",
        )

    db = get_database()

    filtro = {
        "_id": ObjectId(pedido_id),
    }

    rol = usuario.get("rol", "cliente")

    if rol == "cliente":
        filtro["cliente_id"] = str(usuario["_id"])

    elif rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para consultar este pedido.",
        )

    documento = await db["pedidos"].find_one(filtro)

    if documento is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado.",
        )

    documento["id"] = str(documento.pop("_id"))

    return documento


@app.patch(
    "/pedidos/{pedido_id}/estado",
    tags=["Pedidos"],
)
async def actualizar_estado_pedido(
    pedido_id: str,
    datos: ActualizarEstadoPedido,
    usuario: dict = Depends(obtener_admin_actual),
):
    """Actualiza el estado de un pedido."""

    if not ObjectId.is_valid(pedido_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El ID del pedido no es válido.",
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
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Pedido no encontrado.",
                )

            estado_actual = pedido.get(
                "estado",
                "pendiente",
            )

            transiciones_permitidas = {
                "pendiente": {"pagado", "cancelado"},
                "pagado": {"enviado"},
                "enviado": {"entregado"},
                "entregado": set(),
                "cancelado": set(),
            }

            if nuevo_estado not in transiciones_permitidas.get(
                estado_actual,
                set(),
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"No se puede cambiar el pedido de "
                        f"'{estado_actual}' a '{nuevo_estado}'."
                    ),
                )

            # Recuperar inventario si se cancela
            if nuevo_estado == "cancelado":

                for articulo in pedido["articulos"]:

                    producto_id = articulo.get(
                        "producto_id",
                        "",
                    )

                    cantidad = articulo.get(
                        "cantidad",
                        0,
                    )

                    if (
                        not ObjectId.is_valid(producto_id)
                        or cantidad <= 0
                    ):
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=(
                                "No se puede recuperar el inventario "
                                "por los datos de un artículo inválido."
                            ),
                        )

                    resultado_stock = await db["productos"].update_one(
                        {
                            "_id": ObjectId(producto_id),
                        },
                        {
                            "$inc": {
                                "stock": cantidad,
                            }
                        },
                        session=session,
                    )

                    if resultado_stock.matched_count == 0:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=(
                                "No se encontró el producto "
                                f"{producto_id} para recuperar el stock."
                            ),
                        )

            await db["pedidos"].update_one(
                {
                    "_id": ObjectId(pedido_id),
                },
                {
                    "$set": {
                        "estado": nuevo_estado,
                    }
                },
                session=session,
            )

            documento_actualizado = await db["pedidos"].find_one(
                {
                    "_id": ObjectId(pedido_id),
                },
                session=session,
            )

    documento_actualizado["id"] = str(
        documento_actualizado.pop("_id")
    )

    return {
        "mensaje": "Estado del pedido actualizado correctamente",
        "pedido": documento_actualizado,
    }