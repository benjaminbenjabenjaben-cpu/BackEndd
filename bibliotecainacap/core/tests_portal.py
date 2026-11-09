"""El cliente consulta el mismo viaje que gestiona el administrador."""
from django.test import Client
from django.urls import reverse

from .models import Viaje
from .tests_e3 import DatosE3


class PortalClienteTests(DatosE3):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.programado.observaciones = "Nota interna: llamar al encargado de bodega."
        cls.programado.save(update_fields=["observaciones"])

    def test_portal_y_rastreo_son_publicos_y_login_tiene_su_ruta(self):
        self.assertEqual(reverse("core:portal"), "/")
        self.assertEqual(reverse("core:rastreo"), "/rastreo/")
        self.assertEqual(reverse("core:inicio"), "/ingresar/")
        for nombre in ("portal", "rastreo", "inicio"):
            with self.subTest(pagina=nombre):
                self.assertEqual(self.client.get(reverse("core:" + nombre)).status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertRedirects(
            self.client.get(reverse("core:panel")),
            reverse("core:inicio") + "?next=/panel/",
            fetch_redirect_response=False,
        )

    def test_los_viajes_tienen_codigos_unicos_de_seguimiento(self):
        codigos = list(Viaje.objects.values_list("codigo_seguimiento", flat=True))
        self.assertEqual(len(codigos), 4)
        self.assertEqual(len(set(codigos)), 4)
        for codigo in codigos:
            self.assertRegex(codigo, r"^MP-[0-9A-F]{16}$")

    def test_buscar_codigo_abre_su_detalle_publico(self):
        codigo = self.programado.codigo_seguimiento
        detalle = reverse("core:detalle_envio", args=[codigo])
        self.assertEqual(detalle, "/rastreo/" + codigo + "/")
        self.assertRedirects(
            self.client.get(reverse("core:rastreo"), {"codigo": codigo}),
            detalle,
        )
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_detalle_publico_muestra_seguimiento_sin_datos_internos(self):
        respuesta = self.client.get(reverse(
            "core:detalle_envio", args=[self.programado.codigo_seguimiento],
        ))
        self.assertContains(respuesta, self.programado.codigo_seguimiento)
        self.assertContains(respuesta, self.programado.origen)
        self.assertContains(respuesta, self.programado.destino)
        self.assertContains(respuesta, self.programado.get_estado_display())
        for privado in (
            self.programado.observaciones, self.conductor_a.nombre,
            self.conductor_a.rut, self.conductor_a.telefono,
            self.vehiculo_a.patente,
        ):
            with self.subTest(dato=privado):
                self.assertNotContains(respuesta, privado)

    def test_codigos_desconocidos_o_invalidos_se_informan_sin_error_del_servidor(self):
        self.assertEqual(self.client.get(reverse(
            "core:detalle_envio", args=["MP-0000000000000000"],
        )).status_code, 404)
        for codigo in ("MP-0000000000000000", "x" * 200, "' OR 1=1 --", "<script>alert(1)</script>"):
            with self.subTest(codigo=codigo):
                respuesta = self.client.get(reverse("core:rastreo"), {"codigo": codigo})
                self.assertEqual(respuesta.status_code, 200)
                self.assertTrue(respuesta.context["error"])
                self.assertContains(respuesta, respuesta.context["error"])
                self.assertNotContains(respuesta, "<script>alert(1)</script>")

    def test_cambio_del_administrador_se_refleja_en_la_consulta_del_cliente(self):
        cliente_publico = Client()
        detalle = reverse("core:detalle_envio", args=[self.programado.codigo_seguimiento])
        self.assertContains(cliente_publico.get(detalle), "Programado")
        self.client.force_login(self.administrador)
        respuesta = self.client.post(
            reverse("core:viaje_editar", args=[self.programado.pk]),
            self.datos_viaje(
                origen=self.programado.origen,
                destino=self.programado.destino,
                fecha_salida="2026-11-01T08:00",
                fecha_llegada="2026-11-01T10:00",
                estado="finalizado",
                observaciones=self.programado.observaciones,
            ),
        )
        self.assertRedirects(respuesta, reverse("core:viajes"))
        self.programado.refresh_from_db()
        self.assertEqual(self.programado.estado, "finalizado")
        self.assertContains(cliente_publico.get(detalle), "Finalizado")
        self.assertNotIn("_auth_user_id", cliente_publico.session)
