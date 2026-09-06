"""Vistas del prototipo U1: formularios, contextos y datos JSON sin ORM."""
import hashlib
import secrets
from functools import wraps

from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.core.paginator import Paginator
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import AccesoForm, RegistroForm, RastreoForm, EnvioForm, EstadoForm, ESTADOS
from .services import cargar_envios, envios_visibles, filtrar_envios

CUENTAS_DEMO = {
    "admin@musicpro.test": {"nombre": "Alex Morgan", "rol": "administrador"},
    "cliente@musicpro.test": {"nombre": "Camila Torres", "rol": "cliente"},
}


def clave_cuenta(correo):
    return "cuenta:" + hashlib.sha256(correo.encode()).hexdigest()


def acceso_requerido(solo_admin=False):
    def decorador(vista):
        @wraps(vista)
        def protegida(request, *args, **kwargs):
            usuario = request.session.get("usuario")
            if not usuario:
                messages.info(request, "Inicia sesión para acceder a tus envíos.")
                return redirect("core:inicio")
            if solo_admin and usuario["rol"] != "administrador":
                return render(request, "core/error.html", {"titulo": "Acceso restringido", "detalle": "Esta acción está disponible para el equipo de operaciones."}, status=403)
            return vista(request, *args, **kwargs)
        return protegida
    return decorador


def inicio(request):
    if request.session.get("usuario"):
        return redirect("core:panel")
    form = AccesoForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        correo = form.cleaned_data["correo"].lower()
        password = form.cleaned_data["contrasena"]
        cuenta = CUENTAS_DEMO.get(correo)
        valida = cuenta is not None and secrets.compare_digest(password.encode(), b"MusicPro2026!")
        if cuenta is None:
            cuenta = cache.get(clave_cuenta(correo))
            valida = check_password(password, cuenta["password"]) if cuenta else False
        if valida:
            request.session.cycle_key()
            request.session["usuario"] = {"correo": correo, "nombre": cuenta["nombre"], "rol": cuenta["rol"]}
            messages.success(request, "Bienvenido. Tu espacio de seguimiento está listo.")
            return redirect("core:panel")
        form.add_error(None, "Correo o contraseña incorrectos. Revisa los datos e intenta nuevamente.")
    return render(request, "core/iniciar_sesion.html", {"form": form, "rastreo_form": RastreoForm(), "pagina": "inicio"})


def registro(request):
    if request.session.get("usuario"):
        return redirect("core:panel")
    form = RegistroForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        correo = form.cleaned_data["correo"].lower()
        cuenta = {"nombre": form.cleaned_data["nombre"], "rol": "cliente", "password": make_password(form.cleaned_data["contrasena"])}
        if correo in CUENTAS_DEMO or not cache.add(clave_cuenta(correo), cuenta, timeout=7200):
            form.add_error("correo", "Este correo ya está registrado en la demostración.")
        else:
            messages.success(request, "Cuenta temporal creada. Ya puedes iniciar sesión durante las próximas 2 horas.")
            return redirect("core:inicio")
    return render(request, "core/registro_usuario.html", {"form": form, "pagina": "registro"})


@require_POST
def salir(request):
    request.session.flush()
    messages.info(request, "Sesión cerrada. Los cambios de esta sesión se reiniciaron.")
    return redirect("core:inicio")


@acceso_requerido()
def panel(request):
    todos = envios_visibles(request)
    query = request.GET.get("q", "").strip()[:100]
    estado = request.GET.get("estado", "")
    filtrados = filtrar_envios(todos, query, estado)
    resumen = [{"codigo": codigo, "nombre": nombre, "cantidad": sum(e["estado"] == codigo for e in todos)} for codigo, nombre in ESTADOS]
    return render(request, "core/panel_envios.html", {
        "pagina": "panel", "envios": Paginator(filtrados, 6).get_page(request.GET.get("pagina")),
        "resumen": resumen, "total": len(todos), "coincidencias": len(filtrados),
        "q": query, "estado": estado, "estados": ESTADOS,
        "peso_total": sum(float(e["peso"]) for e in todos),
    })


def rastreo(request):
    form = RastreoForm(request.GET if "codigo" in request.GET else None)
    if form.is_bound and form.is_valid():
        codigo = form.cleaned_data["codigo"]
        if any(e["codigo"] == codigo for e in cargar_envios(request)):
            return redirect("core:detalle_envio", codigo=codigo)
        form.add_error("codigo", "No encontramos ese envío. Revisa el código e inténtalo nuevamente.")
    return render(request, "core/buscar_envio.html", {"form": form, "pagina": "rastreo"})


