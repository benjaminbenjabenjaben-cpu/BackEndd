from django.urls import path
from . import views

app_name = "core"
urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("salir/", views.salir, name="salir"),
    path("panel/", views.panel, name="panel"),
    path("tipos/", views.tipos, name="tipos"),
    path("tipos/nuevo/", views.tipo_guardar, name="tipo_crear"),
    path("tipos/<int:pk>/editar/", views.tipo_guardar, name="tipo_editar"),
    path("tipos/<int:pk>/eliminar/", views.tipo_eliminar, name="tipo_eliminar"),
    path("vehiculos/", views.vehiculos, name="vehiculos"),
    path("vehiculos/nuevo/", views.vehiculo_guardar, name="vehiculo_crear"),
    path("vehiculos/<int:pk>/editar/", views.vehiculo_guardar, name="vehiculo_editar"),
    path("vehiculos/<int:pk>/eliminar/", views.vehiculo_eliminar, name="vehiculo_eliminar"),
    path("conductores/", views.conductores, name="conductores"),
    path("conductores/nuevo/", views.conductor_guardar, name="conductor_crear"),
    path("conductores/<int:pk>/editar/", views.conductor_guardar, name="conductor_editar"),
    path("conductores/<int:pk>/eliminar/", views.conductor_eliminar, name="conductor_eliminar"),
    path("viajes/", views.viajes, name="viajes"),
    path("viajes/nuevo/", views.viaje_guardar, name="viaje_crear"),
    path("viajes/<int:pk>/editar/", views.viaje_guardar, name="viaje_editar"),
    path("viajes/<int:pk>/eliminar/", views.viaje_eliminar, name="viaje_eliminar"),
    path("usuarios/", views.usuarios, name="usuarios"),
    path("usuarios/nuevo/", views.usuario_guardar, name="usuario_crear"),
    path("usuarios/<int:pk>/editar/", views.usuario_guardar, name="usuario_editar"),
    path("usuarios/<int:pk>/desactivar/", views.usuario_desactivar, name="usuario_desactivar"),
    path("reportes/", views.reportes, name="reportes"),
]
