from .models import UserLimit
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.shortcuts import redirect
from functools import wraps

def usuario_principal_required(view_func):
    """
    Decorator que permite acesso apenas a usuários principais
    VERIFICA se o usuário tem permissão para criar colaboradores
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if hasattr(request.user, 'colaborador'):
            messages.error(request, "Acesso restrito ao usuário principal.")
            return redirect('dashboard')
        
        try:
            from .models import UserLimit
            user_limit = UserLimit.objects.get(user=request.user)
            if user_limit.can_create_users:
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, "Acesso restrito a usuários principais.")
                return redirect('dashboard')
                
        except UserLimit.DoesNotExist:
            # Se não existe UserLimit, cria um com permissão (para usuários principais)
            user_limit = UserLimit.objects.create(
                user=request.user,
                max_users=2,
                can_create_users=True
            )
            return view_func(request, *args, **kwargs)
            
    return wrapper

def colaborador_tem_permissao(modulo, acao='ver'):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Usuários principais têm acesso total
            if not hasattr(request.user, 'colaborador'):
                return view_func(request, *args, **kwargs)
            
            # Colaboradores precisam de permissão
            try:
                permissao = request.user.colaborador.permissoes.get(modulo=modulo)
                if getattr(permissao, f'pode_{acao}', False):
                    return view_func(request, *args, **kwargs)
                else:
                    messages.error(request, f"Você não tem permissão para acessar {modulo}.")
                    return redirect('dashboard')
            except:
                messages.error(request, "Permissão não configurada.")
                return redirect('dashboard')
        return wrapper
    return decorator