def detalle_envio(request, codigo):
    envio = next((e for e in cargar_envios(request) if e["codigo"] == codigo.upper()), None)
    if not envio:
        return render(request, "core/error.html", {"titulo": "Envío no encontrado", "detalle": "Revisa el código de seguimiento o vuelve a buscar."}, status=404)
    usuario = request.session.get("usuario", {})
    privado = usuario.get("rol") == "administrador" or usuario.get("correo") == envio["cliente"]
    pasos = [{"nombre": nombre, "completo": i <= envio["paso"]} for i, (_, nombre) in enumerate(ESTADOS)]
    # La vista pública entrega solo hitos, sin direcciones ni datos personales.
    if not privado:
        envio = {k: envio[k] for k in ("codigo", "estado", "estado_nombre", "paso", "progreso", "eta")}
    return render(request, "core/detalle_envio.html", {"envio": envio, "privado": privado, "pasos": pasos, "pagina": "rastreo"})


@acceso_requerido(solo_admin=True)
def nuevo_envio(request):
    form = EnvioForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        nuevos = request.session.get("envios_nuevos", [])
        if len(nuevos) >= 20:
            form.add_error(None, "Esta sesión admite hasta 20 envíos de demostración. Cierra sesión para reiniciarla.")
        else:
            envio = dict(form.cleaned_data)
            envio.update(codigo="MP-2026-" + secrets.token_hex(4).upper(), cliente=envio["cliente"].lower(), peso=float(envio["peso"]), estado="bodega", eta="Por programar", conductor="Por asignar", patente="Sin asignar", historial=[{"estado": "bodega", "titulo": "Ingreso a bodega", "nota": "Orden de despacho creada.", "fecha": timezone.now().isoformat()}])
            nuevos.append(envio)
            request.session["envios_nuevos"] = nuevos
            messages.success(request, "Envío creado para esta sesión de demostración.")
            return redirect("core:detalle_envio", codigo=envio["codigo"])
    return render(request, "core/formulario_envio.html", {"form": form, "titulo": "Crear un nuevo envío", "subtitulo": "Prepara el próximo despacho de Music Pro.", "boton": "Guardar envío", "pagina": "nuevo"})


@acceso_requerido(solo_admin=True)
def actualizar_estado(request, codigo):
    envio = next((e for e in envios_visibles(request) if e["codigo"] == codigo), None)
    if not envio:
        raise Http404("Envío no encontrado")
    siguiente = ESTADOS[envio["paso"] + 1:envio["paso"] + 2]
    if not siguiente:
        messages.info(request, "Este envío ya fue recibido y su seguimiento está completo.")
        return redirect("core:detalle_envio", codigo=codigo)
    form = EstadoForm(request.POST if request.method == "POST" else None)
    form.fields["estado"].choices = siguiente
    if request.method == "POST" and form.is_valid():
        historial = [{k: v for k, v in h.items() if k != "fecha_obj"} for h in envio["historial"]]
        historial.append({"estado": form.cleaned_data["estado"], "titulo": dict(ESTADOS)[form.cleaned_data["estado"]], "nota": form.cleaned_data["nota"], "fecha": timezone.now().isoformat()})
        cambios = request.session.get("cambios", {})
        cambios[codigo] = {"estado": form.cleaned_data["estado"], "historial": historial}
        if form.cleaned_data["estado"] == "recibido":
            cambios[codigo]["eta"] = "Entregado"
        request.session["cambios"] = cambios
        messages.success(request, "Estado actualizado. El historial registra el nuevo hito.")
        return redirect("core:detalle_envio", codigo=codigo)
    return render(request, "core/formulario_envio.html", {"form": form, "titulo": "Actualizar seguimiento", "subtitulo": codigo + " · Estado actual: " + envio["estado_nombre"], "boton": "Confirmar estado", "pagina": "panel"})


@acceso_requerido()
def exportar_envios(request):
    envios = filtrar_envios(envios_visibles(request), request.GET.get("q", "").strip()[:100], request.GET.get("estado", ""))
    respuesta = JsonResponse({"modo": "demostracion", "total": len(envios), "envios": envios}, json_dumps_params={"ensure_ascii": False, "indent": 2})
    respuesta["Content-Disposition"] = 'attachment; filename="envios_music_pro.json"'
    return respuesta


def ayuda(request):
    return render(request, "core/ayuda.html", {"pagina": "ayuda"})
