import requests
import os
from functools import wraps

from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.http import HttpResponseForbidden
from django.contrib import messages

# Dirección del backend FastAPI
FASTAPI_URL = os.environ.get(
    "FASTAPI_URL",
    "http://127.0.0.1:8000"
).rstrip("/")

# Completar las direcciones de las imágenes de FastAPI
def completar_urls_imagenes(productos):
    for producto in productos:
        imagen_url = producto.get("imagen_url")

        if imagen_url:
            producto["imagen_url"] = f"{FASTAPI_URL}{imagen_url}"

    return productos

# Permisos de administrador
def requiere_admin(vista):
    @wraps(vista)
    def verificar_acceso(request, *args, **kwargs):
        usuario = request.session.get("usuario")

        if not usuario:
            return redirect("login")

        if usuario.get("rol") != "admin":
            return HttpResponseForbidden(
                "No tienes permisos para acceder a esta sección."
            )

        return vista(request, *args, **kwargs)

    return verificar_acceso


# Permisos de cliente
def requiere_cliente(vista):
    @wraps(vista)
    def verificar_acceso(request, *args, **kwargs):
        usuario = request.session.get("usuario")

        if not usuario:
            return redirect("login")

        if usuario.get("rol", "cliente") != "cliente":
            return HttpResponseForbidden(
                "Esta sección es exclusiva para clientes."
            )

        return vista(request, *args, **kwargs)

    return verificar_acceso


# Obtener token
def obtener_headers_jwt(request):
    token = request.COOKIES.get("techgear_access_token")

    if not token:
        return None

    return {
        "Authorization": f"Bearer {token}"
    }


# Cerrar sesión si el token no es válido
def redirigir_login_token(request):
    request.session.flush()

    respuesta = redirect("login")

    respuesta.delete_cookie(
        "techgear_access_token",
        path="/",
        samesite="Lax",
    )

    return respuesta


# Catálogo de productos
def catalogo(request):
    productos = []
    total = 0
    error = None

    try:
        respuesta = requests.get(
            f"{FASTAPI_URL}/productos",
            timeout=5,
        )

        respuesta.raise_for_status()

        datos = respuesta.json()

        productos = datos.get("productos", [])
        productos = completar_urls_imagenes(productos)
        total = datos.get("total", len(productos))

    except (requests.RequestException, ValueError):
        error = (
            "No fue posible consultar el catálogo. "
            "Verifica que FastAPI esté ejecutándose."
        )

    return render(
        request,
        "store/catalogo.html",
        {
            "productos": productos,
            "total": total,
            "error": error,
            "usuario": request.session.get("usuario"),
        },
    )


# Crear pedidos
@requiere_cliente
@require_POST
def crear_pedido_cliente(request):
    headers = obtener_headers_jwt(request)

    if not headers:
        return redirigir_login_token(request)

    producto_id = request.POST.get(
        "producto_id", ""
    ).strip()

    cantidad = request.POST.get(
        "cantidad", "1"
    ).strip()

    notas = request.POST.get(
        "notas", ""
    ).strip() or None

    try:
        cantidad = int(cantidad)

        if cantidad <= 0:
            raise ValueError

    except ValueError:
        messages.error(
            request,
            "La cantidad debe ser un número entero mayor que cero."
        )
        return redirect("catalogo")

    datos_pedido = {
        "articulos": [
            {
                "producto_id": producto_id,
                "cantidad": cantidad,
            }
        ],
        "notas": notas,
    }

    try:
        respuesta = requests.post(
            f"{FASTAPI_URL}/pedidos",
            json=datos_pedido,
            headers=headers,
            timeout=5,
        )

    except requests.RequestException:
        messages.error(
            request,
            "No fue posible conectar con el servidor de pedidos."
        )
        return redirect("catalogo")

    try:
        datos_respuesta = respuesta.json()

    except ValueError:
        datos_respuesta = {}

    if respuesta.status_code == 201:
        messages.success(
            request,
            f"Pedido registrado correctamente. "
            f"Referencia: {datos_respuesta.get('id', '')}"
        )

        return redirect("mis_pedidos")

    if respuesta.status_code == 401:
        return redirigir_login_token(request)

    detalle = datos_respuesta.get(
        "detail",
        "No fue posible registrar el pedido."
    )

    if isinstance(detalle, list):
        detalle = "; ".join(
            elemento.get("msg", "Dato inválido")
            for elemento in detalle
        )

    messages.error(request, detalle)

    return redirect("catalogo")


