# Music Pro Courier · Prototipo U1

Portal académico de Transporte y Despachos, construido con Django, HTML semántico, Bootstrap y CSS propio. Conserva el diseño del portal y presenta ocho envíos ficticios leídos desde un archivo JSON.

La versión actual se ajusta a la corrección solicitada para la presentación: **sin modelos, Django Forms, base de datos, autenticación, sesiones ni plantillas heredadas o parciales**. Cada página contiene su documento HTML completo.

## Iniciar en este computador

Abre la terminal de Visual Studio Code en la carpeta del proyecto y ejecuta:

```powershell
.\venv\Scripts\python.exe bibliotecainacap\manage.py runserver 127.0.0.1:8000 --noreload
```

Abre **http://127.0.0.1:8000/**. Mantén abierta la terminal; `Ctrl+C` detiene el servidor. No hace falta activar el entorno porque el comando usa directamente su Python. Si modificas Python, detén y vuelve a iniciar el servidor.

Para instalar en otro equipo con Python 3.12 o superior:

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe bibliotecainacap\manage.py runserver
```

No se necesita ejecutar migraciones ni crear un superusuario. Las plantillas se abren a través del servidor Django.

## Recorrido para la evaluación

1. Abre el inicio y presiona **Ingresar al portal**. Puedes dejar los campos vacíos: son visuales y no se validan credenciales.
2. En el panel muestra los cuatro contadores, la tabla, los filtros y la segunda página de resultados.
3. Busca `MP-2026-001` y explica sus etapas e historial. `MP-2026-004` es un ejemplo recibido.
4. Usa **Nuevo envío**, completa datos ficticios y muestra su vista previa.
5. Abre un envío en curso y usa **Actualizar estado** para ver cómo quedaría la siguiente etapa.
6. Vuelve al panel: los ocho ejemplos originales permanecen iguales. Ninguna de las dos acciones guarda cambios.
7. Exporta los resultados filtrados en JSON.

El registro también es visual: envía un formulario y muestra una confirmación, pero no crea cuentas. Las fechas, personas y direcciones son ficticias; no hay GPS ni integración con entregas reales.



**Framework CSS de esta versión:** Bootstrap local, junto a `portal.css`. La versión actual no carga Tailwind. Se conserva este diseño en la corrección.

## Archivos principales

```text
bibliotecainacap/
  manage.py
  bibliotecainacap/
    settings.py
    urls.py
  core/
    urls.py
    views.py
    services.py
    tests.py
    data/envios.json
    templates/core/
      iniciar_sesion.html
      registro_usuario.html
      panel_envios.html
      buscar_envio.html
      detalle_envio.html
      nuevo_envio.html
      actualizar_estado.html
      ayuda.html
      error.html
    static/core/
      portal.css
      portal.js
      concierto.jpg
      favicon.svg
      vendor/
```

## Verificación y avances

```powershell
.\venv\Scripts\python.exe bibliotecainacap\manage.py check
.\venv\Scripts\python.exe bibliotecainacap\manage.py test core
```


