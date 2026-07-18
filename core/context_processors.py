from .models import Perfil


def perfil_context(request):
    if request.user.is_authenticated:
        try:
            perfil = Perfil.objects.get(usuario=request.user)
        except Perfil.DoesNotExist:
            perfil = None
        return {'perfil_empresa': perfil}
    return {}


def permissoes_colaborador_context(request):
    if not request.user.is_authenticated:
        return {}

    if not hasattr(request.user, 'pertence_a'):
        return {'is_colaborador': False}

    try:
        colaborador = request.user.pertence_a
    except Exception:
        return {'is_colaborador': False}

    perm_modulos = {}
    for permissao in colaborador.permissoes.all():
        perm_modulos[permissao.modulo] = {
            'ver': permissao.pode_ver,
            'editar': permissao.pode_editar,
            'excluir': permissao.pode_excluir,
        }

    return {
        'is_colaborador': True,
        'perm_modulos': perm_modulos,
    }
