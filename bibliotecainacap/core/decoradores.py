"""Comprueba el perfil en el servidor, además de proteger el inicio de sesión."""
from functools import wraps

from django.core.exceptions import PermissionDenied


def es_administrador(usuario):
    return usuario.is_authenticated and (
        usuario.is_superuser or usuario.groups.filter(name="Administrador").exists()
    )


def administrador_requerido(vista):
    @wraps(vista)
    def comprobar(request, *args, **kwargs):
        if not es_administrador(request.user):
            raise PermissionDenied("Esta operación requiere el perfil Administrador.")
        return vista(request, *args, **kwargs)
    return comprobar
