"""CRUD propio, autenticación y diez consultas ORM para Transporte."""
from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from .decoradores import administrador_requerido, es_administrador
from .models import Conductor, TipoVehiculo, Vehiculo, Viaje

Usuario = get_user_model()
ROLES = ("Administrador", "Operador")
REPORTES = [
    (1, "Todos los vehículos registrados"),
    (2, "Vehículos de un tipo seleccionado"),
    (3, "Vehículos disponibles"),
    (4, "Los 10 vehículos más antiguos"),
    (5, "Cantidad de conductores registrados"),
    (6, "Viajes de un vehículo seleccionado"),
    (7, "Viajes de un conductor seleccionado"),
    (8, "Cantidad de viajes por estado"),
    (9, "Viajes programados en un rango de fechas"),
    (10, "Vehículos sin viajes registrados"),
]


@never_cache
def mostrar(request, plantilla, contexto=None):
    datos = dict(contexto or {})
    datos["es_administrador"] = es_administrador(request.user)
    return render(request, "core/" + plantilla, datos)


def pagina(request, consulta):
    return Paginator(consulta, 20).get_page(request.GET.get("pagina"))


def mensaje_error(error):
    if isinstance(error, ValidationError):
        return " ".join(error.messages)
    if isinstance(error, IntegrityError):
        return "Ya existe un registro con ese identificador."
    return "Revisa los números, las fechas y las opciones seleccionadas."


def guardar(objeto):
    # full_clean comprueba tipos, campos obligatorios y valores únicos.
    with transaction.atomic():
        objeto.full_clean()
        objeto.save()


def fecha_formulario(valor, obligatoria=True):
    if not valor:
        if obligatoria:
            raise ValidationError("La fecha de salida es obligatoria.")
        return None
    fecha = parse_datetime(valor)
    if fecha is None:
        raise ValidationError("Escribe una fecha y hora válidas.")
    return timezone.make_aware(fecha) if timezone.is_naive(fecha) else fecha


def fecha_html(fecha):
    return timezone.localtime(fecha).strftime("%Y-%m-%dT%H:%M") if fecha else ""


@require_GET
def rastreo(request):
    codigo = request.GET.get("codigo", "").strip().upper()
    error = ""
    if "codigo" in request.GET:
        viaje = Viaje.objects.filter(codigo_seguimiento=codigo).first() if len(codigo) <= 20 else None
        if viaje:
            return redirect("core:detalle_envio", codigo=viaje.codigo_seguimiento)
        error = "No encontramos ese pedido. Revisa el código de seguimiento."
    return render(request, "core/portal_cliente.html", {"codigo": codigo[:20], "error": error})


@require_GET
def detalle_envio(request, codigo):
    viaje = get_object_or_404(Viaje, codigo_seguimiento=codigo.upper())
    estados = Viaje.ESTADOS[:3]
    posicion = next((i for i, (estado, _) in enumerate(estados) if estado == viaje.estado), -1)
    pasos = [
        {"nombre": nombre, "completo": i <= posicion, "actual": i == posicion}
        for i, (_, nombre) in enumerate(estados)
    ]
    return render(request, "core/seguimiento_pedido.html", {
        "viaje": viaje, "pasos": pasos, "cancelado": viaje.estado == "cancelado",
    })


@never_cache
def inicio(request):
    if request.user.is_authenticated:
        return redirect("core:panel")
    error = ""
    if request.method == "POST":
        usuario = authenticate(
            request, username=request.POST.get("username", "").strip(),
            password=request.POST.get("password", ""),
        )
        if usuario is not None:
            login(request, usuario)
            destino = request.GET.get("next", "")
            if destino and url_has_allowed_host_and_scheme(destino, {request.get_host()}):
                return redirect(destino)
            return redirect("core:panel")
        error = "Usuario o contraseña incorrectos."
    return mostrar(request, "iniciar_sesion.html", {
        "error": error, "username": request.POST.get("username", ""),
    })


@login_required
@require_POST
def salir(request):
    logout(request)
    return redirect("core:inicio")


@login_required
def panel(request):
    return mostrar(request, "panel_envios.html", {"totales": {
        "tipos": TipoVehiculo.objects.count(), "vehiculos": Vehiculo.objects.count(),
        "conductores": Conductor.objects.count(), "viajes": Viaje.objects.count(),
    }})


@login_required
def tipos(request):
    return mostrar(request, "tipos.html", {"tipos": pagina(request, TipoVehiculo.objects.order_by("nombre"))})


