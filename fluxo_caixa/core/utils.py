from django.contrib.auth.models import User
from colaborador.models import Colaborador

def get_usuario_referencia(request):
    """
    Retorna o usuário de referência para queries.
    Para colaboradores, retorna o usuario_principal.
    Para usuários normais, retorna o próprio usuário.
    """
    try:
        # Verificar se o usuário é um colaborador ativo
        colaborador = Colaborador.objects.get(
            usuario_colaborador=request.user, 
            ativo=True
        )
        return colaborador.usuario_principal
    except Colaborador.DoesNotExist:
        return request.user