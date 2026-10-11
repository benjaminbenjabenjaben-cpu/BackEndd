"""Pruebas de la interfaz U1 y de los modelos de base de datos U2."""
from pathlib import Path
import re

from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse

from .models import Envio, HistorialSeguimiento
from .services import DATOS


class PortalTests(SimpleTestCase):
    def test_paginas_accesibles_sin_cuenta(self):
        for ruta in ("/", "/registro/", "/panel/", "/rastreo/", "/ayuda/",
                     "/envios/nuevo/", "/rastreo/MP-2026-001/",
                     "/envios/MP-2026-001/estado/"):
            with self.subTest(ruta=ruta):
                respuesta = self.client.get(ruta)
                self.assertContains(respuesta, "<!doctype html>")
                self.assertContains(respuesta, '<main id="contenido"')
                self.assertNotContains(respuesta, "{%")

    def test_acceso_no_valida_credenciales_ni_crea_sesion(self):
        for datos in ({}, {"correo": "no-es-correo", "contrasena": "cualquier-cosa"}):
            self.assertRedirects(self.client.post("/", datos), "/panel/")
        self.assertNotIn("sessionid", self.client.cookies)

    def test_registro_solo_visual(self):
        respuesta = self.client.post("/registro/", {"correo": "ejemplo"})
        self.assertContains(respuesta, "No se creó una cuenta")
        self.assertNotIn("sessionid", self.client.cookies)

    def test_panel_filtra_y_pagina(self):
        respuesta = self.client.get("/panel/")
        self.assertEqual(respuesta.context["total"], 8)
        self.assertEqual(len(respuesta.context["envios"]), 6)
        pagina_dos = self.client.get("/panel/", {"pagina": 2})
        self.assertEqual(len(pagina_dos.context["envios"]), 2)
        filtrado = self.client.get("/panel/", {"q": "MP-2026-001", "estado": "camino"})
        self.assertEqual(filtrado.context["coincidencias"], 1)
        vacio = self.client.get("/panel/", {"q": "inexistente"})
        self.assertContains(vacio, "No hay envíos para mostrar")

    def test_rastreo_normaliza_y_maneja_codigo_inexistente(self):
        self.assertRedirects(self.client.get("/rastreo/", {"codigo": " mp-2026-001 "}),
                             "/rastreo/MP-2026-001/")
        self.assertContains(self.client.get("/rastreo/", {"codigo": ""}), "No encontramos")
        self.assertEqual(self.client.get("/rastreo/NO-EXISTE/").status_code, 404)

    def test_detalle_completo_y_etapas(self):
        respuesta = self.client.get("/rastreo/MP-2026-001/")
        self.assertContains(respuesta, "Información del despacho")
        self.assertContains(respuesta, "Historial de seguimiento")
        self.assertEqual(len(respuesta.context["pasos"]), 4)
        finalizado = self.client.get("/rastreo/MP-2026-004/")
        self.assertEqual(finalizado.context["envio"]["progreso"], 100)
        self.assertNotContains(finalizado, "Actualizar estado →")

    def test_nuevo_envio_es_vista_previa_sin_guardado(self):
        original = DATOS.read_bytes()
        respuesta = self.client.post("/envios/nuevo/", {
            "cliente": "demo@ejemplo.test", "destinatario": "Teatro de ejemplo",
            "origen": "Bodega Central · Quilicura", "destino": "Calle ficticia 123",
            "equipo": "Guitarra", "prioridad": "normal", "bultos": "2", "peso": "12.5",
        })
        self.assertContains(respuesta, "Vista previa · No guardada.")
        self.assertContains(respuesta, "Teatro de ejemplo")
        self.assertNotContains(respuesta, "Actualizar estado →")
        self.assertEqual(DATOS.read_bytes(), original)
        self.assertEqual(self.client.get("/panel/").context["total"], 8)

    def test_nuevo_envio_maneja_entradas_incompletas(self):
        for peso in ("abc", "NaN", "inf", "-1", "3001"):
            respuesta = self.client.post("/envios/nuevo/", {"peso": peso, "bultos": "2"})
            self.assertContains(respuesta, "Completa los campos")

    def test_estado_es_vista_previa_sin_guardado(self):
        original = DATOS.read_bytes()
        respuesta = self.client.post("/envios/MP-2026-001/estado/", {
            "estado": "recibido", "nota": "Entregado en la demostración.",
        })
        self.assertContains(respuesta, "Vista previa · No guardada.")
        self.assertEqual(respuesta.context["envio"]["estado"], "recibido")
        self.assertEqual(DATOS.read_bytes(), original)
        self.assertEqual(self.client.get("/rastreo/MP-2026-001/").context["envio"]["estado"], "camino")

    def test_estado_invalido_y_finalizado(self):
        self.assertContains(self.client.post("/envios/MP-2026-002/estado/", {
            "estado": "recibido", "nota": "Prueba",
        }), "Selecciona la siguiente etapa")
        self.assertRedirects(self.client.get("/envios/MP-2026-004/estado/"),
                             "/rastreo/MP-2026-004/")
        self.assertEqual(self.client.get("/envios/NO-EXISTE/estado/").status_code, 404)

    def test_exportacion_respeta_filtros(self):
        respuesta = self.client.get("/envios/exportar/", {"estado": "bodega"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["total"], 2)
        self.assertTrue(all(e["estado"] == "bodega" for e in respuesta.json()["envios"]))
        self.assertIn("attachment", respuesta["Content-Disposition"])

    def test_texto_ingresado_se_escapa(self):
        respuesta = self.client.get("/panel/", {"q": '<script>alert("x")</script>'})
        self.assertNotContains(respuesta, '<script>alert("x")</script>')
        self.assertContains(respuesta, "&lt;script&gt;")

    def test_html_independiente_y_formularios_html(self):
        core = Path(__file__).resolve().parent
        for nombre in ("forms.py", "context_processors.py"):
            self.assertFalse((core / nombre).exists())
        for plantilla in (core / "templates" / "core").glob("*.html"):
            texto = plantilla.read_text(encoding="utf-8")
            self.assertIn("<!doctype html>", texto)
            self.assertFalse(re.search(r"{%\s*(extends|include|block)\b", texto), plantilla)

    def test_post_conserva_csrf_sin_autenticacion(self):
        navegador = Client(enforce_csrf_checks=True)
        self.assertEqual(navegador.post("/", {}).status_code, 403)
        navegador.get("/")
        token = navegador.cookies["csrftoken"].value
        self.assertRedirects(navegador.post("/", {"csrfmiddlewaretoken": token}), "/panel/")


class ModelosTests(TestCase):
    def crear_envio(self, **cambios):
        datos = {
            "codigo": "MP-2026-001", "destinatario": "Sucursal de prueba",
            "origen": "Bodega Central", "destino": "Calle de ejemplo 123",
            "equipo": "Guitarra", "bultos": 1, "peso": "12.5",
            "cliente": "cliente@ejemplo.test",
        }
        datos.update(cambios)
        return Envio.objects.create(**datos)

    def test_guardar_consultar_modificar_y_eliminar(self):
        envio = self.crear_envio()
        self.assertEqual(Envio.objects.get(codigo=envio.codigo).destinatario,
                         "Sucursal de prueba")
        envio.destinatario = "Teatro de prueba"
        envio.save()
        envio.refresh_from_db()
        self.assertEqual(envio.destinatario, "Teatro de prueba")
        envio.delete()
        self.assertEqual(Envio.objects.count(), 0)

    def test_codigo_no_se_puede_repetir(self):
        self.crear_envio()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.crear_envio()

    def test_un_envio_tiene_varios_eventos_y_se_eliminan_con_el(self):
        envio = self.crear_envio()
        HistorialSeguimiento.objects.create(
            envio=envio, estado="bodega", titulo="Preparación en bodega",
        )
        HistorialSeguimiento.objects.create(
            envio=envio, estado="enviado", titulo="Despacho confirmado",
        )
        self.assertEqual(envio.historial.count(), 2)
        self.assertEqual(envio.historial.first().estado, "bodega")
        envio.delete()
        self.assertEqual(HistorialSeguimiento.objects.count(), 0)

    def test_datos_incorrectos_se_rechazan_al_validar(self):
        for campo, valor in (("bultos", 0), ("peso", "-1.0"),
                             ("estado", "inexistente"), ("cliente", "sin-correo")):
            with self.subTest(campo=campo):
                envio = Envio(
                    codigo="MP-2026-001", destinatario="Sucursal", origen="Bodega",
                    destino="Dirección de ejemplo", equipo="Guitarra", bultos=1,
                    peso="12.5", cliente="cliente@ejemplo.test",
                )
                setattr(envio, campo, valor)
                with self.assertRaises(ValidationError) as error:
                    envio.full_clean()
                self.assertIn(campo, error.exception.message_dict)


class AdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrador = get_user_model().objects.create_superuser(
            username="admin_prueba", password="Prueba-admin-2026!",
        )
        cls.usuario = get_user_model().objects.create_user(username="usuario_prueba")

    def datos_envio(self, **cambios):
        datos = {
            "codigo": "MP-2026-001", "estado": "bodega", "prioridad": "normal",
            "destinatario": "Sucursal de prueba", "origen": "Bodega Central",
            "destino": "Calle de ejemplo 123", "equipo": "Guitarra",
            "bultos": "1", "peso": "12.5", "cliente": "cliente@ejemplo.test",
        }
        datos.update(cambios)
        return datos

    def test_admin_exige_acceso_y_permisos(self):
        for nombre in ("admin:index", "admin:core_envio_changelist",
                       "admin:core_historialseguimiento_changelist"):
            respuesta = self.client.get(reverse(nombre))
            self.assertEqual(respuesta.status_code, 302)
            self.assertTrue(respuesta.url.startswith(reverse("admin:login")))
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 302)

    def test_login_real_y_modelos_visibles(self):
        respuesta = self.client.post(reverse("admin:login"), {
            "username": "admin_prueba", "password": "Prueba-admin-2026!",
            "next": reverse("admin:index"),
        })
        self.assertRedirects(respuesta, reverse("admin:index"))
        respuesta = self.client.get(reverse("admin:index"))
        self.assertContains(respuesta, "Music Pro Courier")
        self.assertContains(respuesta, reverse("admin:core_envio_changelist"))
        self.assertContains(respuesta, reverse("admin:core_historialseguimiento_changelist"))

    def test_crud_de_ambos_modelos_desde_admin(self):
        self.client.force_login(self.administrador)
        respuesta = self.client.post(reverse("admin:core_envio_add"), self.datos_envio())
        self.assertRedirects(respuesta, reverse("admin:core_envio_changelist"))
        envio = Envio.objects.get(codigo="MP-2026-001")
        editar_envio = reverse("admin:core_envio_change", args=[envio.pk])
        self.assertContains(self.client.get(editar_envio), "Sucursal de prueba")
        respuesta = self.client.post(editar_envio, self.datos_envio(destinatario="Teatro"))
        self.assertEqual(respuesta.status_code, 302)
        envio.refresh_from_db()
        self.assertEqual(envio.destinatario, "Teatro")

        datos_evento = {
            "envio": envio.pk, "estado": "bodega", "titulo": "Preparación",
            "nota": "Equipos revisados", "fecha_0": "2026-10-10", "fecha_1": "12:30:00",
        }
        respuesta = self.client.post(reverse("admin:core_historialseguimiento_add"), datos_evento)
        self.assertRedirects(respuesta, reverse("admin:core_historialseguimiento_changelist"))
        evento = envio.historial.get()
        editar_evento = reverse("admin:core_historialseguimiento_change", args=[evento.pk])
        self.assertContains(self.client.get(editar_evento), "Equipos revisados")
        datos_evento["nota"] = "Carga lista para despacho"
        self.assertEqual(self.client.post(editar_evento, datos_evento).status_code, 302)
        evento.refresh_from_db()
        self.assertEqual(evento.nota, "Carga lista para despacho")

        borrar_evento = reverse("admin:core_historialseguimiento_delete", args=[evento.pk])
        self.assertEqual(self.client.get(borrar_evento).status_code, 200)
        self.assertEqual(self.client.post(borrar_evento, {"post": "yes"}).status_code, 302)
        self.assertFalse(HistorialSeguimiento.objects.filter(pk=evento.pk).exists())
        borrar_envio = reverse("admin:core_envio_delete", args=[envio.pk])
        self.assertEqual(self.client.get(borrar_envio).status_code, 200)
        self.assertEqual(self.client.post(borrar_envio, {"post": "yes"}).status_code, 302)
        self.assertFalse(Envio.objects.filter(pk=envio.pk).exists())

    def test_busqueda_filtros_y_seleccion_de_envio(self):
        self.client.force_login(self.administrador)
        primero = Envio.objects.create(**self.datos_envio())
        Envio.objects.create(**self.datos_envio(codigo="MP-2026-002", estado="camino"))
        ruta = reverse("admin:core_envio_changelist")
        for parametros in ({"q": "MP-2026-001"}, {"estado__exact": "bodega"}):
            respuesta = self.client.get(ruta, parametros)
            self.assertEqual(list(respuesta.context["cl"].queryset), [primero])
        respuesta = self.client.get(reverse("admin:autocomplete"), {
            "app_label": "core", "model_name": "historialseguimiento",
            "field_name": "envio", "term": "MP-2026-001",
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual([r["id"] for r in respuesta.json()["results"]], [str(primero.pk)])

    def test_admin_rechaza_carga_invalida(self):
        self.client.force_login(self.administrador)
        respuesta = self.client.post(reverse("admin:core_envio_add"),
                                     self.datos_envio(bultos="0", peso="-1"))
        self.assertEqual(respuesta.status_code, 200)
        errores = respuesta.context["adminform"].form.errors
        self.assertIn("bultos", errores)
        self.assertIn("peso", errores)
        self.assertEqual(Envio.objects.count(), 0)