# Consultar mis pedidos
@requiere_cliente
def mis_pedidos(request):
    headers = obtener_headers_jwt(request)

    if not headers:
        return redirigir_login_token(request)

    pedidos = []
    total = 0
    error = None

    try:
        respuesta = requests.get(
            f"{FASTAPI_URL}/pedidos",
            headers=headers,
            timeout=5,
        )

        if respuesta.status_code == 401:
            return redirigir_login_token(request)

        respuesta.raise_for_status()

        datos = respuesta.json()

        pedidos = datos.get("pedidos", [])
        total = datos.get("total", len(pedidos))

    except requests.RequestException:
        error = "No fue posible consultar tus pedidos."

    except ValueError:
        error = "El servidor devolvió una respuesta inválida."

    return render(
        request,
        "store/mis_pedidos.html",
        {
            "pedidos": pedidos,
            "total": total,
            "error": error,
            "usuario": request.session.get("usuario"),
        },
    )


# Registrar usuario
def registrar_usuario(request):
    if request.method == "GET":
        return render(request, "store/registro.html")

    nombre = request.POST.get("nombre", "").strip()
    correo = request.POST.get("correo", "").strip().lower()
    contrasena = request.POST.get("contrasena", "")
    confirmar_contrasena = request.POST.get(
        "confirmar_contrasena", ""
    )

    if not nombre or not correo or not contrasena:
        return render(
            request,
            "store/registro.html",
            {
                "error": "Debes completar todos los campos.",
                "nombre": nombre,
                "correo": correo,
            },
            status=400,
        )

    if contrasena != confirmar_contrasena:
        return render(
            request,
            "store/registro.html",
            {
                "error": "Las contraseñas no coinciden.",
                "nombre": nombre,
                "correo": correo,
            },
            status=400,
        )

    if len(contrasena) < 8 or len(contrasena) > 128:
        return render(
            request,
            "store/registro.html",
            {
                "error": "La contraseña debe tener entre 8 y 128 caracteres.",
                "nombre": nombre,
                "correo": correo,
            },
            status=400,
        )

    try:
        respuesta = requests.post(
            f"{FASTAPI_URL}/usuarios",
            json={
                "nombre": nombre,
                "correo": correo,
                "contrasena": contrasena,
            },
            timeout=5,
        )

    except requests.RequestException:
        return render(
            request,
            "store/registro.html",
            {
                "error": "No fue posible conectar con el servidor.",
                "nombre": nombre,
                "correo": correo,
            },
            status=503,
        )

    try:
        datos = respuesta.json()
    except ValueError:
        datos = {}

    if respuesta.status_code == 201:
        messages.success(
            request,
            "Tu cuenta fue creada correctamente. Ya puedes iniciar sesión."
        )
        return redirect("login")

    if respuesta.status_code == 409:
        error = "Ya existe una cuenta registrada con ese correo."

    elif respuesta.status_code == 422:
        detalle = datos.get("detail", [])
        if isinstance(detalle, list):
            error = "; ".join(
                elemento.get("msg", "Dato inválido")
                for elemento in detalle
            )
        else:
            error = str(detalle)

    else:
        error = "No fue posible completar el registro. Inténtalo nuevamente."

    return render(
        request,
        "store/registro.html",
        {
            "error": error,
            "nombre": nombre,
            "correo": correo,
        },
        status=400,
    )


# Inicio de sesión
def iniciar_sesion(request):
    if request.method == "GET":
        return render(request, "store/login.html")

    correo = request.POST.get(
        "correo", ""
    ).strip().lower()

    contrasena = request.POST.get(
        "contrasena", ""
    )

    if not correo or not contrasena:
        return render(
            request,
            "store/login.html",
            {"error": "Debes completar todos los campos."},
            status=400,
        )

    try:
        respuesta = requests.post(
            f"{FASTAPI_URL}/usuarios/login",
            json={
                "correo": correo,
                "contrasena": contrasena,
            },
            timeout=5,
        )

    except requests.RequestException:
        return render(
            request,
            "store/login.html",
            {"error": "No fue posible conectar con el servidor."},
            status=503,
        )

    if respuesta.status_code == 401:
        return render(
            request,
            "store/login.html",
            {"error": "Correo o contraseña incorrectos."},
            status=401,
        )

    if respuesta.status_code != 200:
        return render(
            request,
            "store/login.html",
            {"error": "No fue posible iniciar sesión. Verifica tus datos."},
            status=502,
        )

    try:
        datos = respuesta.json()

    except ValueError:
        return render(
            request,
            "store/login.html",
            {"error": "El servidor devolvió una respuesta inválida."},
            status=502,
        )

    token = datos.get("access_token")
    usuario = datos.get("usuario")

    if not token or not isinstance(usuario, dict):
        return render(
            request,
            "store/login.html",
            {"error": "No se recibió una autenticación válida."},
            status=502,
        )

    request.session.flush()

    request.session["usuario"] = {
        "id": usuario["id"],
        "nombre": usuario["nombre"],
        "correo": usuario["correo"],
        "rol": usuario.get("rol", "cliente"),
    }

    request.session.set_expiry(30 * 60)

    if usuario.get("rol") == "admin":
        respuesta_django = redirect("dashboard_admin")
    else:
        respuesta_django = redirect("catalogo")

    respuesta_django.set_cookie(
        key="techgear_access_token",
        value=token,
        max_age=30 * 60,
        httponly=True,
        secure=request.is_secure(),
        samesite="Lax",
        path="/",
    )

    return respuesta_django


