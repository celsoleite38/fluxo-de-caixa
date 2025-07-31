
# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib import messages
from django.db.models import Sum
from datetime import datetime, timedelta, timezone
from .forms import CategoriaForm, EntradaEstoqueForm, UsuarioForm, CustomPasswordChangeForm, MovimentacaoForm, ProdutoForm, NotaVendaForm, ItemVendaForm, CategoriaForm
from .models import ItemVenda, Movimentacao, Categoria, Produto, NotaVenda, MovimentoEstoque
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import models
#from fluxo_caixa.core import models
from django.utils import timezone 

from django.views.decorators.http import require_POST
from django.contrib.auth.forms import PasswordChangeForm
#from dateutil.relativedelta import relativedelta
from django.template.loader import render_to_string
from django.http import HttpResponse

import uuid

@login_required
def dashboard(request):
    hoje = datetime.now().date()
    inicio_mes = hoje.replace(day=1)
    
    # Entradas e saídas do mês
    entradas_mes = Movimentacao.objects.filter(
        tipo='E', 
        data__gte=inicio_mes,
        usuario=request.user
    ).aggregate(total=Sum('valor'))['total'] or 0
    
    saidas_mes = Movimentacao.objects.filter(
        tipo='S', 
        data__gte=inicio_mes,
        usuario=request.user
    ).aggregate(total=Sum('valor'))['total'] or 0
    
    saldo_mes = entradas_mes - saidas_mes
    
    # Últimas movimentações
    ultimas_movimentacoes = Movimentacao.objects.filter(
        usuario=request.user,
        data__gte=hoje - timedelta(days=1)
    ).order_by('-data' )[:10]
    
    # Produtos com baixo estoque
    produtos_baixo_estoque = Produto.objects.filter(quantidade__lte=5)
    
    context = {
        'entradas_mes': entradas_mes,
        'saidas_mes': saidas_mes,
        'saldo_mes': saldo_mes,
        'ultimas_movimentacoes': ultimas_movimentacoes,
        'produtos_baixo_estoque': produtos_baixo_estoque,
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def lista_movimentacoes(request, tipo):
    movimentacoes = Movimentacao.objects.filter(
        tipo=tipo,
        usuario=request.user
    ).order_by('-data')
    
    total = movimentacoes.aggregate(total=Sum('valor'))['total'] or 0
    
    context = {
        'movimentacoes': movimentacoes,
        'total': total,
        'tipo': tipo,
        'titulo': 'Entradas' if tipo == 'E' else 'Saídas'
    }
    return render(request, 'core/entrada_list.html' if tipo == 'E' else 'core/saida_list.html', context)

@login_required
def adicionar_movimentacao(request):
    if request.method == 'POST':
        form = MovimentacaoForm(request.POST)
        if form.is_valid():
            movimentacao = form.save(commit=False)
            movimentacao.usuario = request.user
            movimentacao.save()
            messages.success(request, 'Movimentação adicionada com sucesso!')
            return redirect('dashboard')
    else:
        form = MovimentacaoForm()
    
    return render(request, 'core/movimentacao_form.html', {'form': form})

@login_required
def editar_movimentacao(request, pk):
    movimentacao = get_object_or_404(Movimentacao, pk=pk, usuario=request.user)
    if request.method == 'POST':
        form = MovimentacaoForm(request.POST, instance=movimentacao)
        if form.is_valid():
            form.save()
            messages.success(request, 'Movimentação atualizada com sucesso!')
            return redirect('dashboard')
    else:
        form = MovimentacaoForm(instance=movimentacao)
    
    return render(request, 'core/movimentacao_form.html', {'form': form})

@login_required
def excluir_movimentacao(request, pk):
    movimentacao = get_object_or_404(Movimentacao, pk=pk, usuario=request.user)
    if request.method == 'POST':
        movimentacao.delete()
        messages.success(request, 'Movimentação excluída com sucesso!')
        return redirect('dashboard')
    return render(request, 'core/confirmar_remocao_item.html', {'object': movimentacao})



@login_required
def relatorios(request):
    # Filtros para Movimentações
    movimentacoes = Movimentacao.objects.filter(usuario=request.user)
    
    # Filtros para Vendas (Novo)
    vendas = NotaVenda.objects.filter(usuario=request.user).prefetch_related('itemvenda_set')
    
    # Tratamento dos filtros (compartilhado)
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    if data_inicio:
        try:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            movimentacoes = movimentacoes.filter(data__gte=data_inicio)
            vendas = vendas.filter(data__gte=data_inicio)  # Novo
        except ValueError:
            messages.error(request, "Data início inválida")
    
    if data_fim:
        try:
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
            movimentacoes = movimentacoes.filter(data__lte=data_fim)
            vendas = vendas.filter(data__lte=data_fim)  # Novo
        except ValueError:
            messages.error(request, "Data fim inválida")

    # Cálculos para Movimentações
    total_entradas = movimentacoes.filter(tipo='E').aggregate(total=Sum('valor'))['total'] or 0
    total_saidas = movimentacoes.filter(tipo='S').aggregate(total=Sum('valor'))['total'] or 0
    saldo = total_entradas - total_saidas
    
    # Cálculos para Vendas (Novo)
    total_vendas = vendas.aggregate(total=Sum('total'))['total'] or 0
    qtd_vendas = vendas.count()
    
    context = {
        'movimentacoes': movimentacoes.order_by('-data'),
        'vendas': vendas.order_by('-data'),  # Novo
        'total_entradas': total_entradas,
        'total_saidas': total_saidas,
        'total_vendas': total_vendas,  # Novo
        'qtd_vendas': qtd_vendas,      # Novo
        'saldo': saldo,
        'data_inicio': request.GET.get('data_inicio', ''),
        'data_fim': request.GET.get('data_fim', ''),
    }
    return render(request, 'core/relatorios.html', context)

@login_required
def lista_produtos(request):
    produtos = Produto.objects.all()
    return render(request, 'core/estoque.html', {'produtos': produtos})

@login_required
def adicionar_produto(request):
    if request.method == 'POST':
        form = ProdutoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Produto adicionado com sucesso!')
            return redirect('estoque')
    else:
        form = ProdutoForm()
    
    return render(request, 'core/produto_form.html', {'form': form})

@login_required
@require_POST  # Garante que só aceita requisições POST
def excluir_produto(request, id):
    produto = get_object_or_404(Produto, id=id)
    
    try:
        produto.delete()
        messages.success(request, 'Produto excluído com sucesso!')
    except Exception as e:
        messages.error(request, f'Erro ao excluir produto: {str(e)}')
    
    return redirect('estoque')


@login_required
def editar_produto(request, id):
    produto = get_object_or_404(Produto, id=id)
    
    if request.method == 'POST':
        form = ProdutoForm(request.POST, instance=produto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Produto atualizado com sucesso!')
            return redirect('estoque')
    else:
        form = ProdutoForm(instance=produto)
    
    return render(request, 'core/produto_form.html', {'form': form, 'editar': True})

@login_required
def entrada_estoque(request, id):
    produto = get_object_or_404(Produto, id=id)
    
    if request.method == 'POST':
        form = EntradaEstoqueForm(request.POST)
        if form.is_valid():
            quantidade = form.cleaned_data['quantidade']
            produto.quantidade += quantidade
            produto.save()
            
            # Registrar o movimento no histórico (opcional)
            MovimentoEstoque.objects.create(
                produto=produto,
                quantidade=quantidade,
                tipo='entrada',
                usuario=request.user
            )
            
            messages.success(request, f'{quantidade} unidades adicionadas ao estoque com sucesso!')
            return redirect('estoque')
    else:
        form = EntradaEstoqueForm()
    
    return render(request, 'core/entrada_estoque.html', {
        'form': form,
        'produto': produto
    })



@login_required
def historico_estoque(request):
    # Filtra apenas as entradas (ou todos os movimentos)
    movimentos = MovimentoEstoque.objects.filter(tipo='entrada').order_by('-data')
    
    # Ou para ver todos os movimentos (entradas e saídas):
    # movimentos = MovimentoEstoque.objects.all().order_by('-data')
    
    return render(request, 'core/historico_estoque.html', {
        'movimentos': movimentos
    })


@login_required
def criar_nota_venda(request):
    if request.method == 'POST':
        form = NotaVendaForm(request.POST)
        if form.is_valid():
            nota = form.save(commit=False)
            nota.total = 0
            nota.usuario = request.user
            nota.save()
            return redirect('adicionar_item_venda', nota_id=nota.id)
    else:
        form = NotaVendaForm()
    
    return render(request, 'core/nota_venda_form.html', {'form': form})

@login_required
def adicionar_item_venda(request, nota_id):
    nota = get_object_or_404(NotaVenda, pk=nota_id, usuario=request.user)
    
    if request.method == 'POST':
        form = ItemVendaForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.nota = nota
            item.preco_unitario = item.produto.preco
            item.save()
            
            # Atualizar estoque
            produto = item.produto
            produto.quantidade -= item.quantidade
            produto.save()
            
            # Atualizar total da nota usando o property subtotal
            nota.total = sum(item.subtotal for item in nota.itemvenda_set.all())
            nota.save()
            
            messages.success(request, 'Item adicionado com sucesso!')
            return redirect('adicionar_item_venda', nota_id=nota.id)
    else:
        form = ItemVendaForm()
    
    # Carregar todos os produtos disponíveis para o select
    produtos = Produto.objects.filter(quantidade__gt=0)
    
    # Renomear para 'itens_venda' para evitar conflito com o loop do template
    itens_venda = nota.itemvenda_set.select_related('produto').all()
    
    return render(request, 'core/nota_venda.html', {
        'nota': nota,
        'form': form,
        'itens': itens_venda,  # Agora usando 'itens' que o template espera
        'produtos': produtos,
    })


@login_required
def finalizar_venda(request, nota_id):
    nota = get_object_or_404(NotaVenda, pk=nota_id, usuario=request.user)
    
    Movimentacao.objects.create(
        tipo='E',
        valor=nota.total,
        descricao=f"Venda para {nota.cliente}",
        data=datetime.now().date(),
        usuario=request.user
    )
    
    messages.success(request, 'Venda finalizada com sucesso!')
    return redirect('dashboard')



@login_required
def imprimir_recibo_venda(request, nota_id):
    nota = get_object_or_404(NotaVenda, pk=nota_id, usuario=request.user)
    
    context = {
        'nota': nota,
        'itens': nota.itemvenda_set.all(),
        'data_emissao': timezone.now(),
    }
    
    return render(request, 'core/recibo_impressao.html', context)

def register(request):
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Cadastro realizado com sucesso!')
            return redirect('dashboard')
    else:
        form = UsuarioForm()
    return render(request, 'registration/register.html', {'form': form})



@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Mantém o usuário logado
            messages.success(request, 'Sua senha foi alterada com sucesso!')
            return redirect('dashboard')
        else:
            # Adiciona mensagens de erro específicas
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Erro no campo '{field}': {error}")
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'registration/change_password.html', {
        'form': form,
        'title': 'Alterar Senha'
    })

def lista_entradas(request):
    movimentacoes = Movimentacao.objects.filter(
        tipo='E',
        usuario=request.user
    ).order_by('-data')
    
    total = movimentacoes.aggregate(total=Sum('valor'))['total'] or 0
    
    return render(request, 'core/entrada_list.html', {
        'movimentacoes': movimentacoes,
        'total': total
    })
    
def lista_saidas(request):
    movimentacoes = Movimentacao.objects.filter(
        tipo='S',
        usuario=request.user
    ).select_related('categoria').order_by('-data')
    
    total = movimentacoes.aggregate(total=Sum('valor'))['total'] or 0
    
    return render(request, 'core/saida_list.html', {
        'movimentacoes': movimentacoes,
        'total': total
    })
    
@receiver(post_save, sender=ItemVenda)
def atualizar_total_nota(sender, instance, **kwargs):
    nota = instance.nota
    nota.total = nota.itemvenda_set.aggregate(
        total=models.Sum(models.F('quantidade') * models.F('preco_unitario'))
    )['total'] or 0
    nota.save()
    
def minha_view(request):
    itens = item.objects.all()
    subtotal = 0
    for item in itens:
        subtotal += item.quantidade * item.preco_unitario
    return render(request, 'nota_venda.html', {'subtotal': subtotal})


@login_required
def remover_item_venda(request, pk):
    item = get_object_or_404(ItemVenda, pk=pk, nota__usuario=request.user)
    
    if request.method == 'POST':
        # Devolver a quantidade ao estoque
        produto = item.produto
        produto.quantidade += item.quantidade
        produto.save()
        
        # Remover o item e atualizar o total da nota
        nota = item.nota
        item.delete()
        
        # Recalcular o total da nota
        nota.total = sum(item.subtotal for item in nota.itemvenda_set.all())
        nota.save()
        
        messages.success(request, 'Item removido com sucesso!')
        return redirect('adicionar_item_venda', nota_id=nota.id)
    
    return render(request, 'core/confirmar_remocao_item.html', {'item': item})

@login_required
def user_logout(request):
    logout(request)
    return redirect('logout')
