"""El panel muestra estadísticas reales del mismo período para ambos perfiles."""
from datetime import date, datetime
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Conductor, TipoVehiculo, Vehiculo, Viaje


class PanelTransporteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user(username="admin_panel")
        cls.operador = get_user_model().objects.create_user(username="operador_panel")
        cls.admin.groups.add(Group.objects.create(name="Administrador"))
        cls.operador.groups.add(Group.objects.create(name="Operador"))
        camion = TipoVehiculo.objects.create(nombre="Camión")
        automovil = TipoVehiculo.objects.create(nombre="Automóvil")
        vehiculos = [
            Vehiculo.objects.create(tipo_vehiculo=tipo, patente=patente,
                marca="Marca", modelo="Modelo", anio=2020)
            for tipo, patente in ((camion, "PAAA11"), (automovil, "PBBB22"))
        ]
        conductores = [
            Conductor.objects.create(rut=rut, nombre=nombre, licencia="A4")
            for rut, nombre in (("11111111-1", "Ana Panel"), ("22222222-2", "Luis Panel"))
        ]
        cls.viajes = []
        for mes, dia, hora, minuto, estado, vehiculo, conductor in (
            (11, 12, 9, 0, "finalizado", 0, 0),
            (11, 6, 10, 0, "programado", 0, 1),
            (10, 14, 0, 0, "en_curso", 1, 0),
            (10, 20, 8, 0, "cancelado", 1, 1),
            (10, 13, 23, 59, "finalizado", 0, 0),
            (11, 13, 0, 0, "programado", 0, 0),
        ):
            cls.viajes.append(Viaje.objects.create(
                vehiculo=vehiculos[vehiculo], conductor=conductores[conductor],
                origen="Santiago", destino="Valparaíso", estado=estado,
                fecha_salida=timezone.make_aware(datetime(2026, mes, dia, hora, minuto)),
            ))

    def setUp(self):
        reloj = patch("core.views.timezone.localdate", return_value=date(2026, 11, 12))
        reloj.start()
        self.addCleanup(reloj.stop)
        self.client.force_login(self.admin)

    def test_estadisticas_y_series_coinciden_con_los_viajes_del_periodo(self):
        respuesta = self.client.get(reverse("core:panel"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "core/panel_transporte.html")
        datos = respuesta.context
        self.assertEqual(datos["periodo"], "30")
        self.assertEqual(datos["totales"], {
            "vehiculos": 2, "conductores": 2, "realizados": 1, "programados": 1,
        })
        self.assertEqual({fila["codigo"]: fila["total"] for fila in datos["estados"]}, {
            "programado": 1, "en_curso": 1, "finalizado": 1, "cancelado": 1,
        })
        self.assertEqual({fila["nombre"]: fila["total"] for fila in datos["por_tipo"]}, {
            "Camión": 2, "Automóvil": 2,
        })
        self.assertEqual(len(datos["evolucion"]), 30)
        self.assertEqual(sum(fila["total"] for fila in datos["evolucion"]), 4)
        self.assertEqual(datos["evolucion"][0]["total"], 1)
        self.assertEqual(datos["evolucion"][-1]["total"], 1)
        self.assertEqual({fila["nombre"]: fila["total"] for fila in datos["top_conductores"]}, {
            "Ana Panel": 2, "Luis Panel": 2,
        })
        self.assertTrue(all(fila["participacion"] == 50 for fila in datos["top_conductores"]))
        self.assertEqual([viaje.pk for viaje in datos["ultimos_viajes"]],
                         [self.viajes[i].pk for i in (0, 1, 3, 2)])

    def test_cambiar_periodo_filtra_y_un_valor_invalido_vuelve_a_treinta_dias(self):
        respuesta = self.client.get(reverse("core:panel"), {"periodo": "7"})
        self.assertEqual(respuesta.context["periodo"], "7")
        self.assertEqual(len(respuesta.context["evolucion"]), 7)
        self.assertEqual(sum(fila["total"] for fila in respuesta.context["estados"]), 2)
        self.assertEqual([viaje.pk for viaje in respuesta.context["ultimos_viajes"]],
                         [self.viajes[0].pk, self.viajes[1].pk])
        for valor in ("0", "-1", "999999", "texto"):
            with self.subTest(periodo=valor):
                respuesta = self.client.get(reverse("core:panel"), {"periodo": valor})
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta.context["periodo"], "30")

    def test_sin_viajes_muestra_ceros_sin_inventar_datos(self):
        Viaje.objects.all().delete()
        respuesta = self.client.get(reverse("core:panel"))
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.context
        self.assertEqual(datos["totales"]["realizados"], 0)
        self.assertEqual(datos["totales"]["programados"], 0)
        self.assertEqual(sum(fila["total"] for fila in datos["estados"]), 0)
        self.assertEqual(sum(fila["total"] for fila in datos["evolucion"]), 0)
        self.assertFalse(datos["top_conductores"])
        self.assertFalse(datos["ultimos_viajes"])

    def test_administrador_y_operador_ven_las_mismas_cifras_con_su_perfil(self):
        administrador = self.client.get(reverse("core:panel"))
        self.assertTrue(administrador.context["es_administrador"])
        self.assertContains(administrador, "Administrador")
        self.client.force_login(self.operador)
        operador = self.client.get(reverse("core:panel"))
        self.assertEqual(operador.status_code, 200)
        self.assertFalse(operador.context["es_administrador"])
        self.assertContains(operador, "Operador")
        self.assertEqual(operador.context["totales"], administrador.context["totales"])
