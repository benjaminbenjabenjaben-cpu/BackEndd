# Revisión de la Evaluación 3 — Transporte

Esta revisión corresponde al sistema de Transporte y a las diez consultas
seleccionadas del banco entregado por el profesor.

Resultado de la revisión: **33 pruebas aprobadas sobre MySQL**, comprobación
general sin errores, seis migraciones de `core` aplicadas y ningún cambio de
modelo pendiente. Las cuentas actuales Administrador y Operador utilizan
`pbkdf2_sha256`; MySQL autentica sus cuentas locales con `caching_sha2_password`.
Las credenciales actuales de conexión y acceso no aparecen en los archivos
rastreados ni en los 150 blobs de texto revisados del historial Git.

Los criterios 2.1.1, 2.1.3 y 2.1.4 se cubren respectivamente con la conexión
MySQL, las operaciones CRUD y la aplicación con ORM, sesiones y permisos.

## Correspondencia con la pauta

| Requisito | Archivos principales | Evidencia de comprobación |
|---|---|---|
| Conexión local a MySQL | `bibliotecainacap/bibliotecainacap/settings.py` | Motor MySQL, base `music_pro_e3`, comprobación de conexión y migraciones. |
| Administrador propio, sin Django Admin | `core/urls.py`, `core/views.py`, plantillas | Rutas y páginas propias; sin ruta `/admin/` ni registro de modelos en Admin. |
| Modelo del caso | `core/models.py`, `core/migrations/` | TipoVehiculo, Vehiculo, Conductor y Viaje con atributos, claves y relaciones. |
| CRUD de las cuatro entidades | `core/views.py`, plantillas de formularios y listados | `tests_e3.py` comprueba creación, consulta, modificación, eliminación y relaciones protegidas. |
| Mantención de usuarios | `usuario_guardar`, `usuarios`, `usuario_desactivar` | Alta, consulta, edición y desactivación; contraseñas guardadas mediante `set_password`. |
| Login, logout y sesiones | `inicio`, `salir`, configuración de middleware | Pruebas de credenciales, identificación de sesión y pérdida de acceso tras cerrar sesión. |
| Decoradores y permisos | `core/decoradores.py`, vistas administrativas | `login_required` y decorador reutilizable; pruebas de acceso directo anónimo y de Operador. |
| Formularios HTML propios | Plantillas y `request.POST` en vistas | Sin `ModelForm`, `ProductoForm` ni clases de formularios Django. |
| Validación, CSRF y mensajes | `guardar`, validaciones de vistas, formularios | Campos, tipos, unicidad, fechas, tokens CSRF y mensajes de resultado. |
| Cambios exclusivamente mediante POST | Vistas y formularios de gestión | GET muestra formularios o confirmaciones; POST guarda, elimina, desactiva o cierra sesión. |
| Consultas exclusivamente ORM en la aplicación | `reportes`, `panel` | QuerySets y agregaciones; sin SQL directo en las vistas. |
| Interfaz y persistencia | Plantillas, `tests_e3.py`, `tests_panel.py`, `tests_portal.py` | Pruebas sobre MySQL, revisión visual de perfiles y seguimiento público del mismo viaje. |

Las rutas indicadas como `core/...` se encuentran dentro de `bibliotecainacap/`.

## Diez reportes entregados

Todos están disponibles en `/reportes/`, requieren sesión y utilizan Django ORM.

| N.º | Pregunta que responde | Operación principal |
|---|---|---|
| 1 | Todos los vehículos registrados | `Vehiculo.objects.all()` |
| 2 | Vehículos de un tipo seleccionado | `filter(tipo_vehiculo=tipo)` |
| 3 | Vehículos disponibles | `filter(disponible=True)` |
| 4 | Diez vehículos más antiguos | `order_by("anio", "id")[:10]` |
| 5 | Cantidad de conductores registrados | `Conductor.objects.count()` |
| 6 | Viajes de un vehículo seleccionado | `filter(vehiculo=vehiculo)` |
| 7 | Viajes asignados a un conductor | `filter(conductor=conductor)` |
| 8 | Cantidad de viajes por estado | `values("estado").annotate(total=Count("id"))` |
| 9 | Viajes programados entre fechas | Filtro por estado y límites de fecha, incluyendo ambos días. |
| 10 | Vehículos sin viajes registrados | `filter(viajes__isnull=True)` |

