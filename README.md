# Music Pro Courier — Evaluación 3

Sistema de transporte construido con Django, formularios HTML y MySQL local.
Las operaciones se realizan desde páginas propias: tipos de vehículo, vehículos,
conductores, viajes, usuarios y diez reportes mediante Django ORM.

## Iniciar en esta computadora

Desde la carpeta principal del proyecto:

```powershell
.\.tools\iniciar_mysql.ps1
.\venv\Scripts\python.exe bibliotecainacap\manage.py runserver 127.0.0.1:8000
```

Abre http://127.0.0.1:8000/. Las credenciales iniciales de esta computadora están
solo en `.tools/credenciales_e3.txt`, que no se publica en GitHub.
`Ctrl+C` detiene Django. El administrador propio requiere iniciar sesión.

## Modelos y relaciones

Los cuatro modelos de Transporte se definen en `core/models.py`, según el
esquema entregado en el Word:

- **TipoVehiculo:** nombre único y descripción.
- **Vehiculo:** tipo, patente única, marca, modelo, año, disponibilidad y estado.
- **Conductor:** RUT único, nombre, licencia, teléfono y estado activo.
- **Viaje:** vehículo, conductor, origen, destino, salida, llegada, estado y observaciones.

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
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

El superusuario puede iniciar sesión y crear las cuentas Administrador/Operador
desde la sección Usuarios. Los grupos se crean al asignar el perfil.

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
Las 19 pruebas corresponden al sistema de Transporte de esta evaluación.

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
| `core/tests_e3.py` | Comprobación funcional de E3. |
