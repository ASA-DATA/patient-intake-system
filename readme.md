# Backend: instalación y dependencias

Usar CPython 3.13 (el entorno de referencia es 3.13.7). `requirements.txt`
contiene versiones exactas de dependencias directas y transitivas para Windows
y Linux. Se conservaron las versiones del entorno existente, sin actualizar
en bloque ni incluir `psycopg`/`psycopg-binary`: la aplicación y Alembic usan
`asyncpg`. `tzdata` permite usar `zoneinfo` en Windows; `colorama` es una
dependencia de Click en Windows. Para Linux se fijó la dependencia de Uvicorn
[`uvloop==0.22.1`](https://pypi.org/project/uvloop/0.22.1/), que ofrece ruedas
para CPython 3.13. Los marcadores seleccionan los paquetes de cada plataforma.

## Instalación

Desde la carpeta del backend, crear un entorno nuevo sin paquetes globales.
En PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install pip==25.2
python -m pip install -r requirements.txt
python -m pip check
```

En Linux:

```sh
python3.13 -m venv .venv
. .venv/bin/activate
python -m pip install pip==25.2
python -m pip install -r requirements.txt
python -m pip check
```

Si `.venv` ya existe, usar otro directorio para verificar una instalación
limpia; no recrear ni congelar ciegamente el entorno de trabajo.
Configurar una base de datos de desarrollo mediante `DATABASE_URL`
(`postgresql+asyncpg://...`) y arrancar con:

```sh
python -m uvicorn app.main:app --reload
```

El Dockerfile instala el mismo archivo con pip 25.2 y ejecuta `pip check`.
El flujo existente `deploy-backend.yml` ya construye ese Dockerfile, por lo
que no necesita otro paso de instalación. `test-dependencies.yml` verifica
instalación, conflictos y pruebas en Python 3.13 sobre Linux y Windows, sin
credenciales de servicios. No se requieren pytest ni herramientas de bloqueo
adicionales. La imagen base sigue siendo `python:3.13-slim`: este archivo fija
paquetes Python, no el contenido del sistema operativo ni el digest de Docker.

## Pruebas sin servicios externos

En un checkout limpio, sin `.env` ni variables con credenciales de Google o
Twilio, activar el entorno anterior y usar una URL ficticia. En PowerShell:

```powershell
$env:DATABASE_URL = 'postgresql+asyncpg://test:test@127.0.0.1:1/test'
$env:APP_ENV = 'test'
python -m unittest discover -s tests -v
```

En Linux:

```sh
DATABASE_URL=postgresql+asyncpg://test:test@127.0.0.1:1/test APP_ENV=test \
  python -m unittest discover -s tests -v
```

La suite de `tests/` usa dobles de base de datos, calendario y notificaciones.
No ejecutar los ejemplos `scripts/test_*.py` como pruebas unitarias: algunos
contactan servicios reales. Si el checkout tiene `.env`, ejecutar desde un
directorio temporal vacío, con `PYTHONPATH` apuntando al backend y `-s`
apuntando a la ruta absoluta de `tests/`, para no cargar ese archivo.

## Actualizaciones controladas

1. Crear una rama y un entorno vacío de Python 3.13; instalar el archivo actual
   y ejecutar las comprobaciones anteriores como referencia.
2. Elegir una versión concreta del paquete a cambiar tras revisar sus notas
   de publicación y requisitos. Editar solo su `==` en `requirements.txt`.
3. Resolver de nuevo con `python -m pip install -r requirements.txt`. Si hay un
   conflicto, ajustar únicamente las transitivas necesarias a versiones
   concretas compatibles; no usar una actualización global ni eliminar todos
   los pins. Revisar `python -m pip inspect` y `python -m pip freeze` del entorno
   aislado para añadir cualquier nueva transitiva con `==` y retirar las que
   dejen de ser necesarias. No reemplazar el archivo por un freeze de Windows:
   se perderían los marcadores y la dependencia `uvloop` de Linux.
4. Repetir la instalación en entornos vacíos de Windows y Linux, ejecutar
   `python -m pip check`, la suite y `docker build -t patient-intake-backend:deps .`.
   Revisar que todos los paquetes resueltos estén fijados, incluidos los extras
   de Uvicorn. Conservar solo los cambios de versiones justificados.

Si cambia la versión de pip, actualizar también Dockerfile, CI y estos pasos.
Al cambiar de versión menor de Python, volver a resolver y verificar ambas
plataformas; este conjunto se mantiene para Python 3.13.

## Rangos de fechas

`/api/appointments/by-date` y el endpoint heredado `/api/records/by-date`
interpretan las fechas como días de `CLINIC_TIMEZONE`. Las consultas de
columnas con zona horaria reciben límites con zona: desde la medianoche
inicial (incluida) hasta la medianoche posterior al día final (excluida).
Esto evita depender de la zona del servidor e incluye días de 23 o 25 horas
cuando cambia el horario estacional. Se conserva el margen heredado de diez
días para pacientes y valoraciones. `/api/records` filtra `assessment_date`,
que es una fecha sin hora, y conserva sus límites de fecha inclusivos.
