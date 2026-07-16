from .models import Perfil


def perfil_context(request):
    if request.user.is_authenticated:
        try:
            perfil = Perfil.objects.get(usuario=request.user)
        except Perfil.DoesNotExist:
            perfil = None
        return {'perfil_empresa': perfil}
    return {}
