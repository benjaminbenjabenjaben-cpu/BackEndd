"""Lectura de datos mock y operaciones de la demostración; no utiliza ORM."""
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from .forms import ESTADOS

DATOS = Path(__file__).resolve().parent / "data" / "envios.json"


def cargar_envios(request):
    with DATOS.open(encoding="utf-8") as archivo:
        envios = json.load(archivo)
    envios += deepcopy(request.session.get("envios_nuevos", []))
    cambios = request.session.get("cambios", {})
    for envio in envios:
        if envio["codigo"] in cambios:
            envio.update(deepcopy(cambios[envio["codigo"]]))
        envio["estado_nombre"] = dict(ESTADOS)[envio["estado"]]
        envio["paso"] = [codigo for codigo, _ in ESTADOS].index(envio["estado"])
        envio["progreso"] = round(envio["paso"] / 3 * 100)
        for evento in envio["historial"]:
            evento["fecha_obj"] = datetime.fromisoformat(evento["fecha"])
    return envios


def envios_visibles(request):
    usuario = request.session.get("usuario", {})
    return [envio for envio in cargar_envios(request) if usuario.get("rol") == "administrador" or envio["cliente"] == usuario.get("correo")]


def filtrar_envios(envios, query, estado):
    if query:
        envios = [e for e in envios if query.casefold() in " ".join([e["codigo"], e["destinatario"], e["destino"], e["equipo"]]).casefold()]
    if estado:
        envios = [e for e in envios if e["estado"] == estado]
    return envios
