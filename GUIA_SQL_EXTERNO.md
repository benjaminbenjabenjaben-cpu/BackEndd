# Consultas externas de Transporte

El archivo `consultas_transporte.sql` contiene las consultas 1 a 10 del caso
Transporte. Se ejecuta fuera del código Python, sobre la misma base MySQL que
usa Django. Las páginas de reportes continúan utilizando exclusivamente el ORM.

## Conexión local

| Dato | Valor |
|---|---|
| Motor | MySQL |
| Servidor | `127.0.0.1` |
| Puerto | `3306` |
| Base de datos | `music_pro_e3` |
| Usuario | `musicpro` |
| Contraseña | Consultar el archivo local `bibliotecainacap/mysql.cnf`. |

La contraseña no está incluida en el repositorio. La conexión debe ser MySQL;
no debe crearse una conexión Oracle para esta base.

## Preparar Oracle SQL Developer de este escritorio

La instalación encontrada es **Oracle SQL Developer 26.2**. Oracle documenta las
conexiones MySQL mediante un controlador JDBC externo:
[guía oficial de conexiones MySQL](https://docs.oracle.com/en/database/oracle/sql-developer/26.2/rptug/sql-developer-dialogs.html).

El controlador **MySQL Connector/J 8.4.0** ya está descargado en esta computadora:

```text
C:\Users\Administrator\Desktop\TRABAJO PROGRAMACION BACK END\.tools\jdbc\mysql-connector-j-8.4.0.jar
```

1. En SQL Developer abre **Herramientas → Preferencias → Base de datos →
   Controladores JDBC de terceros**. En inglés: **Tools → Preferences → Database →
   Third Party JDBC Drivers**.
2. Selecciona **Agregar entrada / Add Entry**, elige ese archivo `.jar` y acepta.
3. Crea una conexión llamada **Transporte MySQL**, seleccionando **MySQL** como
   motor. Si esa opción aún no aparece, reinicia SQL Developer después de añadir
   el controlador.
4. Completa los valores de la tabla anterior. Usa la contraseña de MySQL del
   archivo `mysql.cnf`, que es diferente de la contraseña de la página web.
5. Selecciona la base **music_pro_e3**, pulsa **Probar / Test** y, cuando indique
   conexión correcta, pulsa **Conectar / Connect**.
6. Abre una **Hoja SQL / SQL Worksheet** de esa conexión y carga el archivo
   `consultas_transporte.sql` mediante **Archivo → Abrir**. Comprueba que la
   conexión seleccionada en la hoja sea **Transporte MySQL**.

Se verificó una conexión real a MySQL 8.4.13 y se ejecutaron correctamente las
diez consultas usando ese controlador y el Java incluido con SQL Developer.
La conexión guardada y la ejecución dentro de la interfaz gráfica todavía
requieren comprobarse manualmente: el control de ventanas no estuvo disponible.
No se creó una conexión Oracle ni se cambió el motor del proyecto.

## Ejecutar las consultas

1. Inicia MySQL si está detenido: `.\.tools\iniciar_mysql.ps1`.
2. Abre una hoja SQL conectada a MySQL y carga `consultas_transporte.sql`.
3. Si tu instalación de SQL Developer permite esa conexión, utiliza su hoja SQL.
   El soporte depende del controlador y de la versión instalada.
4. Ejecuta primero `USE` y las líneas `SET` del encabezado en esa misma hoja.
5. Selecciona un `SELECT` completo, hasta su punto y coma, y ejecútalo.
   En una hoja compatible de SQL Developer se utiliza **Ctrl+Enter**.
6. Repite con las diez consultas y revisa la cuadrícula de resultados.

Los parámetros iniciales toman el menor identificador existente de cada tabla.
Puedes sustituir `@tipo_id`, `@vehiculo_id` o `@conductor_id` por otro id visible.
Los filtros de fechas van desde hoy hasta dentro de 30 días, incluyendo ambos
días. Puedes cambiar `@desde` y `@hasta`, y volver a ejecutar sus cálculos UTC.

## Fechas y resultados

Django guarda las fechas de los viajes en UTC. El archivo convierte los límites
de los días locales a UTC y muestra la salida con el desfase seleccionado.
`@desfase_local` usa `-03:00` como ejemplo; cámbialo a `-04:00` si corresponde al
período consultado. Estas conversiones con desfases fijos no necesitan cargar
tablas de zonas horarias en MySQL. Si el rango cruza un cambio de horario,
utiliza en cada límite el desfase que le corresponda.

La consulta 8 muestra los cuatro estados, incluso si alguno tiene cero viajes.
Las consultas sin coincidencias pueden devolver cero filas; eso no es un error.
Las tablas `core_*` son los nombres que Django asigna a los modelos de la app.

## Comprobar la persistencia

Crea o modifica un vehículo o viaje desde la web y vuelve a ejecutar el `SELECT`
correspondiente. El resultado debe reflejar el cambio. También puedes comparar
con el mismo reporte de `/reportes/`, usando los mismos filtros.

Este archivo solo consulta registros y configura variables de la sesión SQL;
no crea, modifica ni elimina datos del sistema.
