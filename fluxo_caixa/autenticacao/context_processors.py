from .models import PerfilProfissional

def perfil_profissional(request):
    if request.user.is_authenticated:
        perfil = PerfilProfissional.objects.filter(usuario=request.user).first()
        return {'perfil': perfil}
    return {'perfil': None}
