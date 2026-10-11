"""Administración de los modelos con las herramientas incluidas en Django."""
from django.contrib import admin

from .models import Envio, HistorialSeguimiento

admin.site.site_header = "Music Pro Courier · Administración"
admin.site.site_title = "Music Pro Admin"
admin.site.index_title = "Administración de transporte y despachos"


@admin.register(Envio)
class EnvioAdmin(admin.ModelAdmin):
    list_display = ("codigo", "destinatario", "estado", "prioridad", "cliente")
    list_filter = ("estado", "prioridad")
    search_fields = ("codigo", "destinatario", "cliente")
    ordering = ("-id",)
    list_per_page = 25


@admin.register(HistorialSeguimiento)
class HistorialSeguimientoAdmin(admin.ModelAdmin):
    list_display = ("envio", "estado", "titulo", "fecha")
    list_filter = ("estado",)
    search_fields = ("envio__codigo", "titulo")
    # Busca el envío por código en lugar de cargar todos en un desplegable.
    autocomplete_fields = ("envio",)
    list_select_related = ("envio",)
    ordering = ("-fecha", "-id")
    list_per_page = 25