@login_required
@administrador_requerido
def tipo_guardar(request, pk=None):
    objeto = get_object_or_404(TipoVehiculo, pk=pk) if pk else TipoVehiculo()
    datos = {"nombre": objeto.nombre, "descripcion": objeto.descripcion}
    error = ""
    if request.method == "POST":
        datos = request.POST
        objeto.nombre = datos.get("nombre", "").strip()
        objeto.descripcion = datos.get("descripcion", "").strip()
        try:
            guardar(objeto)
            messages.success(request, "Tipo de vehículo guardado correctamente.")
            return redirect("core:tipos")
        except (ValidationError, IntegrityError) as exc:
            error = mensaje_error(exc)
    return mostrar(request, "tipo_form.html", {"objeto": objeto, "datos": datos, "error": error})


def eliminar_registro(request, objeto, volver):
    error = ""
    if request.method == "POST":
        try:
            with transaction.atomic():
                objeto.delete()
            messages.success(request, "Registro eliminado correctamente.")
            return redirect(volver)
        except ProtectedError:
            error = "No puedes eliminarlo porque tiene registros relacionados."
    return mostrar(request, "eliminar.html", {"objeto": objeto, "volver": volver, "error": error})


@login_required
@administrador_requerido
def tipo_eliminar(request, pk):
    return eliminar_registro(request, get_object_or_404(TipoVehiculo, pk=pk), "core:tipos")


@login_required
def vehiculos(request):
    consulta = Vehiculo.objects.select_related("tipo_vehiculo").order_by("patente")
    return mostrar(request, "vehiculos.html", {"vehiculos": pagina(request, consulta)})


@login_required
@administrador_requerido
def vehiculo_guardar(request, pk=None):
    objeto = get_object_or_404(Vehiculo, pk=pk) if pk else Vehiculo()
    datos = {"tipo_vehiculo": str(objeto.tipo_vehiculo_id or ""), "patente": objeto.patente,
             "marca": objeto.marca, "modelo": objeto.modelo, "anio": objeto.anio or "",
             "disponible": objeto.disponible, "estado": objeto.estado}
    error = ""
    if request.method == "POST":
        datos = request.POST.dict()
        datos["disponible"] = "disponible" in request.POST
        objeto.tipo_vehiculo_id = datos.get("tipo_vehiculo") or None
        objeto.patente = datos.get("patente", "").strip().upper()
        objeto.marca = datos.get("marca", "").strip()
        objeto.modelo = datos.get("modelo", "").strip()
        objeto.anio = datos.get("anio", "")
        objeto.disponible = datos["disponible"]
        objeto.estado = datos.get("estado", "").strip()
        try:
            if int(objeto.anio) < 1:
                raise ValidationError("El año debe ser un número positivo.")
            guardar(objeto)
            messages.success(request, "Vehículo guardado correctamente.")
            return redirect("core:vehiculos")
        except (ValidationError, IntegrityError, ValueError, TypeError, OverflowError) as exc:
            error = mensaje_error(exc)
    return mostrar(request, "vehiculo_form.html", {"objeto": objeto, "datos": datos,
        "error": error, "tipos": TipoVehiculo.objects.order_by("nombre")})


@login_required
@administrador_requerido
def vehiculo_eliminar(request, pk):
    return eliminar_registro(request, get_object_or_404(Vehiculo, pk=pk), "core:vehiculos")


@login_required
def conductores(request):
    return mostrar(request, "conductores.html", {"conductores": pagina(request, Conductor.objects.order_by("nombre"))})


@login_required
@administrador_requerido
def conductor_guardar(request, pk=None):
    objeto = get_object_or_404(Conductor, pk=pk) if pk else Conductor()
    campos = ("rut", "nombre", "licencia", "telefono")
    datos = {campo: getattr(objeto, campo) for campo in campos}
    datos["activo"] = objeto.activo
    error = ""
    if request.method == "POST":
        datos = request.POST.dict()
        datos["activo"] = "activo" in request.POST
        for campo in campos:
            setattr(objeto, campo, datos.get(campo, "").strip())
        objeto.activo = datos["activo"]
        try:
            guardar(objeto)
            messages.success(request, "Conductor guardado correctamente.")
            return redirect("core:conductores")
        except (ValidationError, IntegrityError) as exc:
            error = mensaje_error(exc)
    return mostrar(request, "conductor_form.html", {"objeto": objeto, "datos": datos, "error": error})


