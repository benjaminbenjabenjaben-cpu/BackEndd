# Music Pro Courier — Evaluación 3

Sistema de transporte construido con Django, formularios HTML y MySQL local.
Las operaciones se realizan desde páginas propias: tipos de vehículo, vehículos,
conductores, viajes, usuarios y diez reportes mediante Django ORM.
El portal público permite al cliente consultar el estado de su pedido mediante
el código de seguimiento del viaje, sobre la misma base de datos.

## Iniciar en esta computadora

Desde la carpeta principal del proyecto:

```powershell
.\.tools\iniciar_mysql.ps1
.\venv\Scripts\python.exe bibliotecainacap\manage.py runserver 127.0.0.1:8000
```

Abre http://127.0.0.1:8000/ para el portal del cliente y
http://127.0.0.1:8000/ingresar/ para el acceso administrativo.
Las credenciales iniciales de esta computadora están
solo en `.tools/credenciales_e3.txt`, que no se publica en GitHub.
`Ctrl+C` detiene Django. El administrador propio requiere iniciar sesión.

## Modelos y relaciones

Los cuatro modelos de Transporte se definen en `core/models.py`, según el
esquema entregado en el Word:

- **TipoVehiculo:** nombre único y descripción.
- **Vehiculo:** tipo, patente única, marca, modelo, año, disponibilidad y estado.
- **Conductor:** RUT único, nombre, licencia, teléfono y estado activo.
- **Viaje:** código de seguimiento único, vehículo, conductor, origen, destino,
  salida, llegada, estado y observaciones.

Un tipo puede tener varios vehículos. Cada viaje pertenece a un vehículo y a un
conductor. `ForeignKey` representa esas relaciones; `PROTECT` impide eliminar
un registro que todavía es utilizado por otro. `__str__` define su nombre legible.

La base MySQL `music_pro_e3` contiene únicamente los cuatro modelos del caso,
además de las tablas internas de usuarios y sesiones de Django. Las tablas
`core_tipovehiculo`, `core_vehiculo`, `core_conductor` y `core_viaje` llevan el
prefijo `core_` porque ese es el nombre de la aplicación Django.

Se conserva el historial de migraciones ya aplicado. `0004_transporte` creó
estas entidades y `0005_solo_transporte` retiró las tablas heredadas de Envío e
Historial. El archivo SQLite anterior se conserva fuera de la conexión actual.

`0006_seguimiento_cliente` agrega un código de seguimiento distinto a cada
viaje existente. Los viajes nuevos reciben su código automáticamente.

## Portal del cliente y administración

El cliente entra a `/` o `/rastreo/` y escribe el código que le entrega la
empresa. Ve el estado actual, el recorrido y las fechas. El seguimiento es
público por código y no permite modificar datos ni muestra información personal
del conductor u observaciones internas.

El administrador inicia sesión en `/ingresar/` y gestiona los datos desde
`/panel/`. En **Viajes** puede ver el código y abrir su seguimiento público.
Al editar el estado del viaje, el cliente ve ese cambio al volver a consultar.
Ambas páginas leen el mismo registro de MySQL; no hay otra copia en JSON.

## Sesiones y permisos

`core/views.py` usa `authenticate`, `login` y `logout`. Django guarda la sesión
en la base de datos y la identifica mediante una cookie. El cierre se realiza
con POST. `@login_required` protege las vistas; tras cerrar sesión no se puede
acceder directamente a ellas por la URL.

Hay dos perfiles con grupos de Django:

| Perfil | Acceso |
|---|---|
| Administrador | Consulta y CRUD de tipos, vehículos, conductores y viajes; crea, edita y desactiva usuarios. |
| Operador | Consulta los listados y los diez reportes. |

`core/decoradores.py` comprueba el perfil Administrador en el servidor.
Ocultar botones no reemplaza esa comprobación. El superusuario tiene acceso
administrativo. No se permite desactivar la propia cuenta ni el superusuario.
Al crear usuarios se usa `set_password`, que guarda un hash de la contraseña.
Las cuentas actuales utilizan PBKDF2-SHA256: la base no guarda la contraseña
original. El archivo de conexión `mysql.cnf` y la clave interna `.secret_key`
son privados y están excluidos de Git; esos archivos locales son texto legible.
Al crear cuentas se aplican los validadores de contraseña de Django: longitud
mínima, similitud con datos del usuario, contraseñas comunes y solo numéricas.
La clave interna de Django se genera aleatoriamente una vez y se conserva.
Esta configuración está preparada para la evaluación local en HTTP, con
`DEBUG=True`; no corresponde a una publicación en Internet.

## Formularios y operaciones

Los formularios se escriben en HTML y se procesan con `request.POST` en las
vistas. No se utilizan `ModelForm` ni clases de formularios Django.
`full_clean()` comprueba campos, tipos y valores únicos antes de guardar.
Se valida también que la llegada no sea anterior a la salida.

