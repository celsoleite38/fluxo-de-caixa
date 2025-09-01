from django.shortcuts import redirect
from django.contrib import messages
from django.urls import resolve

class BloqueioColaboradorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # URLs que colaboradores NÃO podem acessar
        urls_proibidas = [
            'colaborador_list', 'colaborador_create', 
            'colaborador_edit', 'colaborador_delete',
            'gerenciar_permissoes', 'gestao_empresa'
        ]
        
        if request.user.is_authenticated:
            # Verifica se é colaborador
            if hasattr(request.user, 'colaborador'):
                resolved = resolve(request.path_info)
                if resolved.url_name in urls_proibidas:
                    messages.error(request, "Acesso restrito ao usuário principal.")
                    return redirect('dashboard')
        
        return self.get_response(request)