# Cerrar sesión
@require_POST
def cerrar_sesion(request):
    request.session.flush()

    respuesta = redirect("catalogo")

    respuesta.delete_cookie(
        "techgear_access_token",
        path="/",
        samesite="Lax",
    )

    return respuesta


# Dashboard administrativo
@requiere_admin
def dashboard_admin(request):
    productos = []
    total = 0
    error = None

    try:
        respuesta = requests.get(
            f"{FASTAPI_URL}/productos",
            timeout=5,
        )

        respuesta.raise_for_status()

        datos = respuesta.json()

        productos = datos.get("productos", [])
        total = datos.get("total", len(productos))

    except (requests.RequestException, ValueError):
        error = "No fue posible consultar los productos de FastAPI."

    return render(
        request,
        "store/dashboard.html",
        {
            "productos": productos,
            "total": total,
            "error": error,
            "usuario": request.session.get("usuario"),
        },
    )


# Crear productos
# Crear productos
@requiere_admin
def crear_producto(request):
    error = None

    if request.method == "POST":
        headers = obtener_headers_jwt(request)

        if not headers:
            return redirigir_login_token(request)

        imagen = request.FILES.get("imagen")

        # Validar la fotografía seleccionada.
        if imagen and imagen.size > 2 * 1024 * 1024:
            error = "La imagen no puede superar los 2 MB."

        elif imagen and imagen.content_type not in [
            "image/jpeg",
            "image/png",
            "image/webp",
        ]:
            error = "Utiliza una imagen JPG, PNG o WebP."

        if not error:
            datos_producto = {
                "nombre": request.POST.get("nombre", "").strip(),
                "descripcion": request.POST.get("descripcion", "").strip() or None,
                "precio": request.POST.get("precio", "").strip(),
                "stock": request.POST.get("stock", "0").strip(),
                "activo": request.POST.get("activo") == "on",
            }

            try:
                # Crear primero el producto en FastAPI.
                respuesta = requests.post(
                    f"{FASTAPI_URL}/productos",
                    json=datos_producto,
                    headers=headers,
                    timeout=10,
                )

                if respuesta.status_code == 401:
                    return redirigir_login_token(request)

                try:
                    datos_respuesta = respuesta.json()
                except ValueError:
                    datos_respuesta = {}

                if respuesta.status_code == 201:
                    producto_id = datos_respuesta.get("id")

                    # Subir la fotografía del producto creado.
                    if imagen and producto_id:
                        try:
                            imagen.seek(0)

                            respuesta_imagen = requests.post(
                                f"{FASTAPI_URL}/productos/{producto_id}/imagen",
                                files={
                                    "imagen": (
                                        imagen.name,
                                        imagen,
                                        imagen.content_type,
                                    )
                                },
                                headers=headers,
                                timeout=15,
                            )

                            if respuesta_imagen.status_code == 401:
                                return redirigir_login_token(request)

                            if respuesta_imagen.status_code == 200:
                                messages.success(
                                    request,
                                    "Producto y fotografía registrados correctamente.",
                                )
                            else:
                                messages.warning(
                                    request,
                                    "El producto fue creado, pero no se pudo guardar su fotografía.",
                                )

                        except requests.RequestException:
                            messages.warning(
                                request,
                                "Producto creado, pero ocurrió un error al subir la fotografía.",
                            )

                    else:
                        messages.success(
                            request,
                            "Producto creado correctamente.",
                        )

                    return redirect("dashboard_admin")

                detalle = datos_respuesta.get("detail")

                if isinstance(detalle, list):
                    errores = []

                    for elemento in detalle:
                        campo = ".".join(
                            str(parte)
                            for parte in elemento.get("loc", [])
                            if parte != "body"
                        )

                        mensaje = elemento.get("msg", "Dato inválido")
                        errores.append(f"{campo}: {mensaje}")

                    error = "; ".join(errores)

                else:
                    error = detalle or "No fue posible crear el producto."

            except requests.RequestException:
                error = "No fue posible conectar con FastAPI."

    return render(
        request,
        "store/formulario_producto.html",
        {
            "error": error,
            "usuario": request.session.get("usuario"),
        },
    )


