"""Pruebas del recorrido del prototipo; SimpleTestCase impide usar una BD."""
from pathlib import Path
import re

from django.conf import settings
from django.test import Client, SimpleTestCase

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

    def test_html_independiente_y_sin_componentes_excluidos(self):
        core = Path(__file__).resolve().parent
        for nombre in ("models.py", "forms.py", "context_processors.py"):
            self.assertFalse((core / nombre).exists())
        self.assertFalse(list(settings.BASE_DIR.glob("*.sqlite3")))
        for plantilla in (core / "templates" / "core").glob("*.html"):
            texto = plantilla.read_text(encoding="utf-8")
            self.assertIn("<!doctype html>", texto)
            self.assertFalse(re.search(r"{%\s*(extends|include|block)\b", texto), plantilla)
        self.assertNotIn("django.contrib.auth", settings.INSTALLED_APPS)
        self.assertNotIn("django.contrib.sessions", settings.INSTALLED_APPS)

    def test_post_conserva_csrf_sin_autenticacion(self):
        navegador = Client(enforce_csrf_checks=True)
        self.assertEqual(navegador.post("/", {}).status_code, 403)
        navegador.get("/")
        token = navegador.cookies["csrftoken"].value
        self.assertRedirects(navegador.post("/", {"csrfmiddlewaretoken": token}), "/panel/")
