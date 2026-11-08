"""Modelos de despachos y de transporte."""
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from .services import ESTADOS


class Envio(models.Model):
    """Información de un despacho de instrumentos o equipos."""

    codigo = models.CharField("código", max_length=20, unique=True)
    estado = models.CharField(max_length=10, choices=ESTADOS, default="bodega")
    destinatario = models.CharField(max_length=80)
    telefono = models.CharField("teléfono de contacto", max_length=12, blank=True)
    origen = models.CharField("origen", max_length=150)
    destino = models.CharField("dirección de destino", max_length=150)
    equipo = models.CharField("instrumentos o equipos", max_length=120)
    bultos = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    peso = models.DecimalField(
        "peso en kg", max_digits=7, decimal_places=1,
        validators=[MinValueValidator(Decimal("0.1"))],
    )
    prioridad = models.CharField(
        max_length=6, choices=[("normal", "Normal"), ("alta", "Alta")],
        default="normal",
    )
    conductor = models.CharField(max_length=80, blank=True)
    patente = models.CharField(max_length=12, blank=True)
    eta = models.CharField("estimación de entrega", max_length=80, blank=True)
    cliente = models.EmailField("correo del cliente")

    class Meta:
        verbose_name = "envío"
        verbose_name_plural = "envíos"

    def __str__(self):
        return f"{self.codigo} - {self.destinatario}"


class HistorialSeguimiento(models.Model):
    """Cada registro representa una etapa del recorrido de un envío."""

    envio = models.ForeignKey(
        Envio, on_delete=models.CASCADE, related_name="historial",
        verbose_name="envío",
    )
    estado = models.CharField(max_length=10, choices=ESTADOS)
    titulo = models.CharField("título", max_length=120)
    nota = models.TextField(blank=True)
    fecha = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        verbose_name = "evento de seguimiento"
        verbose_name_plural = "historial de seguimiento"
        ordering = ["fecha", "id"]

    def __str__(self):
        return f"{self.get_estado_display()} - {self.titulo}"


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