El documento ofrece veinte consultas, pero la evaluación exige diez. Se eligieron
las primeras diez con autorización del estudiante; los reportes 11–20 no forman
parte de la entrega seleccionable. Las estadísticas del panel son un resumen
visual y no sustituyen las diez consultas de la página de reportes.

`consultas_transporte.sql` contiene los equivalentes para demostrar consultas
externas en SQL Developer. Esas instrucciones no se ejecutan desde las vistas.

## Alcance y modelo

La actividad genérica de Producto y Django Admin es material de práctica. El
encargo principal exige Transporte y administrador propio; por eso se aplican
los ejercicios CRUD al caso asignado y no se incorpora Producto ni Django Admin.

Las relaciones son TipoVehiculo → Vehiculo → Viaje ← Conductor. Se conserva el
historial de migraciones. El campo adicional `Viaje.codigo_seguimiento` conecta
el portal del cliente con el viaje administrado y fue autorizado al recuperar
ese portal; no agrega otra entidad. El cliente consulta por código y no modifica
registros ni accede a los datos internos del conductor.

## Contraseñas y configuración privada

Las contraseñas de usuarios Django se almacenan como **hash PBKDF2**, con sal,
mediante `set_password`; no se guardan como texto ni se descifran para iniciar
sesión. Un hash no es cifrado reversible.
Las cuentas nuevas se validan con las comprobaciones estándar de Django:
longitud mínima, similitud con el usuario, contraseñas comunes y solo numéricas.

La configuración de conexión MySQL y las notas locales de credenciales son
archivos privados en texto claro, ignorados por Git. No deben publicarse ni
incluirse en la entrega. No se afirma que todas las credenciales estén cifradas.

La clave de Django se genera en `bibliotecainacap/.secret_key`, también ignorado
por Git. Al cambiar la clave, las sesiones anteriores requieren iniciar sesión
otra vez. No se incluye su valor en documentación ni en el repositorio.

La demostración utiliza HTTP local y Django con DEBUG en este computador. Los
avisos de HTTPS de `check --deploy` corresponden a una publicación en producción;
no se activan redirecciones HTTPS sobre el servidor local de la demostración.
La revisión verifica los requisitos y las pruebas; no constituye una garantía de
seguridad absoluta para publicar el sistema en Internet.

## Demostración breve ante el profesor

1. Sin sesión, abrir `/panel/`, `/usuarios/` y `/reportes/`: deben dirigir al acceso.
2. Ingresar con credenciales correctas: el panel identifica usuario y perfil.
3. Abrir una vista de gestión: explicar su `login_required` y el decorador de Administrador.
4. Ingresar como Operador: consultar datos e intentar una URL de escritura; debe responder 403.
5. Cerrar sesión con el botón: el formulario utiliza POST y token CSRF.
6. Volver a una URL protegida después de salir: debe pedir acceso nuevamente; Django ya no identifica una sesión autenticada.

Para demostrar CRUD, crear un registro de prueba desde el panel, consultarlo,
modificarlo y eliminarlo desde su confirmación. Comprobar los cambios en MySQL.
Mostrar también el alta, edición y desactivación de un usuario de prueba y los
diez reportes con sus filtros.

Desde la carpeta `bibliotecainacap`, comprobar con `python manage.py check`,
`python manage.py showmigrations core`, `python manage.py makemigrations --check --dry-run`
y `python manage.py test core`.
