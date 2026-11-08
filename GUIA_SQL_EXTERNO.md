# Consultas externas de Transporte

`consultas_transporte.sql` contiene las consultas 1 a 10 del caso Transporte.
Se ejecutan fuera de Python, sobre la misma base MySQL que usa Django.
Los reportes de la página siguen utilizando exclusivamente el ORM.

## Conexión ya preparada en este equipo

El usuario confirmó en SQL Developer la conexión **musicpro**, de tipo MySQL,
y una hoja de trabajo asociada. Utiliza esa conexión existente.

| Dato | Valor |
|---|---|
| Nombre en SQL Developer | `musicpro` |
| Motor | MySQL |
| Servidor | `127.0.0.1` |
| Puerto | `3306` |
| Base de datos | `music_pro_e3` |
| Usuario | `musicpro` |
| Contraseña | Archivo local `bibliotecainacap/mysql.cnf`. |

La contraseña de MySQL es diferente de la contraseña para ingresar a la web.
No se publica en GitHub.

## Ejecutar una consulta en SQL Developer

1. Si MySQL está detenido, inicia `.\.tools\iniciar_mysql.ps1`.
2. En SQL Developer pulsa **Ctrl+O** o **Archivo → Abrir** y selecciona
   `consultas_transporte.sql` dentro de la carpeta del proyecto.
3. En el selector de conexión de esa hoja, elige **musicpro**.
4. Selecciona únicamente `USE music_pro_e3;` y pulsa **Ctrl+Enter**.
5. Ejecuta cada instrucción `SET` del encabezado **por separado y en orden**:
   selecciona una sola instrucción completa, hasta su punto y coma, y pulsa
   **Ctrl+Enter**. No selecciones varias instrucciones `SET` juntas.
6. Selecciona el `SELECT` completo de la **CONSULTA 1**, hasta su punto y coma,
   y pulsa **Ctrl+Enter**. Revisa su cuadrícula de resultados.
7. Repite el paso anterior para las consultas 2 a 10.

Mantén la misma hoja y la misma conexión durante estos pasos: las variables
`@tipo_id`, `@vehiculo_id` y las demás pertenecen a esa sesión SQL.

Los parámetros iniciales usan el menor id existente de cada tabla. Puedes
cambiar `@tipo_id`, `@vehiculo_id` o `@conductor_id` por otro identificador.
Si modificas un parámetro, ejecuta de nuevo su instrucción `SET` antes del reporte.

## Fechas y comprobación

El rango inicial va desde hoy hasta dentro de 30 días, incluidos ambos días.
Django guarda las fechas en UTC; el archivo convierte los límites y la salida.
`@desfase_local` usa `-03:00`; utiliza `-04:00` cuando corresponda al período.
Si cambias las fechas, vuelve a ejecutar también `@desde_utc` y `@hasta_utc`.
Si el rango cruza un cambio de horario, aplica a cada límite su desfase correcto.

La consulta 8 muestra los cuatro estados, incluidos los que tienen cero viajes.
Cero filas en otra consulta significa que no existen coincidencias.
Las tablas `core_*` son los nombres asignados por Django.

Para comprobar persistencia, crea o modifica un vehículo o viaje desde la web
y vuelve a ejecutar su `SELECT`. También puedes comparar con `/reportes/`
utilizando los mismos filtros.

Las diez consultas ya se ejecutaron correctamente mediante JDBC y el Java
incluido con SQL Developer. La conexión gráfica está confirmada por el usuario;
la ejecución de los `SELECT` en la hoja gráfica aún debe comprobarse.
El archivo solo consulta datos y configura variables de sesión; no modifica registros.

## Si reinstalas SQL Developer

La instalación actual es **Oracle SQL Developer 26.2** y el controlador descargado
es **MySQL Connector/J 8.4.0**, ubicado en `.tools/jdbc/mysql-connector-j-8.4.0.jar`.

En **Herramientas → Preferencias → Base de datos → Controladores JDBC de terceros**
(**Tools → Preferences → Database → Third Party JDBC Drivers**) pulsa
**Agregar entrada / Add Entry** y selecciona ese `.jar`.
Después crea una conexión **MySQL** llamada **musicpro** con los valores anteriores,
pulsa **Probar / Test** y **Conectar / Connect**. Reinicia SQL Developer si la opción
MySQL todavía no aparece después de añadir el controlador.
[Referencia oficial de conexiones MySQL en SQL Developer](https://docs.oracle.com/en/database/oracle/sql-developer/26.2/rptug/sql-developer-dialogs.html).
