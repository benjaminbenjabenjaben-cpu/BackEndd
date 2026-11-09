"""Los cuatro modelos del sistema de Transporte."""
from uuid import uuid4

from django.db import models


def generar_codigo_seguimiento():
    return "MP-" + uuid4().hex[:16].upper()


class TipoVehiculo(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    descripcion = models.TextField("descripción", blank=True)

    class Meta:
        verbose_name = "tipo de vehículo"
        verbose_name_plural = "tipos de vehículo"

    def __str__(self):
        return self.nombre


class Vehiculo(models.Model):
    tipo_vehiculo = models.ForeignKey(
        TipoVehiculo, on_delete=models.PROTECT, related_name="vehiculos",
        verbose_name="tipo de vehículo",
    )
    patente = models.CharField(max_length=15, unique=True)
    marca = models.CharField(max_length=80)
    modelo = models.CharField(max_length=80)
    anio = models.IntegerField("año")
    disponible = models.BooleanField(default=True)
    estado = models.CharField(max_length=25, default="operativo")

    class Meta:
        verbose_name = "vehículo"
        verbose_name_plural = "vehículos"

    def __str__(self):
        return f"{self.patente} - {self.marca} {self.modelo}"


class Conductor(models.Model):
    rut = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=150)
    licencia = models.CharField(max_length=30)
    telefono = models.CharField("teléfono", max_length=30, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "conductor"
        verbose_name_plural = "conductores"

    def __str__(self):
        return f"{self.rut} - {self.nombre}"


class Viaje(models.Model):
    ESTADOS = [
        ("programado", "Programado"),
        ("en_curso", "En curso"),
        ("finalizado", "Finalizado"),
        ("cancelado", "Cancelado"),
    ]

    codigo_seguimiento = models.CharField(
        "código de seguimiento", max_length=20, unique=True,
        default=generar_codigo_seguimiento, editable=False,
    )
    vehiculo = models.ForeignKey(
        Vehiculo, on_delete=models.PROTECT, related_name="viajes",
        verbose_name="vehículo",
    )
    conductor = models.ForeignKey(
        Conductor, on_delete=models.PROTECT, related_name="viajes",
    )
    origen = models.CharField(max_length=150)
    destino = models.CharField(max_length=150)
    fecha_salida = models.DateTimeField("fecha de salida")
    fecha_llegada = models.DateTimeField("fecha de llegada", null=True, blank=True)
    estado = models.CharField(max_length=25, choices=ESTADOS, default="programado")
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = "viaje"
        verbose_name_plural = "viajes"

    def __str__(self):
        return f"{self.origen} → {self.destino} ({self.vehiculo.patente})"
