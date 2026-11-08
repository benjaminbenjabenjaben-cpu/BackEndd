"""Pruebas de CRUD, sesiones, permisos y los diez reportes de Transporte."""
import ast
from datetime import datetime
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Conductor, TipoVehiculo, Vehiculo, Viaje


class DatosE3(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.grupo_admin, _ = Group.objects.get_or_create(name="Administrador")
        cls.grupo_operador, _ = Group.objects.get_or_create(name="Operador")
        cls.administrador = get_user_model().objects.create_user(
            username="administrador", password="Clave-Prueba-2026!",
        )
        cls.administrador.groups.add(cls.grupo_admin)
        cls.operador = get_user_model().objects.create_user(
            username="operador", password="Clave-Operador-2026!",
        )
        cls.operador.groups.add(cls.grupo_operador)
        cls.camion = TipoVehiculo.objects.create(nombre="Camión")
        cls.automovil = TipoVehiculo.objects.create(nombre="Automóvil")
        cls.vehiculo_a = Vehiculo.objects.create(
            tipo_vehiculo=cls.camion, patente="AAAA11", marca="Marca A",
            modelo="Modelo A", anio=2010, disponible=True,
        )
        cls.vehiculo_b = Vehiculo.objects.create(
            tipo_vehiculo=cls.automovil, patente="BBBB22", marca="Marca B",
            modelo="Modelo B", anio=2020, disponible=False,
        )
        cls.sin_viajes = Vehiculo.objects.create(
            tipo_vehiculo=cls.camion, patente="CCCC33", marca="Marca C",
            modelo="Modelo C", anio=2000, disponible=True,
        )
        cls.conductor_a = Conductor.objects.create(
            rut="11111111-1", nombre="Ana de prueba", licencia="A4",
            telefono="+56911111111",
        )
        cls.conductor_b = Conductor.objects.create(
            rut="22222222-2", nombre="Luis de prueba", licencia="A2",
            telefono="+56922222222",
        )
        cls.programado = Viaje.objects.create(
            vehiculo=cls.vehiculo_a, conductor=cls.conductor_a,
            origen="Origen primero", destino="Destino primero",
            fecha_salida=cls.fecha(1, 8), estado="programado",
        )
        Viaje.objects.create(
            vehiculo=cls.vehiculo_a, conductor=cls.conductor_b,
            origen="Origen segundo", destino="Destino segundo",
            fecha_salida=cls.fecha(3, 8), fecha_llegada=cls.fecha(3, 10),
            estado="finalizado",
        )
        Viaje.objects.create(
            vehiculo=cls.vehiculo_b, conductor=cls.conductor_a,
            origen="Origen tercero", destino="Destino tercero",
            fecha_salida=cls.fecha(10, 9), estado="programado",
        )
        Viaje.objects.create(
            vehiculo=cls.vehiculo_b, conductor=cls.conductor_b,
            origen="Origen cuarto", destino="Destino cuarto",
            fecha_salida=cls.fecha(5, 8), estado="cancelado",
        )

    @staticmethod
    def fecha(dia, hora):
        return timezone.make_aware(datetime(2026, 11, dia, hora))

    def datos_vehiculo(self, **cambios):
        datos = {
            "tipo_vehiculo": str(self.camion.pk), "patente": "DDDD44",
            "marca": "Marca nueva", "modelo": "Modelo nuevo", "anio": "2024",
            "disponible": "on", "estado": "operativo",
        }
        datos.update(cambios)
        return datos

    def datos_viaje(self, **cambios):
        datos = {
            "vehiculo": str(self.vehiculo_a.pk),
            "conductor": str(self.conductor_a.pk),
            "origen": "Origen nuevo", "destino": "Destino nuevo",
            "fecha_salida": "2026-11-12T09:00", "fecha_llegada": "",
            "estado": "programado", "observaciones": "Prueba de CRUD",
        }
        datos.update(cambios)
        return datos


class SeguridadE3Tests(DatosE3):
    def test_login_valida_credenciales_y_logout_cierra_sesion(self):
        respuesta = self.client.post(reverse("core:inicio"), {
            "username": "administrador", "password": "incorrecta",
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        respuesta = self.client.post(reverse("core:inicio"), {
            "username": "administrador", "password": "Clave-Prueba-2026!",
        })
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.client.session["_auth_user_id"], str(self.administrador.pk))
        self.assertEqual(self.client.get(reverse("core:panel")).status_code, 200)
        self.assertEqual(self.client.get(reverse("core:salir")).status_code, 405)
        self.assertEqual(self.client.post(reverse("core:salir")).status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(self.client.get(reverse("core:panel")).status_code, 302)

    def test_todas_las_vistas_administrativas_requieren_sesion(self):
        rutas = [
            ("panel", []), ("tipos", []), ("vehiculos", []),
            ("conductores", []), ("viajes", []), ("usuarios", []), ("reportes", []),
            ("tipo_crear", []), ("tipo_editar", [self.camion.pk]),
            ("tipo_eliminar", [self.camion.pk]), ("vehiculo_crear", []),
            ("vehiculo_editar", [self.vehiculo_a.pk]),
            ("vehiculo_eliminar", [self.vehiculo_a.pk]), ("conductor_crear", []),
            ("conductor_editar", [self.conductor_a.pk]),
            ("conductor_eliminar", [self.conductor_a.pk]), ("viaje_crear", []),
            ("viaje_editar", [self.programado.pk]),
            ("viaje_eliminar", [self.programado.pk]), ("usuario_crear", []),
            ("usuario_editar", [self.operador.pk]),
            ("usuario_desactivar", [self.operador.pk]),
        ]
        for nombre, argumentos in rutas:
            with self.subTest(vista=nombre):
                respuesta = self.client.get(reverse("core:" + nombre, args=argumentos))
                self.assertEqual(respuesta.status_code, 302)
                self.assertEqual(respuesta.url.split("?")[0], reverse("core:inicio"))

    def test_operador_consulta_pero_no_puede_gestionar_por_url_directa(self):
        self.client.force_login(self.operador)
        for nombre in ("panel", "tipos", "vehiculos", "conductores", "viajes", "reportes"):
            with self.subTest(consulta=nombre):
                self.assertEqual(self.client.get(reverse("core:" + nombre)).status_code, 200)
        protegidas = [
            ("tipo_crear", []), ("tipo_editar", [self.camion.pk]),
            ("tipo_eliminar", [self.camion.pk]), ("vehiculo_crear", []),
            ("vehiculo_editar", [self.vehiculo_a.pk]),
            ("vehiculo_eliminar", [self.vehiculo_a.pk]), ("conductor_crear", []),
            ("conductor_editar", [self.conductor_a.pk]),
            ("conductor_eliminar", [self.conductor_a.pk]), ("viaje_crear", []),
            ("viaje_editar", [self.programado.pk]),
            ("viaje_eliminar", [self.programado.pk]), ("usuarios", []),
            ("usuario_crear", []), ("usuario_editar", [self.administrador.pk]),
            ("usuario_desactivar", [self.administrador.pk]),
        ]
        for nombre, argumentos in protegidas:
            with self.subTest(gestion=nombre):
                url = reverse("core:" + nombre, args=argumentos)
                self.assertEqual(self.client.get(url).status_code, 403)
                self.assertEqual(self.client.post(url, {}).status_code, 403)
        self.assertEqual(Vehiculo.objects.count(), 3)
        self.assertTrue(self.administrador.is_active)

    def test_los_post_exigen_csrf_aun_con_sesion(self):
        navegador = Client(enforce_csrf_checks=True)
        navegador.force_login(self.administrador)
        url = reverse("core:tipo_crear")
        self.assertEqual(navegador.post(url, {"nombre": "Sin token"}).status_code, 403)
        pagina = navegador.get(url)
        self.assertContains(pagina, 'name="csrfmiddlewaretoken"')
        token = navegador.cookies["csrftoken"].value
        respuesta = navegador.post(url, {
            "nombre": "Con token", "descripcion": "Prueba",
            "csrfmiddlewaretoken": token,
        })
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(TipoVehiculo.objects.filter(nombre="Con token").exists())

    def test_los_formularios_son_html_sin_model_forms(self):
        core = Path(__file__).resolve().parent
        self.assertFalse((core / "forms.py").exists())
        arbol = ast.parse((core / "views.py").read_text(encoding="utf-8-sig"))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.ImportFrom):
                self.assertNotEqual(nodo.module, "django.forms")


class CRUDE3Tests(DatosE3):
    def setUp(self):
        self.client.force_login(self.administrador)

    def test_crud_tipo_y_eliminacion_solo_tras_confirmacion(self):
        self.assertEqual(self.client.post(reverse("core:tipo_crear"), {
            "nombre": "Minibús", "descripcion": "Transporte de personas",
        }).status_code, 302)
        tipo = TipoVehiculo.objects.get(nombre="Minibús")
        self.assertContains(self.client.get(reverse("core:tipos")), "Minibús")
        self.assertEqual(self.client.post(reverse("core:tipo_editar", args=[tipo.pk]), {
            "nombre": "Bus", "descripcion": "Descripción modificada",
        }).status_code, 302)
        tipo.refresh_from_db()
        self.assertEqual(tipo.nombre, "Bus")
        eliminar = reverse("core:tipo_eliminar", args=[tipo.pk])
        self.assertEqual(self.client.get(eliminar).status_code, 200)
        self.assertTrue(TipoVehiculo.objects.filter(pk=tipo.pk).exists())
        self.assertEqual(self.client.post(eliminar).status_code, 302)
        self.assertFalse(TipoVehiculo.objects.filter(pk=tipo.pk).exists())

    def test_crud_vehiculo_guarda_relacion_y_checkbox(self):
        self.assertEqual(self.client.post(reverse("core:vehiculo_crear"),
                                         self.datos_vehiculo()).status_code, 302)
        vehiculo = Vehiculo.objects.get(patente="DDDD44")
        self.assertEqual(vehiculo.tipo_vehiculo, self.camion)
        self.assertTrue(vehiculo.disponible)
        datos = self.datos_vehiculo(marca="Marca editada", tipo_vehiculo=str(self.automovil.pk))
        datos.pop("disponible")
        self.assertEqual(self.client.post(reverse("core:vehiculo_editar", args=[vehiculo.pk]),
                                         datos).status_code, 302)
        vehiculo.refresh_from_db()
        self.assertEqual(vehiculo.marca, "Marca editada")
        self.assertEqual(vehiculo.tipo_vehiculo, self.automovil)
        self.assertFalse(vehiculo.disponible)
        self.assertContains(self.client.get(reverse("core:vehiculos")), "DDDD44")
        self.assertEqual(self.client.post(reverse("core:vehiculo_eliminar", args=[vehiculo.pk])).status_code, 302)
        self.assertFalse(Vehiculo.objects.filter(pk=vehiculo.pk).exists())

    def test_crud_conductor_guarda_datos_y_desactivacion(self):
        datos = {"rut": "33333333-3", "nombre": "Conductor nuevo", "licencia": "A4",
                 "telefono": "+56933333333", "activo": "on"}
        self.assertEqual(self.client.post(reverse("core:conductor_crear"), datos).status_code, 302)
        conductor = Conductor.objects.get(rut=datos["rut"])
        datos["nombre"] = "Conductor editado"
        datos.pop("activo")
        self.assertEqual(self.client.post(reverse("core:conductor_editar", args=[conductor.pk]),
                                         datos).status_code, 302)
        conductor.refresh_from_db()
        self.assertEqual(conductor.nombre, "Conductor editado")
        self.assertFalse(conductor.activo)
        self.assertContains(self.client.get(reverse("core:conductores")), "Conductor editado")
        self.assertEqual(self.client.post(reverse("core:conductor_eliminar", args=[conductor.pk])).status_code, 302)
        self.assertFalse(Conductor.objects.filter(pk=conductor.pk).exists())

    def test_crud_viaje_y_fechas(self):
        self.assertEqual(self.client.post(reverse("core:viaje_crear"),
                                         self.datos_viaje()).status_code, 302)
        viaje = Viaje.objects.get(destino="Destino nuevo")
        self.assertEqual(viaje.vehiculo, self.vehiculo_a)
        self.assertEqual(viaje.conductor, self.conductor_a)
        self.assertIsNone(viaje.fecha_llegada)
        datos = self.datos_viaje(destino="Destino editado", fecha_llegada="2026-11-12T11:00",
                                 estado="finalizado")
        self.assertEqual(self.client.post(reverse("core:viaje_editar", args=[viaje.pk]), datos).status_code, 302)
        viaje.refresh_from_db()
        self.assertEqual(viaje.estado, "finalizado")
        self.assertGreater(viaje.fecha_llegada, viaje.fecha_salida)
        self.assertContains(self.client.get(reverse("core:viajes")), "Destino editado")
        self.assertEqual(self.client.post(reverse("core:viaje_eliminar", args=[viaje.pk])).status_code, 302)
        self.assertFalse(Viaje.objects.filter(pk=viaje.pk).exists())

    def test_validacion_no_guarda_entradas_invalidas(self):
        antes = Vehiculo.objects.count()
        for cambios in ({"anio": "abc"}, {"tipo_vehiculo": "9999999"},
                         {"patente": self.vehiculo_a.patente}, {"marca": ""}):
            with self.subTest(cambios=cambios):
                respuesta = self.client.post(reverse("core:vehiculo_crear"),
                                             self.datos_vehiculo(**cambios))
                self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(Vehiculo.objects.count(), antes)
        viajes_antes = Viaje.objects.count()
        for cambios in ({"fecha_salida": "no-es-fecha"}, {"estado": "inexistente"},
                         {"fecha_llegada": "2026-11-11T08:00"}, {"conductor": "9999999"}):
            with self.subTest(cambios=cambios):
                self.assertEqual(self.client.post(reverse("core:viaje_crear"),
                                                 self.datos_viaje(**cambios)).status_code, 200)
        self.assertEqual(Viaje.objects.count(), viajes_antes)

    def test_no_se_borran_entidades_referenciadas(self):
        for ruta, objeto in (("tipo_eliminar", self.camion),
                             ("vehiculo_eliminar", self.vehiculo_a),
                             ("conductor_eliminar", self.conductor_a)):
            with self.subTest(ruta=ruta):
                respuesta = self.client.post(reverse("core:" + ruta, args=[objeto.pk]))
                self.assertEqual(respuesta.status_code, 200)
                self.assertTrue(type(objeto).objects.filter(pk=objeto.pk).exists())
        self.assertEqual(Viaje.objects.count(), 4)

    def test_crear_editar_y_desactivar_usuario_sin_elevar_privilegios(self):
        pagina_crear = self.client.get(reverse("core:usuario_crear"))
        self.assertContains(pagina_crear, 'name="password1"')
        self.assertContains(pagina_crear, 'name="password2"')
        datos = {
            "username": "usuario_nuevo", "first_name": "Nombre", "last_name": "Apellido",
            "email": "nuevo@example.com", "rol": "Operador", "is_active": "on",
            "password1": "Clave-Nueva-2026!", "password2": "Clave-Nueva-2026!",
            "is_superuser": "on", "is_staff": "on",
        }
        self.assertEqual(self.client.post(reverse("core:usuario_crear"), datos).status_code, 302)
        usuario = get_user_model().objects.get(username="usuario_nuevo")
        self.assertTrue(usuario.check_password("Clave-Nueva-2026!"))
        self.assertNotEqual(usuario.password, datos["password1"])
        self.assertTrue(usuario.groups.filter(name="Operador").exists())
        self.assertFalse(usuario.is_superuser)
        self.assertFalse(usuario.is_staff)
        datos.update(first_name="Nombre editado", rol="Administrador")
        self.assertEqual(self.client.post(reverse("core:usuario_editar", args=[usuario.pk]), datos).status_code, 302)
        usuario.refresh_from_db()
        self.assertEqual(usuario.first_name, "Nombre editado")
        self.assertTrue(usuario.groups.filter(name="Administrador").exists())
        self.assertFalse(usuario.groups.filter(name="Operador").exists())
        self.assertContains(self.client.get(reverse("core:usuarios")), "usuario_nuevo")
        ruta = reverse("core:usuario_desactivar", args=[usuario.pk])
        self.assertEqual(self.client.get(ruta).status_code, 200)
        usuario.refresh_from_db()
        self.assertTrue(usuario.is_active)
        self.assertEqual(self.client.post(ruta).status_code, 302)
        usuario.refresh_from_db()
        self.assertFalse(usuario.is_active)
        self.client.logout()
        self.client.post(reverse("core:inicio"), {
            "username": usuario.username, "password": "Clave-Nueva-2026!",
        })
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_un_administrador_no_puede_quitar_su_propio_acceso(self):
        ruta = reverse("core:usuario_desactivar", args=[self.administrador.pk])
        self.client.post(ruta)
        self.administrador.refresh_from_db()
        self.assertTrue(self.administrador.is_active)
        self.client.post(reverse("core:usuario_editar", args=[self.administrador.pk]), {
            "username": self.administrador.username, "first_name": "Nombre",
            "last_name": "Apellido", "email": "admin@example.com", "rol": "Operador",
        })
        self.administrador.refresh_from_db()
        self.assertTrue(self.administrador.is_active)
        self.assertTrue(self.administrador.groups.filter(name="Administrador").exists())


class ReportesE3Tests(DatosE3):
    def setUp(self):
        self.client.force_login(self.operador)

    def consultar(self, numero, **filtros):
        respuesta = self.client.get(reverse("core:reportes"), {"consulta": numero, **filtros})
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("resultados", respuesta.context)
        return respuesta.context["resultados"]

    def texto(self, numero, **filtros):
        return "\n".join(str(valor) for fila in self.consultar(numero, **filtros) for valor in fila)

    def test_reportes_1_a_4_consultan_vehiculos_y_disponibilidad(self):
        todos = self.texto(1)
        for vehiculo in (self.vehiculo_a, self.vehiculo_b, self.sin_viajes):
            self.assertIn(vehiculo.patente, todos)
        tipo = self.texto(2, tipo=self.camion.pk)
        self.assertIn(self.vehiculo_a.patente, tipo)
        self.assertIn(self.sin_viajes.patente, tipo)
        self.assertNotIn(self.vehiculo_b.patente, tipo)
        disponibles = self.texto(3)
        self.assertIn(self.vehiculo_a.patente, disponibles)
        self.assertNotIn(self.vehiculo_b.patente, disponibles)
        antiguos = self.texto(4)
        self.assertLess(antiguos.index(self.sin_viajes.patente), antiguos.index(self.vehiculo_a.patente))
        self.assertLess(antiguos.index(self.vehiculo_a.patente), antiguos.index(self.vehiculo_b.patente))

    def test_reporte_5_cuenta_conductores(self):
        resultados = self.consultar(5)
        valores = [valor for fila in resultados for valor in fila]
        self.assertIn(2, valores)

    def test_reportes_6_y_7_filtran_relaciones_correctas(self):
        por_vehiculo = self.texto(6, vehiculo=self.vehiculo_a.pk)
        self.assertIn("Destino primero", por_vehiculo)
        self.assertIn("Destino segundo", por_vehiculo)
        self.assertNotIn("Destino tercero", por_vehiculo)
        por_conductor = self.texto(7, conductor=self.conductor_a.pk)
        self.assertIn("Destino primero", por_conductor)
        self.assertIn("Destino tercero", por_conductor)
        self.assertNotIn("Destino segundo", por_conductor)

    def test_reporte_8_agrupa_estados_y_cuenta_viajes(self):
        resultados = self.consultar(8)
        cantidades = [valor for fila in resultados for valor in fila if isinstance(valor, int)]
        self.assertEqual(sum(cantidades), 4)
        self.assertIn(2, cantidades)

    def test_reporte_9_filtra_programados_y_rango_inclusivo(self):
        texto = self.texto(9, desde="2026-11-01", hasta="2026-11-01")
        self.assertIn("Destino primero", texto)
        self.assertNotIn("Destino tercero", texto)
        amplio = self.texto(9, desde="2026-11-01", hasta="2026-11-30")
        self.assertIn("Destino tercero", amplio)
        self.assertNotIn("Destino segundo", amplio)
        self.assertNotIn("Destino cuarto", amplio)

    def test_reporte_10_identifica_vehiculos_sin_viajes(self):
        texto = self.texto(10)
        self.assertIn(self.sin_viajes.patente, texto)
        self.assertNotIn(self.vehiculo_a.patente, texto)
        self.assertNotIn(self.vehiculo_b.patente, texto)
