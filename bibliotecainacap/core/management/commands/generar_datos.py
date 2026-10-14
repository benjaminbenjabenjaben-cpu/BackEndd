"""Genera despachos ficticios en SQLite para la evaluación de Django Admin."""
from datetime import timedelta
from decimal import Decimal
from time import perf_counter
from uuid import uuid4

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from faker import Faker

from core.models import Envio, HistorialSeguimiento
from core.services import ESTADOS


class Command(BaseCommand):
    help = "Crea entre 1 y 1.000.000 de envíos ficticios y sus eventos de seguimiento."

    def add_arguments(self, parser):
        parser.add_argument("cantidad", type=int, help="Cantidad de envíos nuevos.")

    def handle(self, *args, **options):
        cantidad = options["cantidad"]
        if not 1 <= cantidad <= 1_000_000:
            raise CommandError("La cantidad debe estar entre 1 y 1.000.000 de envíos.")

        inicio = perf_counter()
        fake = Faker("es_CL")
        prefijo = "MP-" + uuid4().hex[:8].upper()
        tamano_lote = 1000
        ahora = timezone.now()
        estados = [codigo for codigo, _ in ESTADOS]
        equipos = ["Guitarras Fender", "Consolas Pioneer DJ", "Sistema de sonido JBL",
                   "Teclados Yamaha", "Micrófonos Shure", "Batería acústica Pearl"]

        # Distintos despachos pueden repetir cliente, destino y conductor.
        # Faker genera un catálogo acotado para no crear un millón de direcciones.
        destinos = [
            (fake.company()[:80], fake.street_address()[:150],
             f"cliente{i}@musicpro.test", fake.numerify(text="+569########"))
            for i in range(min(cantidad, 1000))
        ]
        conductores = [
            (fake.name()[:80], fake.bothify("??-??-##").upper()) for _ in range(20)
        ]
        total_eventos = 0
        self.stdout.write(f"Carga {prefijo}: {cantidad} envíos nuevos.")
        self.stdout.flush()

        # Toda la carga se confirma al final; un error revierte sus inserciones.
        with transaction.atomic():
            for desde in range(0, cantidad, tamano_lote):
                hasta = min(desde + tamano_lote, cantidad)
                envios = []
                for numero in range(desde + 1, hasta + 1):
                    destinatario, destino, cliente, telefono = fake.random_element(destinos)
                    estado = fake.random_element(estados)
                    conductor, patente = fake.random_element(conductores)
                    envios.append(Envio(
                        codigo=f"{prefijo}-{numero:07d}", estado=estado,
                        destinatario=destinatario, telefono=telefono,
                        origen="Bodega Central · Quilicura",
                        destino=destino, equipo=fake.random_element(equipos),
                        bultos=fake.random_int(min=1, max=100),
                        peso=Decimal(fake.random_int(min=1, max=30000)) / Decimal("10"),
                        prioridad=fake.random_element(["normal", "alta"]), cliente=cliente,
                        conductor="" if estado == "bodega" else conductor,
                        patente="" if estado == "bodega" else patente,
                        eta="Entregado" if estado == "recibido" else "Por programar",
                    ))
                Envio.objects.bulk_create(envios, batch_size=tamano_lote)

                eventos = []
                for envio in envios:
                    fecha = ahora - timedelta(days=fake.random_int(min=1, max=30))
                    for paso, (estado, titulo) in enumerate(ESTADOS):
                        eventos.append(HistorialSeguimiento(
                            envio=envio, estado=estado, titulo=titulo,
                            nota="Evento ficticio generado para la evaluación.",
                            fecha=fecha + timedelta(hours=paso),
                        ))
                        if estado == envio.estado:
                            break
                HistorialSeguimiento.objects.bulk_create(eventos, batch_size=tamano_lote)
                total_eventos += len(eventos)
                if hasta % 10000 == 0 or hasta == cantidad:
                    self.stdout.write(f"Procesados {hasta}/{cantidad} envíos.")
                    self.stdout.flush()

            guardados = Envio.objects.filter(codigo__startswith=prefijo + "-").count()
            historial_guardado = HistorialSeguimiento.objects.filter(
                envio__codigo__startswith=prefijo + "-",
            ).count()
            if guardados != cantidad or historial_guardado != total_eventos:
                raise CommandError("La verificación no coincide; se cancela esta carga.")

        self.stdout.write(self.style.SUCCESS(
            f"Guardados y verificados: {guardados} envíos y {historial_guardado} eventos. "
            f"Tiempo: {perf_counter() - inicio:.2f} segundos."
        ))
        self.stdout.write(f"Código de ejemplo: {prefijo}-0000001")
