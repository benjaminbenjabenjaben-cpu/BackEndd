from django.urls import path
from . import views

app_name = "core"
urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("registro/", views.registro, name="registro"),
    path("salir/", views.salir, name="salir"),
    path("panel/", views.panel, name="panel"),
    path("envios/nuevo/", views.nuevo_envio, name="nuevo_envio"),
    path("envios/exportar/", views.exportar_envios, name="exportar_envios"),
    path("envios/<str:codigo>/estado/", views.actualizar_estado, name="actualizar_estado"),
    path("rastreo/", views.rastreo, name="rastreo"),
    path("rastreo/<str:codigo>/", views.detalle_envio, name="detalle_envio"),
    path("ayuda/", views.ayuda, name="ayuda"),
]