@login_required
@administrador_requerido
def conductor_eliminar(request, pk):
    return eliminar_registro(request, get_object_or_404(Conductor, pk=pk), "core:conductores")


@login_required
def viajes(request):
    consulta = Viaje.objects.select_related("vehiculo", "conductor").order_by("-fecha_salida", "-id")
    return mostrar(request, "viajes.html", {"viajes": pagina(request, consulta)})


@login_required
@administrador_requerido
def viaje_guardar(request, pk=None):
    objeto = get_object_or_404(Viaje, pk=pk) if pk else Viaje()
    datos = {"vehiculo": str(objeto.vehiculo_id or ""), "conductor": str(objeto.conductor_id or ""),
        "origen": objeto.origen, "destino": objeto.destino, "estado": objeto.estado,
        "fecha_salida": fecha_html(objeto.fecha_salida), "fecha_llegada": fecha_html(objeto.fecha_llegada),
        "observaciones": objeto.observaciones}
    error = ""
    if request.method == "POST":
        datos = request.POST.dict()
        try:
            objeto.vehiculo_id = datos.get("vehiculo") or None
            objeto.conductor_id = datos.get("conductor") or None
            objeto.origen = datos.get("origen", "").strip()
            objeto.destino = datos.get("destino", "").strip()
            objeto.estado = datos.get("estado", "")
            objeto.observaciones = datos.get("observaciones", "").strip()
            objeto.fecha_salida = fecha_formulario(datos.get("fecha_salida"))
            objeto.fecha_llegada = fecha_formulario(datos.get("fecha_llegada"), obligatoria=False)
            if objeto.fecha_llegada and objeto.fecha_llegada < objeto.fecha_salida:
                raise ValidationError("La llegada no puede ser anterior a la salida.")
            guardar(objeto)
            messages.success(request, "Viaje guardado correctamente.")
            return redirect("core:viajes")
        except (ValidationError, IntegrityError, ValueError, TypeError, OverflowError) as exc:
            error = mensaje_error(exc)
    return mostrar(request, "viaje_form.html", {"objeto": objeto, "datos": datos, "error": error,
        "vehiculos": Vehiculo.objects.order_by("patente"), "conductores": Conductor.objects.order_by("nombre"),
        "estados": Viaje.ESTADOS})


@login_required
@administrador_requerido
def viaje_eliminar(request, pk):
    return eliminar_registro(request, get_object_or_404(Viaje, pk=pk), "core:viajes")


@login_required
@administrador_requerido
def usuarios(request):
    return mostrar(request, "usuarios.html", {"usuarios": pagina(request, Usuario.objects.order_by("username"))})


@login_required
@administrador_requerido
def usuario_guardar(request, pk=None):
    objeto = get_object_or_404(Usuario, pk=pk) if pk else Usuario()
    rol_actual = "Administrador" if objeto.pk and es_administrador(objeto) else "Operador"
    campos = ("username", "first_name", "last_name", "email")
    datos = {campo: getattr(objeto, campo) for campo in campos}
    datos.update(rol=rol_actual, is_active=objeto.is_active)
    error = ""
    if request.method == "POST":
        datos = request.POST.dict()
        datos["is_active"] = "is_active" in request.POST
        try:
            rol = datos.get("rol", "")
            if rol not in ROLES:
                raise ValidationError("Selecciona un perfil válido.")
            if objeto.pk == request.user.pk and (not datos["is_active"] or rol != "Administrador"):
                raise ValidationError("No puedes desactivar tu cuenta ni quitarte el perfil Administrador.")
            if objeto.is_superuser and (not datos["is_active"] or rol != "Administrador"):
                raise ValidationError("La cuenta de superusuario debe permanecer activa y como Administrador.")
            for campo in campos:
                setattr(objeto, campo, datos.get(campo, "").strip())
            objeto.is_active = datos["is_active"]
            if not objeto.pk:
                clave = datos.get("password1", "")
                if not clave or clave != datos.get("password2", ""):
                    raise ValidationError("Escribe y confirma la misma contraseña.")
                validate_password(clave, objeto)
                objeto.set_password(clave)
            with transaction.atomic():
                objeto.full_clean()
                objeto.save()
                grupo, _ = Group.objects.get_or_create(name=rol)
                objeto.groups.set([grupo])
            messages.success(request, "Usuario guardado correctamente.")
            return redirect("core:usuarios")
        except (ValidationError, IntegrityError) as exc:
            error = mensaje_error(exc)
    return mostrar(request, "usuario_form.html", {"objeto": objeto, "datos": datos,
        "error": error, "roles": ROLES, "rol_actual": rol_actual})


