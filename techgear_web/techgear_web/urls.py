"""
URL configuration for techgear_web project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from store import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Catálogo
    path('', views.catalogo, name='catalogo'),

    # Inicio de sesión
    path('login/', views.iniciar_sesion, name='login'),

    # Cierre de sesión
    path('logout/', views.cerrar_sesion, name='logout'),

    # Dashboard administrativo
    path('dashboard/', views.dashboard_admin, name='dashboard_admin'),

    # Crear productos
    path(
        'dashboard/productos/nuevo/',
        views.crear_producto,
        name='crear_producto'
    ),
    # Editar productos
    path(
        'dashboard/productos/<str:producto_id>/editar/',
        views.editar_producto,
        name='editar_producto'
    ),
    
    # Eliminar productos
path(
    'dashboard/productos/<str:producto_id>/eliminar/',
    views.eliminar_producto,
    name='eliminar_producto'
),

    # Pedidos
    path(
        'pedidos/',
        views.mis_pedidos,
        name='mis_pedidos'
    ),
    path(
        'pedidos/nuevo/',
        views.crear_pedido_cliente,
        name='crear_pedido_cliente'
    ),
]