"""Datos ficticios: lectura de JSON y operaciones con listas de Python."""
import json
from datetime import datetime
from pathlib import Path

ESTADOS = [
    ("bodega", "En bodega"),
    ("enviado", "Enviado"),
    ("camino", "En camino"),
    ("recibido", "Recibido"),
]
DATOS = Path(__file__).resolve().parent / "data" / "envios.json"


def preparar_envio(envio):
    """Agrega las etiquetas y el progreso que mostrará el HTML."""
    envio["estado_nombre"] = dict(ESTADOS)[envio["estado"]]
    envio["paso"] = [codigo for codigo, _ in ESTADOS].index(envio["estado"])
    envio["progreso"] = round(envio["paso"] / 3 * 100)
    for evento in envio["historial"]:
        evento["fecha_obj"] = datetime.fromisoformat(evento["fecha"])
    return envio


def cargar_envios():
    """Lee los ejemplos; nunca modifica el archivo."""
    with DATOS.open(encoding="utf-8") as archivo:
        return [preparar_envio(envio) for envio in json.load(archivo)]


def filtrar_envios(envios, query, estado):
    """Filtra la lista según el texto buscado y el estado seleccionado."""
    if query:
        envios = [e for e in envios if query.casefold() in " ".join(
            [e["codigo"], e["destinatario"], e["destino"], e["equipo"]]
        ).casefold()]
    if estado:
        envios = [e for e in envios if e["estado"] == estado]
    return envios
