import requests

from django.conf import settings
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

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
    }

    request.session.set_expiry(30 * 60)

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