# Editar productos
@requiere_admin
def editar_producto(request, producto_id):
    error = None
    producto = None

    if request.method == "POST":
        headers = obtener_headers_jwt(request)

        if not headers:
            return redirigir_login_token(request)

        imagen = request.FILES.get("imagen")

        # Validar el tamaño de la fotografía.
        if imagen and imagen.size > 2 * 1024 * 1024:
            error = "La imagen no puede superar los 2 MB."

        if not error:
            datos_producto = {
                "nombre": request.POST.get("nombre", "").strip(),
                "descripcion": request.POST.get("descripcion", "").strip() or None,
                "precio": request.POST.get("precio", "").strip(),
                "stock": request.POST.get("stock", "0").strip(),
                "activo": request.POST.get("activo") == "on",
            }

            try:
                # Actualizar los datos del producto.
                respuesta = requests.put(
                    f"{FASTAPI_URL}/productos/{producto_id}",
                    json=datos_producto,
                    headers=headers,
                    timeout=10,
                )

                if respuesta.status_code == 401:
                    return redirigir_login_token(request)

                if respuesta.status_code == 200:

                    # Reemplazar la fotografía si se seleccionó otra.
                    if imagen:
                        try:
                            imagen.seek(0)

                            respuesta_imagen = requests.post(
                                f"{FASTAPI_URL}/productos/{producto_id}/imagen",
                                files={
                                    "imagen": (
                                        imagen.name,
                                        imagen,
                                        imagen.content_type,
                                    )
                                },
                                headers=headers,
                                timeout=15,
                            )

                            if respuesta_imagen.status_code == 401:
                                return redirigir_login_token(request)

                            if respuesta_imagen.status_code == 200:
                                messages.success(
                                    request,
                                    "Producto y fotografía actualizados correctamente.",
                                )
                            else:
                                messages.warning(
                                    request,
                                    "Los datos se actualizaron, pero no se pudo cambiar la fotografía.",
                                )

                        except requests.RequestException:
                            messages.warning(
                                request,
                                "Los datos se actualizaron, pero ocurrió un error al subir la fotografía.",
                            )

                    else:
                        messages.success(
                            request,
                            "Producto actualizado correctamente.",
                        )

                    return redirect("dashboard_admin")

                try:
                    datos_respuesta = respuesta.json()
                except ValueError:
                    datos_respuesta = {}

                detalle = datos_respuesta.get("detail")

                if isinstance(detalle, list):
                    error = "; ".join(
                        elemento.get("msg", "Dato inválido")
                        for elemento in detalle
                    )
                else:
                    error = detalle or "No fue posible actualizar el producto."

            except requests.RequestException:
                error = "No fue posible conectar con FastAPI."

    # Consultar los datos actuales del producto.
    try:
        respuesta_producto = requests.get(
            f"{FASTAPI_URL}/productos/{producto_id}",
            timeout=5,
        )

        if respuesta_producto.status_code == 404:
            messages.error(request, "El producto no existe.")
            return redirect("dashboard_admin")

        respuesta_producto.raise_for_status()
        producto = respuesta_producto.json()

    except requests.RequestException:
        error = "No fue posible consultar el producto en FastAPI."

    except ValueError:
        error = "El servidor devolvió una respuesta inválida."

    return render(
        request,
        "store/formulario_editar_producto.html",
        {
            "producto": producto,
            "error": error,
            "usuario": request.session.get("usuario"),
        },
    )


# Eliminar productos
@requiere_admin
@require_POST
def eliminar_producto(request, producto_id):
    headers = obtener_headers_jwt(request)

    if not headers:
        return redirigir_login_token(request)

    try:
        respuesta = requests.delete(
            f"{FASTAPI_URL}/productos/{producto_id}",
            headers=headers,
            timeout=5,
        )
        
        if respuesta.status_code == 401:
            return redirigir_login_token(request)

        if respuesta.status_code == 200:
            messages.success(
                request,
                "Producto eliminado correctamente."
            )

        elif respuesta.status_code == 404:
            messages.error(
                request,
                "El producto no existe o ya fue eliminado."
            )

        else:
            try:
                detalle = respuesta.json().get("detail")
            except ValueError:
                detalle = None

            messages.error(
                request,
                detalle or "No fue posible eliminar el producto."
            )

    except requests.RequestException:
        messages.error(
            request,
            "No fue posible conectar con FastAPI."
        )

    return redirect("dashboard_admin")
