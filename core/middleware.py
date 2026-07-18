from django.shortcuts import redirect
from django.urls import resolve, reverse


class VerificacaoEmailMiddleware:
    URLS_EXCLUIDAS = [
        'login', 'logout', 'register', 'admin:login', 'admin:logout',
        'ativar_conta', 'reenviar_ativacao', 'verificar_email',
        'solicitar_reset_senha', 'reset_senha_confirmar', 'reset_senha_completo',
        'password_change', 'password_change_done',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            resolved = resolve(request.path_info)
            if resolved.url_name not in self.URLS_EXCLUIDAS:
                perfil = getattr(request.user, 'perfil', None)
                if not perfil or not perfil.email_verificado:
                    return redirect('verificar_email')

        return self.get_response(request)
