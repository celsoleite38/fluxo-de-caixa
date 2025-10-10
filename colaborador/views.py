from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.db.models import Count
from django.utils import timezone
from .models import UserLimit, UserCreationRequest, Colaborador, PermissaoColaborador
from .forms import CustomUserCreationForm
from django.contrib.auth.models import User
from .decorators import usuario_principal_required
def is_admin(user):
    return user.is_superuser

@login_required
@usuario_principal_required
def colaborador_list(request):
    user_limit, created = UserLimit.objects.get_or_create(
        user=request.user,
        defaults={'max_users': 2, 'can_create_users': True}
    )
    
    # AGORA CORRETO: Buscar apenas colaboradores associados ao usuário atual
    colaboradores = Colaborador.objects.filter(
        usuario_principal=request.user,
        ativo=True
    )

    vagas_disponiveis = max(0, user_limit.max_users - colaboradores.count())
    
    context = {
        'colaboradores': colaboradores,
        'user_limit': user_limit,
        'vagas_disponiveis': vagas_disponiveis
    }
    return render(request, 'colaborador_list.html', context)

@login_required
@usuario_principal_required
def colaborador_create(request):
    user_limit, created = UserLimit.objects.get_or_create(
        user=request.user,
        defaults={'max_users': 2, 'can_create_users': True}
    )
    
    if not user_limit.can_create_users:
        messages.error(request, 'Você não tem permissão para criar novos colaboradores.')
        return redirect('colaborador:colaborador_list')
    
    # Contar colaboradores reais
    current_users_count = Colaborador.objects.filter(
        usuario_principal=request.user,
        ativo=True
    ).count()
    
    if current_users_count >= user_limit.max_users:
        messages.error(request, f'Limite máximo de {user_limit.max_users} colaboradores atingido.')
        return redirect('colaborador:request_more_users')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # AGORA IMPORTANTE: Criar o registro de colaborador
            Colaborador.objects.create(
                usuario_principal=request.user,
                usuario_colaborador=user,
                ativo=True
            )
            
            messages.success(request, f'Colaborador {user.username} criado com sucesso!')
            return redirect('colaborador:colaborador_list')
    else:
        form = CustomUserCreationForm()
    
    remaining = user_limit.max_users - current_users_count
    return render(request, 'colaborador_form.html', {
        'form': form, 
        'title': 'Adicionar Colaborador',
        'remaining': remaining
    })

@login_required
@usuario_principal_required
def colaborador_edit(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Colaborador {user.username} atualizado com sucesso!')
            return redirect('colaborador:colaborador_list')
    else:
        form = CustomUserCreationForm(instance=user)
    
    return render(request, 'colaborador_form.html', {
        'form': form, 
        'title': 'Editar Colaborador'
    })

@login_required
@usuario_principal_required
def colaborador_delete(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'Colaborador {username} excluído com sucesso!')
        return redirect('colaborador:colaborador_list')
    
    return render(request, 'colaborador/colaborador_confirm_delete.html', {'user': user})

@login_required
def request_more_users(request):
    user_limit = UserLimit.objects.get(user=request.user)
    
    if request.method == 'POST':
        additional_users = int(request.POST.get('additional_users', 1))
        
        UserCreationRequest.objects.create(
            user=request.user,
            additional_users_requested=additional_users
        )
        
        messages.success(request, 'Solicitação enviada para o administrador.')
        return redirect('colaborador:colaborador_list')
    
    return render(request, 'colaborador/request_more_users.html', {
        'user_limit': user_limit
    })

@login_required
@user_passes_test(is_admin)
def user_requests(request):
    requests = UserCreationRequest.objects.filter(approved=False)
    return render(request, 'colaborador/admin/user_requests.html', {'requests': requests})

@login_required
@user_passes_test(is_admin)
def approve_request(request, request_id):
    user_request = get_object_or_404(UserCreationRequest, id=request_id)
    
    if request.method == 'POST':
        user_request.approved = True
        user_request.approved_by = request.user
        user_request.approved_at = timezone.now()
        user_request.save()
        
        user_limit = UserLimit.objects.get(user=user_request.user)
        user_limit.max_users += user_request.additional_users_requested
        user_limit.save()
        
        messages.success(request, f'Limite de {user_request.user.username} aumentado para {user_limit.max_users} usuários.')
        return redirect('colaborador:user_requests')
    
    return render(request, 'colaborador/admin/approve_request.html', {'user_request': user_request})

from colaborador.decorators import colaborador_tem_permissao

@login_required
@colaborador_tem_permissao('vendas', 'ver')
def vendas(request):
    # Lógica de vendas - colaboradores podem acessar se tiverem permissão
    vendas = Venda.objects.filter(empresa=request.user.colaborador.empresa)
    return render(request, 'core/vendas.html', {'vendas': vendas})

@login_required
@colaborador_tem_permissao('estoque', 'ver')
def estoque(request):
    # Lógica de estoque - colaboradores podem acessar se tiverem permissão
    estoque = Produto.objects.filter(empresa=request.user.colaborador.empresa)
    return render(request, 'core/estoque.html', {'estoque': estoque})

@login_required
@usuario_principal_required
def gerenciar_permissoes(request, colaborador_id=None):
    """
    View para o usuário principal gerenciar permissões dos colaboradores
    """
    if colaborador_id:
        # Gerenciar permissões de um colaborador específico
        colaborador = get_object_or_404(Colaborador, id=colaborador_id, usuario_principal=request.user)
        return gerenciar_permissoes_colaborador(request, colaborador)
    else:
        # Listar todos os colaboradores para gerenciamento
        colaboradores = Colaborador.objects.filter(usuario_principal=request.user, ativo=True)
        return render(request, 'listar_para_permissoes.html', {
            'colaboradores': colaboradores
        })

def gerenciar_permissoes_colaborador(request, colaborador):
    if request.method == 'POST':
        # Processar o formulário de permissões
        for modulo, modulo_nome in PermissaoColaborador.MODULOS_CHOICES:
            permissao, created = PermissaoColaborador.objects.get_or_create(
                colaborador=colaborador,
                modulo=modulo
            )
            permissao.pode_ver = request.POST.get(f'{modulo}_ver') == 'on'
            permissao.pode_editar = request.POST.get(f'{modulo}_editar') == 'on'
            permissao.pode_excluir = request.POST.get(f'{modulo}_excluir') == 'on'
            permissao.save()
        
        messages.success(request, f"Permissões de {colaborador.usuario_colaborador.username} atualizadas!")
        return redirect('colaborador:gerenciar_permissoes')
    
    # PREPARAR OS DADOS PARA O TEMPLATE (Solução 2)
    permissoes_dict = {}
    for permissao in colaborador.permissoes.all():
        permissoes_dict[permissao.modulo] = permissao
    
    modulos_com_permissoes = []
    for modulo_valor, modulo_nome in PermissaoColaborador.MODULOS_CHOICES:
        permissao = permissoes_dict.get(modulo_valor)
        modulos_com_permissoes.append({
            'valor': modulo_valor,
            'nome': modulo_nome,
            'permissao': permissao
        })
    
    return render(request, 'gerenciar_permissoes.html', {
        'colaborador': colaborador,
        'modulos_com_permissoes': modulos_com_permissoes
    })