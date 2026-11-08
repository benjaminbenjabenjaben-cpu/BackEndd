"""Pruebas de los modelos heredados y del generador de datos de E2."""
from io import StringIO
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.management import call_command, CommandError
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Envio, HistorialSeguimiento
from .services import ESTADOS


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


class GeneracionDatosTests(TestCase):
    def generar(self, cantidad):
        salida = StringIO()
        call_command("generar_datos", cantidad, stdout=salida)
        return salida.getvalue()

    def test_carga_por_lotes_y_relaciones_coherentes(self):
        salida = self.generar(1001)
        self.assertEqual(Envio.objects.count(), 1001)
        self.assertIn("Guardados y verificados: 1001 envíos", salida)
        self.assertGreaterEqual(HistorialSeguimiento.objects.count(), 1001)
        self.assertLessEqual(HistorialSeguimiento.objects.count(), 4004)
        estados = [codigo for codigo, _ in ESTADOS]
        for telefono in Envio.objects.values_list("telefono", flat=True):
            self.assertRegex(telefono, r"^\+569[0-9]{8}$")
        for envio in Envio.objects.order_by("pk")[:10]:
            envio.full_clean()
            self.assertLessEqual(len(envio.codigo), 20)
            historial = list(envio.historial.values_list("estado", flat=True))
            self.assertEqual(historial, estados[:estados.index(envio.estado) + 1])

    def test_repetir_carga_agrega_sin_borrar_ni_duplicar_codigos(self):
        self.generar(1)
        original = Envio.objects.get()
        original.destinatario = "Registro editado manualmente"
        original.save()
        self.generar(3)
        self.assertEqual(Envio.objects.count(), 4)
        self.assertEqual(Envio.objects.values("codigo").distinct().count(), 4)
        original.refresh_from_db()
        self.assertEqual(original.destinatario, "Registro editado manualmente")

    def test_cantidades_invalidas_no_insertan(self):
        for cantidad in (0, -1, 1000001):
            with self.subTest(cantidad=cantidad):
                with self.assertRaises(CommandError):
                    self.generar(cantidad)
        self.assertEqual(Envio.objects.count(), 0)
        self.assertEqual(HistorialSeguimiento.objects.count(), 0)

    def test_fallo_de_historial_revierte_la_carga(self):
        self.generar(1)
        envios_antes = Envio.objects.count()
        eventos_antes = HistorialSeguimiento.objects.count()
        with patch(
            "core.management.commands.generar_datos.HistorialSeguimiento.objects.bulk_create",
            side_effect=RuntimeError("Fallo simulado"),
        ):
            with self.assertRaises(RuntimeError):
                self.generar(3)
        self.assertEqual(Envio.objects.count(), envios_antes)
        self.assertEqual(HistorialSeguimiento.objects.count(), eventos_antes)
