import requests

from django.conf import settings
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from functools import wraps
from django.http import HttpResponseForbidden
from django.contrib import messages

def requiere_admin(vista):
    """Restringe el acceso exclusivamente a usuarios administradores."""

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

def catalogo(request):
    productos = []
    total = 0
    error = None

    try:
        respuesta = requests.get(
            "http://127.0.0.1:8000/productos",
            timeout=5,
        )
        respuesta.raise_for_status()

        datos = respuesta.json()
        productos = datos.get("productos", [])
        total = datos.get("total", len(productos))

    except requests.RequestException:
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

def iniciar_sesion(request):
    """Consume el login de FastAPI y gestiona la sesión de Django."""

    if request.method == "GET":
        return render(request, "store/login.html")

    correo = request.POST.get("correo", "").strip().lower()
    contrasena = request.POST.get("contrasena", "")

    if not correo or not contrasena:
        return render(
            request,
            "store/login.html",
            {"error": "Debes completar todos los campos."},
            status=400,
        )

    try:
        respuesta = requests.post(
            "http://127.0.0.1:8000/usuarios/login",
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
    except requests.exceptions.JSONDecodeError:
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

    # Evitar reutilizar una sesión anterior.
    request.session.flush()

    # Guardar únicamente información pública del usuario.
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

    # Guardar el JWT en una cookie HttpOnly.
    respuesta_django.set_cookie(
        key="techgear_access_token",
        value=token,
        max_age=30 * 60,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        path="/",
    )

    return respuesta_django

@require_POST
def cerrar_sesion(request):
    """Cierra la sesión y elimina la cookie JWT."""

    request.session.flush()

    respuesta = redirect("catalogo")

    respuesta.delete_cookie(
        "techgear_access_token",
        path="/",
        samesite="Lax",
    )

    return respuesta

@requiere_admin
def dashboard_admin(request):
    """Muestra los productos en el panel administrativo."""

    productos = []
    total = 0
    error = None

    try:
        respuesta = requests.get(
            "http://127.0.0.1:8000/productos",
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

@requiere_admin
def crear_producto(request):
    """Permite al administrador registrar productos mediante FastAPI."""

    error = None

    if request.method == "POST":

        datos_producto = {
            "nombre": request.POST.get("nombre", "").strip(),
            "descripcion": request.POST.get("descripcion", "").strip() or None,
            "precio": request.POST.get("precio", "").strip(),
            "stock": request.POST.get("stock", "0").strip(),
            "activo": request.POST.get("activo") == "on",
        }

        try:
            respuesta = requests.post(
                "http://127.0.0.1:8000/productos",
                json=datos_producto,
                timeout=5,
            )

            try:
                datos_respuesta = respuesta.json()
            except ValueError:
                datos_respuesta = {}

            if respuesta.status_code == 201:
                messages.success(
                    request,
                    "Producto creado correctamente."
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

@requiere_admin
def editar_producto(request, producto_id):
    """Permite al administrador actualizar un producto mediante FastAPI."""

    error = None
    producto = None

    if request.method == "POST":

        datos_producto = {
            "nombre": request.POST.get("nombre", "").strip(),
            "descripcion": request.POST.get("descripcion", "").strip() or None,
            "precio": request.POST.get("precio", "").strip(),
            "stock": request.POST.get("stock", "0").strip(),
            "activo": request.POST.get("activo") == "on",
        }

        try:
            respuesta = requests.put(
                f"http://127.0.0.1:8000/productos/{producto_id}",
                json=datos_producto,
                timeout=5,
            )

            if respuesta.status_code == 200:
                messages.success(
                    request,
                    "Producto actualizado correctamente."
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

    try:
        respuesta_producto = requests.get(
            f"http://127.0.0.1:8000/productos/{producto_id}",
            timeout=5,
        )

        if respuesta_producto.status_code == 404:
            messages.error(request, "El producto no existe.")
            return redirect("dashboard_admin")

        respuesta_producto.raise_for_status()
        producto = respuesta_producto.json()

    except requests.RequestException:
        error = "No fue posible consultar el producto en FastAPI."

    return render(
        request,
        "store/formulario_editar_producto.html",
        {
            "producto": producto,
            "error": error,
            "usuario": request.session.get("usuario"),
        },
    )
    
@requiere_admin
@require_POST
def eliminar_producto(request, producto_id):
    """Permite al administrador eliminar productos mediante FastAPI."""

    try:
        respuesta = requests.delete(
            f"http://127.0.0.1:8000/productos/{producto_id}",
            timeout=5,
        )

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