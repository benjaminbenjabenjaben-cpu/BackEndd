"""Seeder de envíos: genera datos con Faker y guarda cada registro."""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from faker import Faker

from core.models import Envio, HistorialSeguimiento
from core.services import ESTADOS


class Command(BaseCommand):
    help = "Genera envíos de prueba y su historial con Faker."

    def add_arguments(self, parser):
        parser.add_argument("cantidad", type=int)

    def handle(self, *args, **options):
        cantidad = options["cantidad"]
        if not 1 <= cantidad <= 1_000_000:
            raise CommandError("La cantidad debe estar entre 1 y 1.000.000 de envíos.")

        fake = Faker("es_CL")
        self.stdout.write(f"Generando {cantidad} envíos de prueba...")
        total_eventos = 0

        # Confirma la carga al terminar y la revierte si ocurre un error.
        with transaction.atomic():
            for i in range(cantidad):
                estado_envio = fake.random_element(["bodega", "enviado", "camino", "recibido"])
                envio = Envio.objects.create(
                    codigo="MP-" + str(fake.unique.random_int(
                        min=1_000_000_000_000_000, max=9_999_999_999_999_999,
                    )),
                    estado=estado_envio,
                    destinatario=fake.name(),
                    telefono=fake.numerify(text="+569########"),
                    origen="Bodega Central · Quilicura",
                    destino=fake.street_address(),
                    equipo=fake.random_element(["Guitarra", "Teclado", "Batería", "Micrófono"]),
                    bultos=fake.random_int(min=1, max=100),
                    peso=fake.pydecimal(min_value=1, max_value=3000, right_digits=1),
                    prioridad=fake.random_element(["normal", "alta"]),
                    conductor=fake.name() if estado_envio != "bodega" else "",
                    patente=fake.bothify(text="??-??-##").upper() if estado_envio != "bodega" else "",
                    eta="Entregado" if estado_envio == "recibido" else "Por programar",
                    cliente=fake.safe_email(),
                )

                # Cada evento se relaciona con el envío que acabamos de crear.
                for estado, titulo in ESTADOS:
                    HistorialSeguimiento.objects.create(
                        envio=envio,
                        estado=estado,
                        titulo=titulo,
                        nota="Evento de prueba generado con Faker.",
                    )
                    total_eventos += 1
                    if estado == estado_envio:
                        break

                if (i + 1) % 10000 == 0:
                    self.stdout.write(f"Procesados {i + 1}/{cantidad} envíos.")

        self.stdout.write(self.style.SUCCESS(
            f"Se crearon {cantidad} envíos y {total_eventos} eventos correctamente."
        ))
        self.stdout.write(f"Código de ejemplo: {envio.codigo}")
