# TechGear — Sistema híbrido de catálogo y pedidos

Aplicación web de comercio tecnológico desarrollada como un sistema híbrido. **FastAPI** funciona como microservicio de negocio y expone la API REST conectada a **MongoDB Atlas**. **Django** implementa el portal web mediante el patrón MVT (Modelo–Vista–Plantilla), renderiza las páginas HTML y consume la API de FastAPI.

El proyecto contempla usuarios con roles de administrador y cliente, catálogo de productos, gestión de inventario, pedidos y carga de imágenes de productos.

---

## Tabla de contenido

1. [Arquitectura](#arquitectura)
2. [Tecnologías](#tecnologías)
3. [Funcionalidades](#funcionalidades)
4. [Requisitos previos](#requisitos-previos)
5. [Clonar el repositorio](#clonar-el-repositorio)
6. [Crear y activar el entorno virtual](#crear-y-activar-el-entorno-virtual)
7. [Configurar FastAPI y MongoDB Atlas](#configurar-fastapi-y-mongodb-atlas)
8. [Configurar Django](#configurar-django)
9. [Ejecutar el proyecto localmente](#ejecutar-el-proyecto-localmente)
10. [Rutas y documentación](#rutas-y-documentación)
11. [Estructura del repositorio](#estructura-del-repositorio)
12. [Despliegue](#despliegue)
13. [Variables de entorno](#variables-de-entorno)
14. [Solución de problemas](#solución-de-problemas)
15. [Flujo de Git](#flujo-de-git)
16. [Seguridad](#seguridad)

---

## Arquitectura

El sistema está dividido en dos aplicaciones independientes que se comunican por HTTP:

| Componente | Responsabilidad | Despliegue |
|---|---|---|
| **Django (`techgear_web`)** | Portal web, plantillas HTML, sesiones, navegación y formularios para administradores y clientes. | Vercel |
| **FastAPI (`techgear_api`)** | API REST, autenticación basada en JWT, lógica de productos y pedidos, inventario y servicio de imágenes. | Render |
| **MongoDB Atlas** | Persistencia de usuarios, productos, pedidos e imágenes. | Servicio administrado en la nube |

### Comunicación entre los componentes

- El navegador del usuario accede al portal Django.
- Django realiza solicitudes HTTP a FastAPI usando la variable `FASTAPI_URL`.
- FastAPI consulta y actualiza la base de datos MongoDB Atlas.
- Las imágenes de los productos se guardan en MongoDB y se sirven mediante los endpoints de imágenes de FastAPI. Django utiliza las URL que devuelve la API para mostrarlas en el catálogo.

**Importante:** Django no debe usar `127.0.0.1` para comunicarse con FastAPI en producción. En Vercel, `FASTAPI_URL` debe contener la URL pública de Render.

---

## Tecnologías

- Python 3.14 (versión fijada para el despliegue de Django en Vercel mediante `.python-version`).
- FastAPI y Uvicorn.
- Django 6.1.2.
- MongoDB Atlas.
- Motor (cliente asíncrono de MongoDB utilizado por la API).
- Pydantic.
- PyJWT y pwdlib con Argon2 para autenticación y hash de contraseñas.
- Requests para la comunicación HTTP entre Django y FastAPI.
- WhiteNoise para servir archivos estáticos de Django.
- HTML5 y CSS3 para las plantillas del portal.

---

## Funcionalidades

### Portal Django

- Catálogo público de productos.
- Registro e inicio de sesión de usuarios.
- Navegación según el rol autenticado: administrador o cliente.
- Dashboard administrativo para consultar, crear, editar y eliminar productos.
- Formularios de carga de imágenes de productos.
- Consulta de pedidos del cliente.
- Formularios para realizar pedidos.
- Plantillas adaptables a escritorio, tableta y móvil.

### API FastAPI

- Comprobación de estado del servicio y conexión con MongoDB.
- Registro e inicio de sesión de usuarios.
- Emisión y validación de tokens JWT.
- Consulta y operaciones CRUD de productos, con protección de las operaciones administrativas.
- Creación y consulta de pedidos y validación de sus estados.
- Consulta de productos con sus URL de imagen.
- Carga y consulta de imágenes JPG/JPEG, PNG y WebP. El endpoint de carga valida el tipo de imagen y limita el tamaño del archivo a 2 MB.

### Persistencia

La base de datos utilizada por el proyecto se denomina `techgear`. Entre las colecciones utilizadas por la aplicación se encuentran:

- `usuarios`
- `productos`
- `pedidos`
- `imagenes_productos`

Las imágenes se almacenan en MongoDB; las copias locales de imágenes de productos no son necesarias para que el catálogo las consulte cuando la API y MongoDB están disponibles.

---

## Requisitos previos

Antes de comenzar, instala o prepara:

1. **Git**, para clonar y versionar el repositorio.
2. **Python 3.14**, recomendado para mantener la misma versión fijada para Vercel. El entorno virtual debe crearse con esa versión cuando esté disponible.
3. **MongoDB Atlas**, con un clúster, una base de datos y un usuario con permisos de lectura y escritura.
4. **Visual Studio Code** u otro editor de código.
5. **PowerShell** en Windows (los comandos de esta guía están escritos para PowerShell).

El proyecto local también puede ejecutarse desde otros sistemas operativos, adaptando los comandos de activación del entorno virtual.

---

## Clonar el repositorio

Abre PowerShell en la carpeta donde deseas guardar el proyecto y ejecuta:

```powershell
git clone https://github.com/sebas17-code/Taller2-Api.git
```

Entra en el directorio del repositorio:

```powershell
cd Taller2-Api
```

Abre el proyecto en Visual Studio Code:

```powershell
code .
```

Si el comando `code` no está disponible, abre Visual Studio Code manualmente y selecciona **File → Open Folder** para abrir la carpeta `Taller2-Api`.

---

## Crear y activar el entorno virtual

Desde la carpeta raíz `Taller2-Api`, crea un entorno virtual con Python 3.14:

```powershell
py -3.14 -m venv .venv
```

Actívalo:

```powershell
.\.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea la activación por la política de ejecución, permite scripts solo en la sesión actual y vuelve a activarlo:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Actualiza `pip` e instala las dependencias de ambas aplicaciones:

```powershell
python -m pip install --upgrade pip
pip install -r .\techgear_api\requirements.txt
pip install -r .\techgear_web\requirements.txt
```

Comprueba la versión activa de Python:

```powershell
python --version
```

> **Carga de imágenes:** FastAPI necesita el paquete `python-multipart` para recibir formularios multipart y archivos mediante `UploadFile`. Verifica que `python-multipart` esté incluido en `techgear_api/requirements.txt` antes de instalar y desplegar la API.

---

## Configurar FastAPI y MongoDB Atlas

### 1. Crear el archivo `.env`

En la raíz del repositorio, crea el archivo:

```text
techgear_api/.env
```

Puedes abrirlo desde PowerShell con:

```powershell
notepad .\techgear_api\.env
```

Agrega las variables siguientes y reemplaza los valores de ejemplo por los datos privados de tu clúster:

```dotenv
MONGODB_URI="mongodb+srv://USUARIO:CONTRASENA@CLUSTER/techgear?retryWrites=true&w=majority"
MONGODB_DATABASE=techgear
JWT_SECRET_KEY=REEMPLAZAR_POR_UNA_CLAVE_ALEATORIA_DE_AL_MENOS_32_CARACTERES
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

- `MONGODB_URI`: cadena de conexión de MongoDB Atlas. Reemplaza usuario, contraseña, clúster y demás parámetros por los datos reales entregados por Atlas.
- `MONGODB_DATABASE`: nombre de la base de datos (`techgear`).
- `JWT_SECRET_KEY`: clave privada usada para firmar los tokens JWT. Debe tener al menos 32 caracteres.
- `JWT_ALGORITHM`: algoritmo de firma. El valor predeterminado de la aplicación es `HS256`.
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`: duración del token en minutos. El valor predeterminado es `30`.

Puedes generar una clave JWT aleatoria desde PowerShell:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copia el resultado directamente en el archivo `.env`, como valor de `JWT_SECRET_KEY`. No publiques ni compartas esa clave.

### 2. Permitir la conexión desde MongoDB Atlas

En MongoDB Atlas:

1. Abre **Security → Network Access**.
2. Configura el acceso de red necesario para el entorno desde el que se ejecuta la API.
3. En **Database Access**, verifica que el usuario de base de datos exista y tenga permisos sobre `techgear`.
4. Comprueba que la contraseña y el nombre del clúster de `MONGODB_URI` sean correctos. Si la contraseña contiene caracteres especiales, codifícala para usarla en una URI.

No uses una URI de producción en archivos de ejemplo, capturas, commits o mensajes públicos.

---

## Configurar Django

Django necesita una clave propia, independiente de `JWT_SECRET_KEY`.

### 1. Crear `DJANGO_SECRET_KEY` en Windows

Si es una instalación nueva, genera una clave y guárdala como variable de entorno del usuario:

```powershell
$claveDjango = python -c "import secrets; print(secrets.token_urlsafe(48))"
[Environment]::SetEnvironmentVariable("DJANGO_SECRET_KEY", $claveDjango, "User")
$env:DJANGO_SECRET_KEY = $claveDjango
Remove-Variable claveDjango
```

La variable persistente estará disponible en nuevas terminales de PowerShell. Si ya existe una clave para este proyecto, no es necesario generar otra.

Para cargar la variable en una terminal que ya estaba abierta:

```powershell
$env:DJANGO_SECRET_KEY = [Environment]::GetEnvironmentVariable("DJANGO_SECRET_KEY", "User")
```

Verifica que exista sin imprimir su contenido:

```powershell
if ([string]::IsNullOrWhiteSpace($env:DJANGO_SECRET_KEY)) {
    Write-Host "Falta DJANGO_SECRET_KEY"
} else {
    Write-Host "DJANGO_SECRET_KEY está configurada"
}
```

### 2. Configurar la URL de FastAPI para desarrollo local

En una terminal donde vayas a ejecutar Django, define:

```powershell
$env:FASTAPI_URL = "http://127.0.0.1:8000"
```

El código de `store/views.py` tiene esa dirección como valor predeterminado, pero declararla explícitamente facilita distinguir el entorno local del de producción.

---

## Ejecutar el proyecto localmente

Es necesario mantener **dos terminales de PowerShell abiertas**: una para FastAPI y otra para Django. Los dos servicios deben estar ejecutándose para que el portal pueda mostrar los datos de la API.

### Terminal 1: iniciar FastAPI

Desde la raíz `Taller2-Api`, activa el entorno virtual y ejecuta:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn techgear_api.src.main:app --reload
```

La API quedará disponible en:

- API: <http://127.0.0.1:8000>
- Documentación interactiva: <http://127.0.0.1:8000/docs>
- OpenAPI: <http://127.0.0.1:8000/openapi.json>
- Estado y conexión con MongoDB: <http://127.0.0.1:8000/health>

Una respuesta esperada del endpoint `/health`, cuando MongoDB esté conectado, es:

```json
{
  "status": "ok",
  "mongodb_conectado": true
}
```

### Terminal 2: comprobar y ejecutar Django

Abre una segunda terminal en la raíz `Taller2-Api` y ejecuta:

```powershell
.\.venv\Scripts\Activate.ps1
$env:DJANGO_SECRET_KEY = [Environment]::GetEnvironmentVariable("DJANGO_SECRET_KEY", "User")
$env:FASTAPI_URL = "http://127.0.0.1:8000"
```

Comprueba la configuración de Django:

```powershell
python .\techgear_web\manage.py check
```

Recolecta los archivos estáticos:

```powershell
python .\techgear_web\manage.py collectstatic --noinput
```

Inicia el portal:

```powershell
python .\techgear_web\manage.py runserver 127.0.0.1:8001
```

Abre el portal en:

<http://127.0.0.1:8001/>

Para probar el proyecto, mantén ambas terminales abiertas. Si se detiene FastAPI, Django no podrá consultar productos, pedidos ni imágenes a través de la API.

---

## Rutas y documentación

### Django

| Ruta | Descripción |
|---|---|
| `/` | Catálogo público de productos. |
| `/login/` | Inicio de sesión. |
| `/registro/` | Registro de clientes. |
| `/dashboard/` | Panel administrativo. Requiere permisos de administrador. |
| `/pedidos/` | Consulta de pedidos del cliente. |

Las rutas de creación, edición y eliminación de productos y pedidos están definidas en `techgear_web/techgear_web/urls.py`. Consulta ese archivo para revisar sus nombres y parámetros exactos.

### FastAPI

La documentación interactiva de FastAPI es la referencia principal para consultar métodos, parámetros, respuestas y requisitos de autenticación:

- `/docs`: documentación Swagger UI.
- `/health`: estado del servicio y conexión a MongoDB.
- `/productos`: operaciones del catálogo.
- `/productos/{producto_id}`: consulta y operaciones sobre un producto específico.
- `/productos/{producto_id}/imagen`: carga y consulta de la imagen de un producto.
- `/pedidos`: operaciones de pedidos.
- `/usuarios` y `/usuarios/login`: registro e inicio de sesión mediante la API.

Algunas operaciones requieren un token JWT y permisos de administrador. Consulta `/docs` para identificar qué operaciones requieren autenticación y qué esquema de datos espera cada endpoint.

---

## Estructura del repositorio

La estructura principal del proyecto es:

```text
Taller2-Api/
│
├── techgear_api/
│   ├── data/
│   │   └── database.py          # Conexión con MongoDB Atlas
│   ├── src/
│   │   ├── main.py               # Aplicación y endpoints FastAPI
│   │   ├── security.py           # JWT y seguridad
│   │   └── models/               # Modelos y validaciones Pydantic
│   ├── .env                      # Variables locales (no subir a Git)
│   └── requirements.txt          # Dependencias de FastAPI
│
├── techgear_web/
│   ├── manage.py                 # Entrada de comandos Django
│   ├── .python-version           # Python 3.14 para Vercel
│   ├── requirements.txt          # Dependencias de Django
│   ├── techgear_web/
│   │   ├── settings.py           # Configuración del proyecto
│   │   ├── urls.py               # Rutas principales
│   │   └── wsgi.py               # Punto de entrada WSGI
│   └── store/
│       ├── views.py              # Vistas y consumo de FastAPI
│       ├── templates/store/      # Plantillas HTML del portal
│       └── migrations/           # Migraciones de Django
│
├── .gitignore
└── README.md
```

Los archivos `staticfiles/`, `.venv/`, `db.sqlite3`, archivos `.env` y otros datos generados o privados no deben versionarse.

---

## Despliegue

El despliegue se realiza como **dos proyectos independientes**. FastAPI permanece en Render y Django se publica en Vercel. No se importa el repositorio como un único proyecto multiservicio.

### 1. FastAPI en Render

Configuración utilizada para el servicio de API:

| Campo | Valor |
|---|---|
| Repositorio | `https://github.com/sebas17-code/Taller2-Api` |
| Directorio raíz | Raíz del repositorio (`.`) |
| Build Command | `pip install -r techgear_api/requirements.txt` |
| Start Command | `python -m uvicorn techgear_api.src.main:app --host 0.0.0.0 --port $PORT` |
| URL pública | `https://taller2-api-p8kq.onrender.com` |

Configura en **Render → servicio → Environment**:

| Variable | Uso |
|---|---|
| `MONGODB_URI` | URI privada de MongoDB Atlas. |
| `MONGODB_DATABASE` | `techgear`. |
| `JWT_SECRET_KEY` | Clave privada aleatoria de al menos 32 caracteres. |
| `JWT_ALGORITHM` | `HS256` (opcional; es el valor predeterminado). |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` (opcional; es el valor predeterminado). |

Después de guardar variables, Render debe completar un nuevo despliegue. Comprueba la API:

```powershell
Invoke-RestMethod `
    -Uri "https://taller2-api-p8kq.onrender.com/health" `
    -TimeoutSec 60 |
    ConvertTo-Json -Depth 5
```

La respuesta debe mostrar `status: ok` y `mongodb_conectado: true`.

### 2. Django en Vercel

Importa el repositorio de GitHub en Vercel como **un proyecto independiente** y configura:

| Campo | Valor |
|---|---|
| Nombre sugerido | `techgear-web` |
| Repositorio | `sebas17-code/Taller2-Api` |
| Root Directory | `techgear_web` |
| Framework Preset | Django, si la detección automática lo identifica. |
| Build Command | Automático / vacío. |
| Install Command | Automático / vacío. |
| Output Directory | Vacío. |

El archivo `techgear_web/.python-version` fija Python `3.14` para el despliegue. No configures `staticfiles` como Output Directory: Django utiliza `STATIC_ROOT` para recolectar los archivos estáticos.

En **Vercel → Project → Settings → Environment Variables**, agrega las variables siguientes para **Production** y **Preview**:

| Variable | Valor |
|---|---|
| `DJANGO_SECRET_KEY` | Clave privada de Django. No reutilices `JWT_SECRET_KEY`. |
| `FASTAPI_URL` | `https://taller2-api-p8kq.onrender.com` |

Guarda las variables y vuelve a desplegar para que se apliquen al nuevo deployment.

> **Validación de producción pendiente:** después de que Vercel asigne el dominio, comprueba que `ALLOWED_HOSTS` incluya el dominio, que `CSRF_TRUSTED_ORIGINS` permita el origen HTTPS de Vercel para los formularios POST y que las rutas de login, registro, pedidos y carga de imágenes funcionen. No habilites `DEBUG` en producción.

---

## Variables de entorno

Las variables locales y las variables de despliegue se configuran por separado:

| Variable | Aplicación | Local | Producción |
|---|---|---|---|
| `MONGODB_URI` | FastAPI | `techgear_api/.env` | Render Environment |
| `MONGODB_DATABASE` | FastAPI | `techgear_api/.env` | Render Environment |
| `JWT_SECRET_KEY` | FastAPI | `techgear_api/.env` | Render Environment |
| `JWT_ALGORITHM` | FastAPI | `techgear_api/.env` (opcional) | Render Environment (opcional) |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | FastAPI | `techgear_api/.env` (opcional) | Render Environment (opcional) |
| `DJANGO_SECRET_KEY` | Django | Variable de entorno de Windows | Vercel Environment |
| `FASTAPI_URL` | Django | `http://127.0.0.1:8000` | `https://taller2-api-p8kq.onrender.com` |

**Nunca subas valores reales de estas variables al repositorio.** Comparte nombres de variables, no sus valores.

---

## Solución de problemas

### FastAPI indica `mongodb_conectado: false`

1. Comprueba que `MONGODB_URI` esté configurada en el entorno donde se ejecuta FastAPI.
2. Verifica usuario, contraseña, nombre del clúster y permisos en Atlas.
3. Revisa **Network Access** en MongoDB Atlas.
4. Reinicia o vuelve a desplegar el servicio después de modificar las variables.

### FastAPI no inicia por `JWT_SECRET_KEY`

La variable debe llamarse exactamente `JWT_SECRET_KEY` y contener al menos 32 caracteres. No es la misma clave que `DJANGO_SECRET_KEY`.

### Error de carga de imágenes o `python-multipart`

Verifica que `python-multipart` esté en `techgear_api/requirements.txt` y vuelve a instalar las dependencias o desplegar la API. El endpoint de carga recibe archivos mediante multipart/form-data.

### Django no carga productos

1. Comprueba que FastAPI esté activo.
2. Verifica `FASTAPI_URL` en la terminal de Django o en Vercel.
3. En local, usa `http://127.0.0.1:8000`.
4. En producción, usa la URL HTTPS pública de Render, sin agregar `/productos` al final.
5. Revisa los registros del servicio correspondiente.

### Django muestra un error de clave secreta

Comprueba que exista `DJANGO_SECRET_KEY` en el entorno de ejecución. No sustituyas esta variable por `JWT_SECRET_KEY`.

### Error CSRF al enviar formularios en Vercel

Revisa que el dominio HTTPS de Vercel esté incluido en `CSRF_TRUSTED_ORIGINS` en `settings.py`. No desactives la protección CSRF para resolver el problema.

### Los archivos CSS o estáticos no aparecen

Comprueba `STATIC_URL`, `STATIC_ROOT`, el middleware WhiteNoise y que se ejecute `collectstatic`. No configures `staticfiles/` como Output Directory de Vercel.

### Comprobaciones útiles

```powershell
# Verificar la configuración de Django
python .\techgear_web\manage.py check

# Recolectar archivos estáticos de Django
python .\techgear_web\manage.py collectstatic --noinput

# Comprobar que los módulos Python compilan
python -m compileall .\techgear_api .\techgear_web

# Ver el estado de Git
git status
```

---

## Flujo de Git

Desde la raíz del repositorio:

```powershell
# Revisar los cambios
git status

# Revisar espacios y errores de formato
git diff --check

# Agregar los cambios
git add .

# Revisar exactamente qué se va a confirmar
git status

git diff --cached --check

# Crear un commit
git commit -m "feat: describe brevemente los cambios"

# Enviar la rama main a GitHub
git push origin main
```

Antes de `git add .`, verifica que `.gitignore` excluya por lo menos:

```gitignore
.venv/
**/__pycache__/
*.py[cod]
.env
**/.env
*.sqlite3
techgear_web/db.sqlite3
techgear_web/staticfiles/
.vercel/
```

No agregues al repositorio claves JWT, claves de Django, URI de MongoDB, bases de datos locales ni archivos de secretos.

---

## Seguridad

- Mantén `DEBUG=False` en producción.
- Usa una clave `DJANGO_SECRET_KEY` privada para Django y otra `JWT_SECRET_KEY` para FastAPI.
- No publiques archivos `.env` ni valores de variables de entorno.
- Protege las operaciones administrativas de productos con autenticación y autorización.
- Mantén la protección CSRF en los formularios Django.
- No incluyas credenciales ni datos personales en logs, capturas o commits.
- La URL de las imágenes puede ser pública para que el catálogo las muestre; la operación de carga debe permanecer protegida por autenticación administrativa.

---

## Estado de despliegue conocido

- **FastAPI en Render:** el endpoint `/health` ha respondido `status: ok` y `mongodb_conectado: true` después de configurar las variables de entorno.
- **Django en Vercel:** la configuración del proyecto y sus variables de entorno debe validarse con un deployment exitoso y pruebas funcionales sobre el dominio asignado.

