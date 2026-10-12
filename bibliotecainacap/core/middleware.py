"""Acceso sin contraseña al administrador para la presentación local."""
from django.conf import settings
from django.contrib.auth import get_user_model


def admin_local_sin_contrasena(get_response):
    def middleware(request):
        if (
            settings.DEBUG
            and request.META.get("REMOTE_ADDR") in ("127.0.0.1", "::1")
            and request.path.startswith("/admin/")
        ):
            # Usa el superadministrador existente; no crea cuentas nuevas.
            administrador = get_user_model().objects.filter(
                is_superuser=True, is_staff=True, is_active=True,
            ).first()
            if administrador is not None:
                request.user = administrador
        return get_response(request)

    return middleware
