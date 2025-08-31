
# Create your views here.
from django.db.models.aggregates import Count
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib import messages
from django.db.models import Sum
from datetime import datetime, timedelta, timezone, date
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
from django.http import HttpResponse, JsonResponse
from decimal import Decimal

import uuid

@login_required
def dashboard(request):
    hoje = date.today()
    inicio_mes = hoje.replace(day=1)
    
    # Movimentações do DIA (adicionado)
    movimentacoes_hoje = Movimentacao.objects.filter(
        usuario=request.user,
        data=hoje
    ).order_by('-data')
    
    # Totais do DIA (adicionado)
    entradas_hoje = movimentacoes_hoje.filter(tipo='E').aggregate(
        total=Sum('valor')
    )['total'] or 0
    
    saidas_hoje = movimentacoes_hoje.filter(tipo='S').aggregate(
        total=Sum('valor')
    )['total'] or 0
    
    saldo_hoje = entradas_hoje - saidas_hoje
    
    # Entradas e saídas do mês (mantido)
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
    
    # Vendas do DIA (adicionado - se aplicável)
    vendas_hoje = NotaVenda.objects.filter(
        usuario=request.user,
        data=hoje
    )
    
    total_vendas_hoje = vendas_hoje.aggregate(total=Sum('total'))['total'] or 0
    qtd_vendas_hoje = vendas_hoje.count()
    
    # Produtos com baixo estoque (mantido)
    produtos_baixo_estoque = Produto.objects.filter(quantidade__lte=5)
    
    context = {
        # Novos dados do dia
        'movimentacoes_hoje': movimentacoes_hoje,
        'entradas_hoje': entradas_hoje,
        'saidas_hoje': saidas_hoje,
        'saldo_hoje': saldo_hoje,
        'vendas_hoje': vendas_hoje,
        'total_vendas_hoje': total_vendas_hoje,
        'qtd_vendas_hoje': qtd_vendas_hoje,
        'data_hoje': hoje,
        
        # Dados do mês (mantidos)
        'entradas_mes': entradas_mes,
        'saidas_mes': saidas_mes,
        'saldo_mes': saldo_mes,
        
        # Outros dados
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
    entradas = movimentacoes.filter(tipo='E').order_by('-data')
    saidas = movimentacoes.filter(tipo='S').order_by('-data')
    
    # Filtros para Vendas - APENAS VENDAS FINALIZADAS
    vendas = NotaVenda.objects.filter(usuario=request.user, status='finalizada')
    
    # Tratamento dos filtros
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    forma_pagamento = request.GET.get('forma_pagamento', '')
    
    # Aplicar filtros de data
    if data_inicio:
        try:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            movimentacoes = movimentacoes.filter(data__gte=data_inicio)
            vendas = vendas.filter(data__gte=data_inicio)
        except ValueError:
            messages.error(request, "Data início inválida")
    
    if data_fim:
        try:
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
            movimentacoes = movimentacoes.filter(data__lte=data_fim)
            vendas = vendas.filter(data__lte=data_fim)
        except ValueError:
            messages.error(request, "Data fim inválida")

    # Aplicar filtro de forma de pagamento
    if forma_pagamento:
        vendas = vendas.filter(forma_pagamento=forma_pagamento)

    # Cálculos para Movimentações
    total_entradas = movimentacoes.filter(tipo='E').aggregate(total=Sum('valor'))['total'] or 0
    total_saidas = movimentacoes.filter(tipo='S').aggregate(total=Sum('valor'))['total'] or 0
    saldo = total_entradas - total_saidas
    
    # Cálculos para Vendas - CORRIGIDO
    # Usar total_com_desconto para o valor real recebido
    total_vendas = vendas.aggregate(total=Sum('total_com_desconto'))['total'] or 0
    total_vendas_bruto = vendas.aggregate(total=Sum('total'))['total'] or 0
    total_descontos = total_vendas_bruto - total_vendas
    qtd_vendas = vendas.count()
    
    # Estatísticas por forma de pagamento - CORRIGIDO
    # Primeiro pegar todas as vendas COM forma de pagamento
    vendas_com_forma = vendas.exclude(forma_pagamento__isnull=True)
    vendas_por_forma = vendas_com_forma.values('forma_pagamento').annotate(
        total=Sum('total_com_desconto'),
        quantidade=Count('id')
    ).order_by('-total')
    
    # Converter para lista para manipulação
    vendas_por_forma_list = list(vendas_por_forma)
    
    # Verificar vendas SEM forma de pagamento
    vendas_sem_forma = vendas.filter(forma_pagamento__isnull=True)
    if vendas_sem_forma.exists():
        total_sem_forma = vendas_sem_forma.aggregate(
            total=Sum('total_com_desconto'),
            quantidade=Count('id')
        )
        if total_sem_forma['quantidade'] > 0:
            vendas_por_forma_list.append({
                'forma_pagamento': None,
                'total': total_sem_forma['total'] or 0,
                'quantidade': total_sem_forma['quantidade'] or 0
            })
    
    context = {
        'movimentacoes': movimentacoes.order_by('-data'),
        'entradas': entradas,
        'saidas': saidas,  
        'vendas': vendas.order_by('-data'),
        'total_entradas': total_entradas,
        'total_saidas': total_saidas,
        'total_vendas': total_vendas,
        'total_descontos': total_descontos,
        'qtd_vendas': qtd_vendas,
        'saldo': saldo,
        'data_inicio': request.GET.get('data_inicio', ''),
        'data_fim': request.GET.get('data_fim', ''),
        'forma_pagamento': forma_pagamento,
        'vendas_por_forma_pagamento': vendas_por_forma_list,
        'FORMAS_PAGAMENTO': NotaVenda.FORMA_PAGAMENTO_CHOICES,
    }
    return render(request, 'core/relatorios.html', context)

# caixa/views.py


def imprimir_entradas(request):
    # Use Movimentacao filtrando por tipo 'E' (Entrada)
    entradas = Movimentacao.objects.filter(tipo='E', usuario=request.user).order_by("-data")
    total = entradas.aggregate(total=Sum('valor'))['total'] or 0
    
    return render(request, "core/imprimir_entradas.html", {
        "entradas": entradas,
        "total": total
    })

def imprimir_saidas(request):
    # Use Movimentacao filtrando por tipo 'S' (Saída)
    saidas = Movimentacao.objects.filter(tipo='S', usuario=request.user).order_by("-data")
    total = saidas.aggregate(total=Sum('valor'))['total'] or 0
    
    return render(request, "core/imprimir_saidas.html", {
        "saidas": saidas,
        "total": total
    })


@login_required
def lista_produtos(request):
    produtos = Produto.objects.filter(usuario=request.user)
    return render(request, 'core/estoque.html', {'produtos': produtos})

@login_required
def adicionar_produto(request):
    if request.method == 'POST':
        form = ProdutoForm(request.POST)
        if form.is_valid():
            produto = form.save(commit=False)
            produto.usuario = request.user
            produto.save()
            messages.success(request, 'Produto adicionado com sucesso!')
            return redirect('estoque')
    else:
        form = ProdutoForm(usuario=request.user)
    
    return render(request, 'core/produto_form.html', {'form': form})

@login_required
@require_POST  # Garante que só aceita requisições POST
def excluir_produto(request, id):
    produto = get_object_or_404(Produto, id=id, usuario=request.user)
    
    try:
        produto.delete()
        messages.success(request, 'Produto excluído com sucesso!')
    except Exception as e:
        messages.error(request, f'Erro ao excluir produto: {str(e)}')
    
    return redirect('estoque')


@login_required
def editar_produto(request, id):
    produto = get_object_or_404(Produto, id=id, usuario=request.user)
    
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
    produto = get_object_or_404(Produto, id=id, usuario=request.user)
    
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
    
    movimentos = MovimentoEstoque.objects.filter(
        usuario=request.user,
        produto__usuario=request.user  
    ).order_by('-data')
    
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
        form = ItemVendaForm(request.POST, usuario=request.user)
        if form.is_valid():
            item = form.save(commit=False)
            item.nota = nota
            item.preco_unitario = item.produto.preco
            
            if item.produto.quantidade < item.quantidade:
                messages.error(request, f'Estoque insuficiente para {item.produto.nome}. Disponível: {item.produto.quantidade}')
                return redirect('adicionar_item_venda', nota_id=nota.id)
            
            item.save()
            
            
            produto = item.produto
            produto.quantidade -= item.quantidade
            produto.save()
            
            # Atualizar total da nota usando o property subtotal
            nota.total = sum(item.subtotal for item in nota.itemvenda_set.all())
            nota.save()
            
            messages.success(request, 'Item adicionado com sucesso!')
            return redirect('adicionar_item_venda', nota_id=nota.id)
    else:
        form = ItemVendaForm(usuario=request.user)
    
    # Carregar todos os produtos disponíveis para o select
    produtos = Produto.objects.filter(usuario=request.user, quantidade__gt=0)
    
    itens_venda = nota.itemvenda_set.select_related('produto').all()
    
    return render(request, 'core/nota_venda.html', {
        'nota': nota,
        'form': form,
        'itens': itens_venda,  
        'produtos': produtos,
    })


@login_required
def finalizar_venda(request, nota_id):
    nota = get_object_or_404(NotaVenda, pk=nota_id, usuario=request.user)
    
    
    itens = nota.itemvenda_set.all()
    if not itens.exists():
        messages.error(request, 'Não é possível finalizar uma venda sem itens!')
        return redirect('nota_venda', nota_id=nota_id)
    
    for item in itens:
        if item.produto.quantidade < item.quantidade:
            messages.error(request, f'Estoque insuficiente para {item.produto.nome}. Disponível: {item.produto.quantidade}, Solicitado: {item.quantidade}')
            return redirect('adicionar_item_venda', nota_id=nota_id)
    
    if request.method == 'POST':
        # Processar formulário de pagamento
        forma_pagamento = request.POST.get('forma_pagamento')
        desconto_percentual = request.POST.get('desconto_percentual', '0')
        desconto_valor = request.POST.get('desconto_valor', '0')
        
        # Validar forma de pagamento
        if not forma_pagamento:
            messages.error(request, 'Selecione uma forma de pagamento!')
            return render(request, 'finalizar_venda.html', {
                'nota': nota,
                'itens': itens
            })
        
        # Converter para Decimal
        try:
            desconto_percentual = Decimal(desconto_percentual)
            desconto_valor = Decimal(desconto_valor)
        except (ValueError, TypeError):
            desconto_percentual = Decimal(0)
            desconto_valor = Decimal(0)
        
        # Calcular desconto final
        if desconto_percentual > 0:
            desconto_final = (nota.total * desconto_percentual) / 100
        else:
            desconto_final = desconto_valor
        
        # Validar desconto
        if desconto_final > nota.total:
            messages.error(request, 'Desconto não pode ser maior que o total da venda!')
            return render(request, 'finalizar_venda.html', {
                'nota': nota,
                'itens': itens
            })
        
        # Atualizar nota
        nota.desconto = desconto_final
        nota.total_com_desconto = nota.total - desconto_final
        nota.forma_pagamento = forma_pagamento
        nota.status = 'finalizada'
        nota.save()
        
        for item in itens:
            produto = item.produto
            produto.quantidade -= item.quantidade
            produto.save()
            
            # Registrar movimento de saída de estoque
            MovimentoEstoque.objects.create(
                produto=produto,
                quantidade=item.quantidade,
                tipo='saida',
                usuario=request.user
            )
        
        # Criar movimentação de caixa com valor líquido (com desconto)
        Movimentacao.objects.create(
            tipo='E',
            valor=nota.total_com_desconto,
            descricao=f"Venda #{nota.id} para {nota.cliente} - {forma_pagamento}",
            data=datetime.now().date(),
            usuario=request.user
        )
        
        # Atualizar estoque dos produtos
        for item in itens:
            produto = item.produto
            produto.quantidade -= item.quantidade
            produto.save()
        
        messages.success(request, 'Venda finalizada com sucesso!')
        return redirect('dashboard')
    
    # Se for GET, mostrar formulário de pagamento
    return render(request, 'core/finalizar_venda.html', {
        'nota': nota,
        'itens': itens
    })

@login_required
def cancelar_venda(request, nota_id):
    nota = get_object_or_404(NotaVenda, pk=nota_id, usuario=request.user)
    
    if nota.status == 'finalizada':
        messages.error(request, 'Não é possível cancelar uma venda já finalizada!')
        return redirect('dashboard')
    
    # Deletar a nota de venda (os itens serão deletados em cascade)
    nota.delete()
    
    messages.success(request, 'Venda cancelada com sucesso!')
    return redirect('dashboard')


@login_required
def aplicar_desconto_ajax(request):
    if request.method == 'POST':
        nota_id = request.POST.get('nota_id')
        tipo_desconto = request.POST.get('tipo_desconto')
        valor_desconto = request.POST.get('valor_desconto')
        
        if not all([nota_id, tipo_desconto, valor_desconto]):
            return JsonResponse({'success': False, 'error': 'Dados incompletos'})
        
        try:
            nota = get_object_or_404(NotaVenda, id=nota_id, usuario=request.user)
            valor_desconto = Decimal(valor_desconto)
            
            if tipo_desconto == 'percentual':
                desconto = (nota.total * valor_desconto) / 100
            else:  # valor
                desconto = valor_desconto
            
            # Validar desconto
            if desconto > nota.total:
                return JsonResponse({
                    'success': False, 
                    'error': 'Desconto não pode ser maior que o total'
                })
            
            total_com_desconto = nota.total - desconto
            
            return JsonResponse({
                'success': True,
                'desconto': str(desconto.quantize(Decimal('0.01'))),
                'total_com_desconto': str(total_com_desconto.quantize(Decimal('0.01')))
            })
            
        except (ValueError, TypeError) as e:
            return JsonResponse({'success': False, 'error': 'Valor inválido'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': 'Erro interno'})
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})

# views.py
@login_required
def ver_nota_venda(request, nota_id):
    nota = get_object_or_404(NotaVenda, pk=nota_id, usuario=request.user)
    itens = nota.itemvenda_set.all()
    
    return render(request, 'nota_venda.html', {
        'nota': nota,
        'itens': itens,
        'produtos': Produto.objects.all()  # ou sua query de produtos
    })


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
