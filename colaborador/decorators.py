from .models import UserLimit
from django.contrib import messages
from django.shortcuts import redirect
from functools import wraps

def usuario_principal_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if hasattr(request.user, 'pertence_a'):
            messages.error(request, "Acesso restrito ao usuário principal.")
            return redirect('dashboard')
        
        try:
            user_limit = UserLimit.objects.get(user=request.user)
            if user_limit.can_create_users:
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, "Acesso restrito a usuários principais.")
                return redirect('dashboard')
                
        except UserLimit.DoesNotExist:
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
            if not request.user.is_authenticated:
                return redirect('login')

            if not hasattr(request.user, 'pertence_a'):
                return view_func(request, *args, **kwargs)
            
            try:
                permissao = request.user.pertence_a.permissoes.get(modulo=modulo)
                if getattr(permissao, f'pode_{acao}', False):
                    return view_func(request, *args, **kwargs)
                else:
                    messages.error(request, f"Você não tem permissão para {acao} no módulo {modulo}.")
                    return redirect('dashboard')
            except Exception:
                messages.error(request, f"Você não tem permissão para acessar {modulo}.")
                return redirect('dashboard')
        return wrapper
    return decorator
