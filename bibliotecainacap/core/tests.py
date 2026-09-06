"""Pruebas funcionales U1. SimpleTestCase prohíbe consultas a la base de datos."""
from django.core.cache import cache
from django.test import Client, SimpleTestCase
from django.urls import reverse

from .forms import EnvioForm


class PortalTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def acceder(self, rol="admin"):
        return self.client.post(reverse("core:inicio"), {"correo": f"{rol}@musicpro.test", "contrasena": "MusicPro2026!"})

    def test_paginas_publicas_y_estaticos_referenciados(self):
        for nombre in ("inicio", "registro", "rastreo", "ayuda"):
            response = self.client.get(reverse(f"core:{nombre}"))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "/static/core/portal.css")

    def test_acceso_invalido_no_crea_sesion_de_usuario(self):
        response = self.client.post("/", {"correo": "admin@musicpro.test", "contrasena": "incorrecta"})
        self.assertContains(response, "Correo o contraseña incorrectos")
        self.assertNotIn("usuario", self.client.session)

    def test_panel_protegido_y_login_correcto(self):
        self.assertRedirects(self.client.get("/panel/"), "/")
        self.assertRedirects(self.acceder(), "/panel/")
        response = self.client.get("/panel/")
        self.assertEqual(response.context["total"], 8)
        self.assertContains(response, "Control de despachos")

    def test_filtros_paginacion_y_vacio(self):
        self.acceder()
        response = self.client.get("/panel/", {"estado": "camino", "q": "fender"})
        self.assertEqual(response.context["coincidencias"], 1)
        self.assertContains(response, "MP-2026-001")
        self.assertContains(self.client.get("/panel/", {"q": "inexistente"}), "No hay envíos para mostrar")
        self.assertEqual(len(self.client.get("/panel/?pagina=2").context["envios"]), 2)
        self.assertEqual(self.client.get("/panel/?pagina=error").status_code, 200)

    def test_cliente_solo_ve_sus_envios_y_no_administra(self):
        self.acceder("cliente")
        response = self.client.get("/panel/")
        self.assertEqual(response.context["total"], 4)
        self.assertNotContains(response, "MP-2026-002")
        for url in ("/envios/nuevo/", "/envios/MP-2026-001/estado/"):
            self.assertEqual(self.client.get(url).status_code, 403)
            self.assertEqual(self.client.post(url, {}).status_code, 403)

    def test_rastreo_normaliza_codigo_y_maneja_errores(self):
        self.assertRedirects(self.client.get("/rastreo/?codigo=mp-2026-001"), "/rastreo/MP-2026-001/")
        self.assertContains(self.client.get("/rastreo/?codigo=MP-2026-999"), "No encontramos ese envío")
        self.assertContains(self.client.get("/rastreo/?codigo=INVALIDO"), "Usa un código")
        self.assertEqual(self.client.get("/rastreo/MP-2026-999/").status_code, 404)

    def test_rastreo_publico_y_otro_cliente_no_filtran_datos_personales(self):
        response = self.client.get("/rastreo/MP-2026-002/")
        self.assertContains(response, "En bodega")
        self.assertNotContains(response, "sucursal@musicpro.test")
        self.assertNotContains(response, "Vicuña Mackenna")
        self.acceder("cliente")
        self.assertNotContains(self.client.get("/rastreo/MP-2026-002/"), "sucursal@musicpro.test")
        self.assertContains(self.client.get("/rastreo/MP-2026-001/"), "Historial de seguimiento")

    def test_exportacion_respeta_propiedad_y_filtros(self):
        self.acceder("cliente")
        response = self.client.get("/envios/exportar/?estado=camino")
        data = response.json()
        self.assertEqual(data["total"], 2)
        self.assertTrue(all(e["cliente"] == "cliente@musicpro.test" and e["estado"] == "camino" for e in data["envios"]))
        self.assertIn("attachment", response["Content-Disposition"])

    def test_creacion_valida_y_estado_secuencial(self):
        self.acceder()
        data = {"cliente": "cliente@musicpro.test", "destinatario": "Sala de ensayo", "origen": "Bodega Central · Quilicura", "destino": "Calle Prueba 123", "equipo": "Guitarra", "bultos": 2, "peso": "12.5", "prioridad": "alta"}
        invalido = self.client.post("/envios/nuevo/", {**data, "peso": "-1"})
        self.assertEqual(invalido.status_code, 200)
        self.assertTrue(invalido.context["form"].errors)
        self.assertNotIn("envios_nuevos", self.client.session)
        response = self.client.post("/envios/nuevo/", data)
        self.assertEqual(response.status_code, 302)
        codigo = self.client.session["envios_nuevos"][0]["codigo"]
        self.assertContains(self.client.get(response.url), "Guitarra")
        url = reverse("core:actualizar_estado", args=[codigo])
        self.assertEqual(self.client.post(url, {"estado": "recibido", "nota": "Salto inválido"}).status_code, 200)
        self.assertNotIn(codigo, self.client.session.get("cambios", {}))
        self.assertEqual(self.client.post(url, {"estado": "enviado", "nota": "Carga verificada y despachada"}).status_code, 302)
        self.assertEqual(self.client.session["cambios"][codigo]["estado"], "enviado")
        self.assertContains(self.client.get(response.url), "Carga verificada y despachada")

    def test_entrega_finalizada_no_retrocede(self):
        self.acceder()
        self.assertRedirects(self.client.post("/envios/MP-2026-004/estado/", {"estado": "bodega", "nota": "Intento de cambio"}), "/rastreo/MP-2026-004/")
        self.assertNotIn("MP-2026-004", self.client.session.get("cambios", {}))

    def test_registro_valida_confirmacion_y_permite_login(self):
        data = {"nombre": "Cliente Prueba", "correo": "nuevo@example.test", "contrasena": "PruebaSegura2026", "confirmar": "no-coincide", "aceptar": "on"}
        self.assertContains(self.client.post("/registro/", data), "Las contraseñas no coinciden")
        data["confirmar"] = data["contrasena"]
        self.assertRedirects(self.client.post("/registro/", data), "/")
        self.assertContains(self.client.post("/registro/", data), "Este correo ya está registrado")
        response = self.client.post("/", {"correo": data["correo"], "contrasena": data["contrasena"]})
        self.assertRedirects(response, "/panel/")
        self.assertEqual(self.client.session["usuario"]["rol"], "cliente")
        self.assertNotIn("password", self.client.session["usuario"])
        self.assertContains(self.client.get("/panel/"), "No hay envíos para mostrar")

    def test_salir_solo_por_post_y_elimina_cambios(self):
        self.acceder()
        self.assertEqual(self.client.get("/salir/").status_code, 405)
        self.assertRedirects(self.client.post("/salir/"), "/")
        self.assertNotIn("usuario", self.client.session)

    def test_csrf_rechaza_post_sin_token(self):
        cliente = Client(enforce_csrf_checks=True)
        self.assertEqual(cliente.post("/", {"correo": "admin@musicpro.test", "contrasena": "MusicPro2026!"}).status_code, 403)

    def test_peso_acepta_limites_exactos_y_rechaza_fuera_de_rango(self):
        datos = {"cliente": "cliente@musicpro.test", "destinatario": "Sala de ensayo", "origen": "Bodega Central · Quilicura", "destino": "Calle Prueba 123", "equipo": "Micrófono", "bultos": 1, "prioridad": "normal"}
        for peso in ("0.1", "3000.0"):
            with self.subTest(peso=peso):
                form = EnvioForm({**datos, "peso": peso})
                self.assertTrue(form.is_valid(), form.errors)
        for peso in ("0", "-1", "3000.1", "0.01"):
            with self.subTest(peso=peso):
                self.assertIn("peso", EnvioForm({**datos, "peso": peso}).errors)

    def test_post_vacio_muestra_errores_en_todos_los_formularios(self):
        for ruta in ("/", "/registro/"):
            response = self.client.post(ruta, {})
            self.assertTrue(response.context["form"].is_bound)
            self.assertTrue(response.context["form"].errors)
        self.acceder()
        for ruta in ("/envios/nuevo/", "/envios/MP-2026-002/estado/"):
            response = self.client.post(ruta, {})
            self.assertTrue(response.context["form"].is_bound)
            self.assertTrue(response.context["form"].errors)
        self.assertNotIn("envios_nuevos", self.client.session)
        self.assertNotIn("cambios", self.client.session)

    def test_recibir_envio_cierra_la_estimacion_y_registra_hito(self):
        self.acceder()
        response = self.client.post("/envios/MP-2026-001/estado/", {"estado": "recibido", "nota": "Instrumentos recibidos en sucursal."})
        self.assertRedirects(response, "/rastreo/MP-2026-001/")
        cambio = self.client.session["cambios"]["MP-2026-001"]
        self.assertEqual(cambio["eta"], "Entregado")
        self.assertEqual(cambio["historial"][-1]["estado"], "recibido")
        self.assertContains(self.client.get(response.url), "Entregado")
