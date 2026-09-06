def portal(request):
    return {"usuario_demo": request.session.get("usuario"), "nombre_sitio": "Music Pro Courier"}