- Crear y modificar: formulario POST con `{% csrf_token %}` y `save()` del ORM.
- Consultar: QuerySets del ORM y tablas HTML paginadas.
- Eliminar: página de confirmación y borrado únicamente con POST.
- Usuarios: alta, consulta, edición y desactivación desde el sistema propio.
- Mensajes: confirmación o error después de cada operación.

## Diez consultas ORM

El panel de inicio muestra tarjetas, gráficos de estados, viajes por tipo,
evolución diaria, conductores con más viajes y los últimos viajes. El selector
de 7, 30 o 90 días filtra los viajes por fecha de salida, incluyendo el día actual.
Los totales de vehículos y conductores corresponden a todos los registros.
Administrador y Operador comparten el diseño; las operaciones de gestión
conservan sus permisos. Los gráficos usan JavaScript y SVG locales.

Se implementaron las consultas 1 a 10 del apartado Transporte del Word.
Todas se muestran en `/reportes/` y respetan los permisos de sesión.

| N.º | Reporte | ORM principal |
|---|---|---|
| 1 | Todos los vehículos registrados | `Vehiculo.objects.all()` |
| 2 | Vehículos de un tipo seleccionado | `filter(tipo_vehiculo=tipo)` |
| 3 | Vehículos disponibles | `filter(disponible=True)` |
| 4 | Los diez vehículos más antiguos | `order_by("anio", "id")[:10]` |
| 5 | Cantidad de conductores | `Conductor.objects.count()` |
| 6 | Viajes de un vehículo | `filter(vehiculo=vehiculo)` |
| 7 | Viajes de un conductor | `filter(conductor=conductor)` |
| 8 | Cantidad de viajes por estado | `values("estado").annotate(total=Count("id"))` |
| 9 | Viajes programados entre dos fechas | `filter(estado="programado", fecha_salida__gte=inicio, fecha_salida__lt=fin)` |
| 10 | Vehículos sin viajes | `filter(viajes__isnull=True)` |

El reporte 9 incluye el día inicial y el final del rango. Se filtra con fechas
con zona horaria, sin necesitar tablas adicionales de zonas horarias en MySQL.

## Consultas externas en SQL

`consultas_transporte.sql` contiene las mismas diez consultas en SQL de MySQL,
para ejecutarlas desde una herramienta externa conectada a `music_pro_e3`.
Las consultas SQL no se ejecutan desde las vistas: la página Reportes continúa
utilizando exclusivamente el ORM de Django.

[Pasos para ejecutar las consultas externas](GUIA_SQL_EXTERNO.md).

## Instalar en otro computador

Se necesita Python 3.12 o superior y MySQL local.
[Descarga oficial de MySQL](https://dev.mysql.com/downloads/mysql/8.4.html?os=3).

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

En MySQL crea la base `music_pro_e3` con `utf8mb4` y un usuario con permisos sobre
esa base. Copia `bibliotecainacap/mysql.cnf.example` como
`bibliotecainacap/mysql.cnf` y completa los datos de conexión locales.
Ese archivo contiene la contraseña y está ignorado por Git.

```powershell
cd .\bibliotecainacap
python -c "from pathlib import Path; from secrets import token_urlsafe; Path('.secret_key').write_text(token_urlsafe(64), encoding='utf-8')"
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

El superusuario puede iniciar sesión y crear las cuentas Administrador/Operador
desde la sección Usuarios. Los grupos se crean al asignar el perfil.
Genera `.secret_key` únicamente en la instalación inicial: reemplazarla invalida
las sesiones anteriores y exige iniciar sesión nuevamente.

## Comandos de comprobación

Desde la carpeta que contiene `manage.py`:

```powershell
python manage.py check
python manage.py showmigrations core
python manage.py makemigrations --check --dry-run
python manage.py test core
```

Las pruebas usan una base MySQL independiente llamada `test_music_pro_e3`.
El usuario de conexión necesita permiso para crear y borrar esa base de pruebas.
Se comprueban sesiones, permisos, CSRF, CRUD, usuarios y los diez reportes.
Las pruebas incluyen el sistema administrativo y su conexión con el seguimiento
público del cliente.

[Revisión final de la pauta y demostración para la evaluación](REVISION_E3.md).

## Archivos para explicar

| Archivo | Función |
|---|---|
| `bibliotecainacap/settings.py` | Configuración de MySQL, sesiones y autenticación. |
| `core/models.py` | Entidades y relaciones. |
| `core/migrations/` | Historial de los cambios de estructura. |
| `core/views.py` | Login/logout, CRUD, validaciones y consultas ORM. |
| `core/decoradores.py` | Comprobación del perfil Administrador. |
| `core/urls.py` | Rutas del sistema propio. |
| `core/templates/core/` | Formularios y páginas HTML. |
| `core/templates/core/panel_transporte.html` | Panel visual compartido por Administrador y Operador. |
| `core/static/core/panel.js` | Dibuja los gráficos SVG a partir de los datos que entrega la vista. |
| `core/tests_e3.py` | Comprobación funcional de E3. |
