"""Regresiones de acceso directo, redirecciones y desactivación de cuentas."""
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from .models import Conductor, TipoVehiculo, Vehiculo, Viaje
from .tests_e3 import DatosE3


class SeguridadFinalTests(DatosE3):
    def test_el_alta_de_usuario_rechaza_contrasenas_debiles(self):
        self.client.force_login(self.administrador)
        for clave in ("12345678", "password", "abc"):
            with self.subTest(clave=clave):
                respuesta = self.client.post(reverse("core:usuario_crear"), {
                    "username": "usuario_prueba_seguridad", "email": "prueba@example.com",
                    "rol": "Operador", "is_active": "on", "password1": clave, "password2": clave,
                })
                self.assertEqual(respuesta.status_code, 200)
                self.assertTrue(respuesta.context["error"])
                self.assertFalse(get_user_model().objects.filter(username="usuario_prueba_seguridad").exists())

    def test_post_anonimo_no_crea_modifica_elimina_ni_desactiva_registros(self):
        Usuario = get_user_model()
        modelos = (TipoVehiculo, Vehiculo, Conductor, Viaje, Usuario, Usuario.groups.through)

        def estado_base():
            return [list(modelo.objects.order_by("pk").values()) for modelo in modelos]

        antes = estado_base()
        usuario = {
            "username": "usuario_anonimo", "first_name": "Cambio", "last_name": "Prueba",
            "email": "prueba@example.com", "rol": "Operador", "is_active": "on",
            "password1": "Clave-Prueba-Anonima!", "password2": "Clave-Prueba-Anonima!",
        }
        conductor = {"rut": "33333333-3", "nombre": "Conductor nuevo", "licencia": "A4"}
        operaciones = [
            ("tipo_crear", [], {"nombre": "Tipo nuevo", "descripcion": "Prueba"}),
            ("tipo_editar", [self.camion.pk], {"nombre": "Tipo cambiado", "descripcion": "Cambio"}),
            ("tipo_eliminar", [self.automovil.pk], {}),
            ("vehiculo_crear", [], self.datos_vehiculo()),
            ("vehiculo_editar", [self.vehiculo_a.pk], self.datos_vehiculo(patente="MODF11")),
            ("vehiculo_eliminar", [self.sin_viajes.pk], {}),
            ("conductor_crear", [], conductor),
            ("conductor_editar", [self.conductor_a.pk], conductor),
            ("conductor_eliminar", [self.conductor_b.pk], {}),
            ("viaje_crear", [], self.datos_viaje()),
            ("viaje_editar", [self.programado.pk], self.datos_viaje(estado="en_curso")),
            ("viaje_eliminar", [self.programado.pk], {}),
            ("usuario_crear", [], usuario),
            ("usuario_editar", [self.operador.pk], {**usuario, "username": self.operador.username}),
            ("usuario_desactivar", [self.operador.pk], {}),
        ]
        for nombre, argumentos, datos in operaciones:
            with self.subTest(operacion=nombre):
                respuesta = self.client.post(reverse("core:" + nombre, args=argumentos), datos)
                self.assertEqual(respuesta.status_code, 302)
                self.assertEqual(respuesta.url.split("?")[0], reverse("core:inicio"))
                self.assertEqual(estado_base(), antes)

    def test_login_rechaza_redirecciones_externas_y_acepta_una_ruta_interna(self):
        credenciales = {"username": "administrador", "password": "Clave-Prueba-2026!"}
        for destino in ("https://ejemplo-malicioso.test/", "//ejemplo-malicioso.test/", "javascript:alert(1)"):
            with self.subTest(destino=destino):
                self.client.logout()
                respuesta = self.client.post(
                    reverse("core:inicio") + "?" + urlencode({"next": destino}), credenciales,
                )
                self.assertRedirects(respuesta, reverse("core:panel"), fetch_redirect_response=False)
        self.client.logout()
        destino = reverse("core:vehiculos") + "?pagina=2"
        respuesta = self.client.post(
            reverse("core:inicio") + "?" + urlencode({"next": destino}), credenciales,
        )
        self.assertRedirects(respuesta, destino, fetch_redirect_response=False)

    def test_desactivar_usuario_le_quita_el_acceso_a_su_sesion_existente(self):
        navegador_operador = Client()
        navegador_operador.force_login(self.operador)
        self.assertEqual(navegador_operador.get(reverse("core:panel")).status_code, 200)
        self.client.force_login(self.administrador)
        respuesta = self.client.post(reverse("core:usuario_desactivar", args=[self.operador.pk]))
        self.assertRedirects(respuesta, reverse("core:usuarios"))
        self.operador.refresh_from_db()
        self.assertFalse(self.operador.is_active)
        for nombre in ("panel", "reportes"):
            with self.subTest(vista=nombre):
                ruta = reverse("core:" + nombre)
                self.assertRedirects(
                    navegador_operador.get(ruta), reverse("core:inicio") + "?next=" + ruta,
                    fetch_redirect_response=False,
                )