@login_required
@administrador_requerido
def usuario_desactivar(request, pk):
    objeto = get_object_or_404(Usuario, pk=pk)
    error = ""
    if request.method == "POST":
        if objeto.pk == request.user.pk or objeto.is_superuser:
            error = "No puedes desactivar tu propia cuenta ni el superusuario."
        else:
            objeto.is_active = False
            objeto.save(update_fields=["is_active"])
            messages.success(request, "Usuario desactivado correctamente.")
            return redirect("core:usuarios")
    return mostrar(request, "eliminar.html", {"objeto": objeto, "volver": "core:usuarios",
        "accion": "Desactivar", "error": error})


@login_required
def reportes(request):
    error = ""
    try:
        numero = int(request.GET.get("consulta", 1))
        if numero not in range(1, 11):
            raise ValueError
    except (ValueError, TypeError):
        numero = 1
        error = "Selecciona una consulta del 1 al 10."
    columnas, resultados = (), []
    vehiculos_base = Vehiculo.objects.select_related("tipo_vehiculo").order_by("patente")
    viajes_base = Viaje.objects.select_related("vehiculo", "conductor").order_by("fecha_salida", "id")
    try:
        if numero in (1, 2, 3, 4, 10):
            consulta = vehiculos_base
            if numero == 2:
                tipo = get_object_or_404(TipoVehiculo, pk=int(request.GET["tipo"]))
                consulta = consulta.filter(tipo_vehiculo=tipo)
            elif numero == 3:
                consulta = consulta.filter(disponible=True)
            elif numero == 4:
                consulta = consulta.order_by("anio", "id")[:10]
            elif numero == 10:
                consulta = consulta.filter(viajes__isnull=True)
            columnas = ("Patente", "Tipo", "Marca", "Modelo", "Año", "Disponible")
            resultados = [(v.patente, v.tipo_vehiculo.nombre, v.marca, v.modelo, v.anio,
                           "Sí" if v.disponible else "No") for v in consulta]
        elif numero == 5:
            columnas, resultados = ("Conductores registrados",), [(Conductor.objects.count(),)]
        elif numero in (6, 7, 9):
            consulta = viajes_base
            if numero == 6:
                vehiculo = get_object_or_404(Vehiculo, pk=int(request.GET["vehiculo"]))
                consulta = consulta.filter(vehiculo=vehiculo)
            elif numero == 7:
                conductor = get_object_or_404(Conductor, pk=int(request.GET["conductor"]))
                consulta = consulta.filter(conductor=conductor)
            else:
                desde, hasta = parse_date(request.GET["desde"]), parse_date(request.GET["hasta"])
                if not desde or not hasta or desde > hasta:
                    raise ValidationError("Selecciona un rango de fechas válido.")
                inicio_periodo = timezone.make_aware(datetime.combine(desde, time.min))
                fin_periodo = timezone.make_aware(datetime.combine(hasta + timedelta(days=1), time.min))
                consulta = consulta.filter(
                    estado="programado", fecha_salida__gte=inicio_periodo, fecha_salida__lt=fin_periodo,
                )
            columnas = ("Viaje", "Vehículo", "Conductor", "Origen", "Destino", "Salida", "Estado")
            resultados = [(v.pk, v.vehiculo.patente, v.conductor.nombre, v.origen, v.destino,
                           timezone.localtime(v.fecha_salida).strftime("%d/%m/%Y %H:%M"),
                           v.get_estado_display()) for v in consulta]
        elif numero == 8:
            conteos = Viaje.objects.values("estado").annotate(total=Count("id"))
            cantidades = {fila["estado"]: fila["total"] for fila in conteos}
            columnas = ("Estado", "Cantidad")
            resultados = [(nombre, cantidades.get(estado, 0)) for estado, nombre in Viaje.ESTADOS]
    except (KeyError, ValueError, TypeError, OverflowError, ValidationError) as exc:
        error = "Selecciona los filtros necesarios para ejecutar la consulta."
        if isinstance(exc, ValidationError):
            error = mensaje_error(exc)
    return mostrar(request, "reportes.html", {"numero": numero, "titulo": dict(REPORTES)[numero],
        "reportes": REPORTES, "columnas": columnas, "resultados": resultados, "error": error,
        "tipos": TipoVehiculo.objects.order_by("nombre"), "vehiculos": vehiculos_base,
        "conductores": Conductor.objects.order_by("nombre"), "filtros": request.GET})
