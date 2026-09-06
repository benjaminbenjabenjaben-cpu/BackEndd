from decimal import Decimal

from django import forms

ESTADOS = [("bodega", "En bodega"), ("enviado", "Enviado"), ("camino", "En camino"), ("recibido", "Recibido")]


class FormularioEstilizado(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs["class"] = "form-check-input" if isinstance(field.widget, forms.CheckboxInput) else "form-select" if isinstance(field.widget, forms.Select) else "form-control"


class AccesoForm(FormularioEstilizado):
    correo = forms.EmailField(label="Correo electrónico", max_length=100, widget=forms.EmailInput(attrs={"placeholder": "tu@correo.cl", "autocomplete": "username"}))
    contrasena = forms.CharField(label="Contraseña", max_length=128, strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))


class RegistroForm(FormularioEstilizado):
    nombre = forms.CharField(label="Nombre completo", min_length=3, max_length=80, widget=forms.TextInput(attrs={"autocomplete": "name"}))
    correo = forms.EmailField(label="Correo electrónico", max_length=100, widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    contrasena = forms.CharField(label="Contraseña", min_length=10, max_length=128, strip=False, help_text="Al menos 10 caracteres, con letras y números.", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    confirmar = forms.CharField(label="Repite tu contraseña", max_length=128, strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    aceptar = forms.BooleanField(label="Entiendo que esta cuenta es temporal y usaré datos ficticios.")

    def clean_contrasena(self):
        value = self.cleaned_data["contrasena"]
        if not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
            raise forms.ValidationError("Incluye al menos una letra y un número.")
        return value

    def clean(self):
        data = super().clean()
        if data.get("contrasena") and data.get("contrasena") != data.get("confirmar"):
            self.add_error("confirmar", "Las contraseñas no coinciden.")
        return data


class RastreoForm(FormularioEstilizado):
    codigo = forms.RegexField(label="Código de seguimiento", regex=r"^MP-2026-[A-Z0-9]{3,12}$", max_length=20, error_messages={"invalid": "Usa un código como MP-2026-001."}, widget=forms.TextInput(attrs={"placeholder": "MP-2026-001", "autocomplete": "off"}))

    def __init__(self, data=None, *args, **kwargs):
        if data is not None:
            data = data.copy()
            data["codigo"] = data.get("codigo", "").strip().upper()
        super().__init__(data, *args, **kwargs)


class EnvioForm(FormularioEstilizado):
    cliente = forms.EmailField(label="Correo del cliente", max_length=100)
    destinatario = forms.CharField(label="Destinatario o sucursal", max_length=80)
    origen = forms.ChoiceField(label="Origen", choices=[("Bodega Central · Quilicura", "Bodega Central · Quilicura"), ("Sucursal Providencia", "Sucursal Providencia")])
    destino = forms.CharField(label="Dirección de destino", min_length=5, max_length=150)
    equipo = forms.CharField(label="Instrumentos o equipos", max_length=120)
    bultos = forms.IntegerField(label="Cantidad de bultos", min_value=1, max_value=100)
    peso = forms.DecimalField(label="Peso total (kg)", min_value=Decimal("0.1"), max_value=Decimal("3000"), max_digits=6, decimal_places=1)
    prioridad = forms.ChoiceField(label="Prioridad", choices=[("normal", "Normal"), ("alta", "Alta")])


class EstadoForm(FormularioEstilizado):
    estado = forms.ChoiceField(label="Siguiente estado", choices=ESTADOS)
    nota = forms.CharField(label="Nota de seguimiento", min_length=5, max_length=180, help_text="Describe el hito del despacho. No incluyas datos personales.", widget=forms.Textarea(attrs={"rows": 3}))
