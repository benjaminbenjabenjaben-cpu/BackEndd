"""Modelos de los despachos y sus eventos de seguimiento."""
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
