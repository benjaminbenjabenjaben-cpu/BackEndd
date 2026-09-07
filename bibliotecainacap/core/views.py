"""Vistas U1: reciben una petición y entregan HTML con datos de ejemplo."""
from math import isfinite

from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .services import ESTADOS, cargar_envios, filtrar_envios, preparar_envio


def inicio(request):
    # El acceso es visual: no consulta cuentas ni comprueba credenciales.
    if request.method == "POST":
        return redirect("core:panel")
    return render(request, "core/iniciar_sesion.html", {"pagina": "inicio"})


def registro(request):
    return render(request, "core/registro_usuario.html", {
        "pagina": "registro", "enviado": request.method == "POST",
    })


@require_POST
def salir(request):
    return redirect("core:inicio")


def panel(request):
    todos = cargar_envios()
    query = request.GET.get("q", "").strip()[:100]
    estado = request.GET.get("estado", "")
    filtrados = filtrar_envios(todos, query, estado)
    resumen = [
        {"codigo": codigo, "nombre": nombre,
         "cantidad": sum(e["estado"] == codigo for e in todos)}
        for codigo, nombre in ESTADOS
    ]
    return render(request, "core/panel_envios.html", {
        "pagina": "panel", "mostrar_menu": True,
        "envios": Paginator(filtrados, 6).get_page(request.GET.get("pagina")),
        "resumen": resumen, "total": len(todos), "coincidencias": len(filtrados),
        "q": query, "estado": estado, "estados": ESTADOS,
        "peso_total": sum(float(e["peso"]) for e in todos),
    })


def rastreo(request):
    codigo = request.GET.get("codigo", "").strip().upper()[:40]
    error = ""
    if "codigo" in request.GET:
        if any(e["codigo"] == codigo for e in cargar_envios()):
            return redirect("core:detalle_envio", codigo=codigo)
        error = "No encontramos ese envío. Prueba con MP-2026-001."
    return render(request, "core/buscar_envio.html", {
        "codigo": codigo, "error": error, "pagina": "rastreo",
    })


def mostrar_detalle(request, envio, vista_previa=False):
    """Prepara las cuatro etapas para la plantilla de seguimiento."""
    pasos = [
        {"nombre": nombre, "completo": i <= envio["paso"]}
        for i, (_, nombre) in enumerate(ESTADOS)
    ]
    return render(request, "core/detalle_envio.html", {
        "envio": envio, "pasos": pasos, "pagina": "rastreo",
        "mostrar_menu": True, "vista_previa": vista_previa,
    })


def detalle_envio(request, codigo):
    envio = next((e for e in cargar_envios() if e["codigo"] == codigo.upper()), None)
    if envio is None:
        return render(request, "core/error.html", {
            "titulo": "Envío no encontrado",
            "detalle": "Revisa el código de seguimiento o vuelve a buscar.",
        }, status=404)
    return mostrar_detalle(request, envio)


def nuevo_envio(request):
    # Los campos provienen de inputs HTML, sin clases de Django Forms.
    datos = request.POST if request.method == "POST" else {}
    error = ""
    if request.method == "POST":
        campos = ("cliente", "destinatario", "origen", "destino", "equipo", "prioridad")
        envio = {campo: datos.get(campo, "").strip()[:150] for campo in campos}
        try:
            envio["bultos"] = int(datos.get("bultos", ""))
            envio["peso"] = float(datos.get("peso", "").replace(",", "."))
            numeros_correctos = (1 <= envio["bultos"] <= 100
                and isfinite(envio["peso"]) and 0.1 <= envio["peso"] <= 3000)
        except ValueError:
            numeros_correctos = False
        if not all(envio.get(campo) for campo in campos) or not numeros_correctos:
            error = "Completa los campos. Usa entre 1 y 100 bultos y entre 0,1 y 3000 kg."
        elif envio["prioridad"] not in ("normal", "alta"):
            error = "Selecciona una prioridad válida."
        else:
            envio.update(
                codigo="MP-DEMO-PREVIA", estado="bodega", eta="Por programar",
                conductor="Por asignar", patente="Sin asignar",
                historial=[{"estado": "bodega", "titulo": "Ingreso a bodega",
                            "nota": "Vista previa de un despacho. No guardado.",
                            "fecha": timezone.now().isoformat()}],
            )
            return mostrar_detalle(request, preparar_envio(envio), vista_previa=True)
    return render(request, "core/nuevo_envio.html", {
        "datos": datos, "error": error, "pagina": "nuevo", "mostrar_menu": True,
    })


def actualizar_estado(request, codigo):
    envio = next((e for e in cargar_envios() if e["codigo"] == codigo.upper()), None)
    if envio is None:
        return detalle_envio(request, codigo)
    siguiente = ESTADOS[envio["paso"] + 1:envio["paso"] + 2]
    if not siguiente:
        return redirect("core:detalle_envio", codigo=envio["codigo"])
    error = ""
    nota = request.POST.get("nota", "").strip()[:180]
    if request.method == "POST":
        estado = request.POST.get("estado", "")
        if estado != siguiente[0][0] or not nota:
            error = "Selecciona la siguiente etapa y escribe una observación."
        else:
            envio["estado"] = estado
            envio["historial"].append({
                "estado": estado, "titulo": dict(ESTADOS)[estado], "nota": nota,
                "fecha": timezone.now().isoformat(),
            })
            if estado == "recibido":
                envio["eta"] = "Entregado"
            return mostrar_detalle(request, preparar_envio(envio), vista_previa=True)
    return render(request, "core/actualizar_estado.html", {
        "envio": envio, "siguiente": siguiente, "error": error, "nota": nota,
        "pagina": "panel", "mostrar_menu": True,
    })


def exportar_envios(request):
    envios = filtrar_envios(cargar_envios(), request.GET.get("q", "").strip()[:100],
                           request.GET.get("estado", ""))
    respuesta = JsonResponse(
        {"modo": "demostracion", "total": len(envios), "envios": envios},
        json_dumps_params={"ensure_ascii": False, "indent": 2},
    )
    respuesta["Content-Disposition"] = 'attachment; filename="envios_music_pro.json"'
    return respuesta


def ayuda(request):
    return render(request, "core/ayuda.html", {"pagina": "ayuda"})
