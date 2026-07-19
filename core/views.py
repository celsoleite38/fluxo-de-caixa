# Create your views here.
from django.db.models.aggregates import Count
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, update_session_auth_hash, authenticate
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum
from django.db.models import Q
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.utils import timezone as tz
from datetime import datetime, timedelta, timezone, date, time
from itertools import product as itertools_product

from core.utils import get_usuario_referencia
from colaborador.decorators import colaborador_tem_permissao
from .forms import (
    CategoriaForm, EditarPerfilForm, EntradaEstoqueForm, UsuarioForm,
    CustomPasswordChangeForm, MovimentacaoForm, ProdutoForm, NotaVendaForm,
    ItemVendaForm, TipoVariacaoForm, ValorVariacaoForm, ProdutoVariacaoForm,
    CorrecaoEstoqueForm, OrcamentoForm, ItemOrcamentoForm, MaquinaCartaoForm,
    SolicitarResetSenhaForm, ResetSenhaForm,
)
from .models import (
    ItemVenda, Movimentacao, Categoria, Produto, NotaVenda, MovimentoEstoque,
    TipoVariacao, ValorVariacao, ProdutoVariacao, Orcamento, ItemOrcamento,
    ConfigEstoqueBaixo, MaquinaCartao, TokenVerificacao, Perfil,
)
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import models
from django.utils import timezone

from django.views.decorators.http import require_POST
from django.contrib.auth.forms import PasswordChangeForm
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse
from decimal import Decimal, ROUND_HALF_UP
from colaborador.models import Colaborador
import uuid

from .models import Perfil
from logs.models import LogSistema

def formatar_brl(valor):
    v = Decimal(valor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    partes = f"{v:,.2f}".split('.')
    inteiro = partes[0].replace(',', '.')
    decimal = partes[1]
    return f"{inteiro},{decimal}"

@login_required
def dashboard(request):
    from .utils import get_usuario_referencia
    usuario_referencia = get_usuario_referencia(request)
    hoje = date.today()
    inicio_mes = hoje.replace(day=1)

    movimentacoes_hoje = Movimentacao.objects.filter(
        usuario=usuario_referencia,
        data=hoje
    ).order_by('-data')

    entradas_hoje = movimentacoes_hoje.filter(
        tipo='E').aggregate(total=Sum('valor'))['total'] or 0

    saidas_hoje = movimentacoes_hoje.filter(
        tipo='S').aggregate(total=Sum('valor'))['total'] or 0

    saldo_hoje = entradas_hoje - saidas_hoje

    entradas_mes = Movimentacao.objects.filter(
        tipo='E',
        data__gte=inicio_mes,
        usuario=usuario_referencia
    ).aggregate(total=Sum('valor'))['total'] or 0

    saidas_mes = Movimentacao.objects.filter(
        tipo='S',
        data__gte=inicio_mes,
        usuario=usuario_referencia
    ).aggregate(total=Sum('valor'))['total'] or 0

    saldo_mes = entradas_mes - saidas_mes

    vendas_hoje = NotaVenda.objects.filter(
        usuario=usuario_referencia,
        data=hoje
    )
    total_vendas_hoje = vendas_hoje.aggregate(total=Sum('total'))['total'] or 0
    qtd_vendas_hoje = vendas_hoje.count()

    # Buscar configuracao de estoque baixo para esta empresa
    from .models import ConfigEstoqueBaixo
    config_estoque, _ = ConfigEstoqueBaixo.objects.get_or_create(
        usuario=usuario_referencia,
        defaults={
            'nome_empresa': usuario_referencia.get_full_name() or usuario_referencia.username,
            'limite_estoque_baixo': 5,
            'dias_movimentacao': 30,
        }
    )
    limite = config_estoque.limite_estoque_baixo
    dias_mov = config_estoque.dias_movimentacao

    # Produtos com movimentacao nos ultimos N dias e estoque baixo
    corte = hoje - timedelta(days=dias_mov)

    # IDs de produtos sem grade que tiveram movimentacao recente
    ids_com_movimento = MovimentoEstoque.objects.filter(
        usuario=usuario_referencia,
        variacao__isnull=True,
        data__gte=corte
    ).values_list('produto_id', flat=True).distinct()

    produtos_sem_grade = Produto.objects.filter(
        usuario=usuario_referencia,
        tem_variacao=False,
        quantidade__lte=limite
    ).filter(
        Q(pk__in=ids_com_movimento) | Q(quantidade=0)
    )

    # IDs de variacoes que tiveram movimentacao recente
    ids_var_movimento = MovimentoEstoque.objects.filter(
        usuario=usuario_referencia,
        variacao__isnull=False,
        data__gte=corte
    ).values_list('variacao_id', flat=True).distinct()

    variacoes_baixo = ProdutoVariacao.objects.filter(
        produto__usuario=usuario_referencia,
        ativo=True,
        quantidade__lte=limite
    ).select_related('produto').filter(
        Q(pk__in=ids_var_movimento) | Q(quantidade=0)
    )

    # Montar lista unica de itens com estoque baixo
    itens_baixo_estoque = []

    for p in produtos_sem_grade:
        itens_baixo_estoque.append({
            'nome': p.nome,
            'sku': None,
            'variacao': None,
            'quantidade': p.quantidade,
            'produto_id': p.pk,
            'url': f'/estoque/editar/{p.pk}/',
        })

    for v in variacoes_baixo:
        itens_baixo_estoque.append({
            'nome': v.produto.nome,
            'sku': v.sku,
            'variacao': v.descricao_variacao,
            'quantidade': v.quantidade,
            'produto_id': v.produto.pk,
            'url': f'/produto/{v.produto.pk}/variacao/',
        })

    # Ordenar por quantidade (menor primeiro)
    itens_baixo_estoque.sort(key=lambda x: x['quantidade'])
    itens_baixo_top5 = itens_baixo_estoque[:5]

    context = {
        'entradas_hoje': entradas_hoje,
        'saidas_hoje': saidas_hoje,
        'saldo_hoje': saldo_hoje,
        'entradas_hoje_fmt': formatar_brl(entradas_hoje),
        'saidas_hoje_fmt': formatar_brl(saidas_hoje),
        'saldo_hoje_fmt': formatar_brl(abs(saldo_hoje)),
        'entradas_mes': entradas_mes,
        'saidas_mes': saidas_mes,
        'saldo_mes': saldo_mes,
        'entradas_mes_fmt': formatar_brl(entradas_mes),
        'saidas_mes_fmt': formatar_brl(saidas_mes),
        'saldo_mes_fmt': formatar_brl(abs(saldo_mes)),
        'vendas_hoje': vendas_hoje,
        'total_vendas_hoje': formatar_brl(total_vendas_hoje),
        'qtd_vendas_hoje': qtd_vendas_hoje,
        'data_hoje': hoje,
        'movimentacoes_hoje': movimentacoes_hoje,
        'itens_baixo_estoque': itens_baixo_top5,
        'qtd_itens_baixo': len(itens_baixo_estoque),
    }
    return render(request, 'core/dashboard.html', context)

@login_required
@colaborador_tem_permissao('financeiro', 'ver')
def lista_movimentacoes(request, tipo):
    from .utils import get_usuario_referencia
    usuario_referencia = get_usuario_referencia(request)
    movimentacoes = Movimentacao.objects.filter(
        tipo=tipo,
        usuario=usuario_referencia
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
@colaborador_tem_permissao('financeiro', 'editar')
def adicionar_movimentacao(request):
    from .utils import get_usuario_referencia
    usuario_referencia = get_usuario_referencia(request)
    if request.method == 'POST':
        form = MovimentacaoForm(request.POST)
        if form.is_valid():
            movimentacao = form.save(commit=False)
            movimentacao.usuario = usuario_referencia
            movimentacao.save()

            LogSistema.objects.create(
                usuario=request.user,
                acao='C',
                modulo='Fluxo de Caixa',
                descricao=f"Adicionou movimentação tipo '{movimentacao.get_tipo_display()}' no valor de R$ {movimentacao.valor}"
            )

            messages.success(request, 'Movimentação adicionada com sucesso!')
            return redirect('dashboard')
    else:
        form = MovimentacaoForm()
    
    return render(request, 'core/movimentacao_form.html', {'form': form})

@login_required
@colaborador_tem_permissao('financeiro', 'editar')
def editar_movimentacao(request, pk):
    usuario_referencia = get_usuario_referencia(request)
    movimentacao = get_object_or_404(Movimentacao, pk=pk, usuario=usuario_referencia)
    if request.method == 'POST':
        form = MovimentacaoForm(request.POST, instance=movimentacao)
        if form.is_valid():
            form.save()

            LogSistema.objects.create(
                usuario=request.user,
                acao='U',
                modulo='Fluxo de Caixa',
                descricao=f"Editou a movimentação ID {pk} para o valor de R$ {movimentacao.valor}"
            )

            messages.success(request, 'Movimentação atualizada com sucesso!')
            return redirect('dashboard')
    else:
        form = MovimentacaoForm(instance=movimentacao)
    
    return render(request, 'core/movimentacao_form.html', {'form': form})

@login_required
@colaborador_tem_permissao('financeiro', 'excluir')
def excluir_movimentacao(request, pk):
    usuario_referencia = get_usuario_referencia(request)
    movimentacao = get_object_or_404(Movimentacao, pk=pk, usuario=usuario_referencia)
    if request.method == 'POST':
        valor_removido = movimentacao.valor
        tipo_removido = movimentacao.get_tipo_display()
        movimentacao.delete()

        LogSistema.objects.create(
            usuario=request.user,
            acao='D',
            modulo='Fluxo de Caixa',
            descricao=f"Excluiu movimentação ID {pk} ({tipo_removido}) no valor de R$ {valor_removido}"
        )

        messages.success(request, 'Movimentação excluída com sucesso!')
        return redirect('dashboard')
    return render(request, 'core/confirmar_remocao_item.html', {'object': movimentacao})


@login_required
@colaborador_tem_permissao('relatorios', 'ver')
def relatorios(request):
    from .utils import get_usuario_referencia
    
    usuario_referencia = get_usuario_referencia(request)
    movimentacoes = Movimentacao.objects.filter(usuario=usuario_referencia)
    
    vendas = NotaVenda.objects.filter(usuario=usuario_referencia, status='finalizada')
    
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    forma_pagamento = request.GET.get('forma_pagamento', '')
    
    if data_inicio:
        try:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            inicio_datetime = timezone.make_aware(
                datetime.combine(data_inicio_obj, time.min)
            )
            movimentacoes = movimentacoes.filter(data__gte=inicio_datetime)
            vendas = vendas.filter(data__gte=inicio_datetime)
        except ValueError:
            messages.error(request, "Data início inválida")
    
    if data_fim:
        try:
            data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
            fim_datetime = timezone.make_aware(
                datetime.combine(data_fim_obj, time.max)
            )
            movimentacoes = movimentacoes.filter(data__lte=fim_datetime)
            vendas = vendas.filter(data__lte=fim_datetime)
        except ValueError:
            messages.error(request, "Data fim inválida")

    if forma_pagamento:
        vendas = vendas.filter(forma_pagamento=forma_pagamento)

    entradas = movimentacoes.filter(tipo='E').order_by('-data')
    saidas = movimentacoes.filter(tipo='S').order_by('-data')
    
    total_entradas = entradas.aggregate(total=Sum('valor'))['total'] or 0
    total_saidas = saidas.aggregate(total=Sum('valor'))['total'] or 0
    saldo = total_entradas - total_saidas
    
    total_vendas = vendas.aggregate(total=Sum('total_com_desconto'))['total'] or 0
    total_vendas_bruto = vendas.aggregate(total=Sum('total'))['total'] or 0
    total_descontos = total_vendas_bruto - total_vendas
    qtd_vendas = vendas.count()
    
    vendas_com_forma = vendas.exclude(forma_pagamento__isnull=True)
    vendas_por_forma = vendas_com_forma.values('forma_pagamento').annotate(
        total=Sum('total_com_desconto'),
        quantidade=Count('id')
    ).order_by('-total')
    
    vendas_por_forma_list = list(vendas_por_forma)
    
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
    
    # Relatorio de Lucro: produtos vendidos no periodo com preco compra vs venda
    itens_venda = ItemVenda.objects.filter(
        nota__usuario=usuario_referencia,
        nota__status='finalizada'
    ).select_related('produto', 'variacao')
    
    if data_inicio:
        itens_venda = itens_venda.filter(nota__data__gte=inicio_datetime)
    if data_fim:
        itens_venda = itens_venda.filter(nota__data__lte=fim_datetime)
    
    lucro_produtos = []
    lucro_por_produto = {}
    for item in itens_venda:
        prod = item.produto
        if prod.id not in lucro_por_produto:
            lucro_por_produto[prod.id] = {
                'produto': prod,
                'qtd_vendida': 0,
                'total_venda': 0,
                'total_compra': 0,
            }
        entrada = lucro_por_produto[prod.id]
        entrada['qtd_vendida'] += item.quantidade
        entrada['total_venda'] += float(item.preco_unitario * item.quantidade)
        # Custo: usa preco_compra da variacao se tiver, senao do produto
        if item.variacao:
            custo = float(item.variacao.preco_compra_efetivo * item.quantidade)
        else:
            custo = float(prod.preco_compra * item.quantidade)
        entrada['total_compra'] += custo
    
    for prod_id, dados in lucro_por_produto.items():
        dados['lucro'] = dados['total_venda'] - dados['total_compra']
        if dados['total_compra'] > 0:
            dados['margem'] = (dados['lucro'] / dados['total_compra']) * 100
        else:
            dados['margem'] = 0
        lucro_produtos.append(dados)
    
    lucro_produtos.sort(key=lambda x: x['lucro'], reverse=True)
    
    total_custo = sum(d['total_compra'] for d in lucro_produtos)
    total_receita = sum(d['total_venda'] for d in lucro_produtos)
    total_lucro = total_receita - total_custo
    margem_geral = (total_lucro / total_custo * 100) if total_custo > 0 else 0
    ticket_medio_geral = float(total_vendas) / qtd_vendas if qtd_vendas > 0 else 0
    
    # Vendas por periodo (dia)
    from django.db.models.functions import TruncDate
    vendas_por_dia_raw = vendas.annotate(
        data_venda=TruncDate('data')
    ).values('data_venda').annotate(
        total=Sum('total_com_desconto'),
        quantidade=Count('id')
    ).order_by('data_venda')
    
    vendas_por_dia = []
    for dia in vendas_por_dia_raw:
        d = dict(dia)
        d['ticket_medio'] = float(d['total']) / d['quantidade'] if d['quantidade'] > 0 else 0
        vendas_por_dia.append(d)
    
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
        'lucro_produtos': lucro_produtos,
        'total_custo': total_custo,
        'total_receita': total_receita,
        'total_lucro': total_lucro,
        'margem_geral': margem_geral,
        'vendas_por_dia': vendas_por_dia,
        'ticket_medio_geral': ticket_medio_geral,
    }
    return render(request, 'core/relatorios.html', context)


def imprimir_entradas(request):
    usuario_referencia = get_usuario_referencia(request)
    entradas = Movimentacao.objects.filter(tipo='E', usuario=usuario_referencia).order_by("-data")
    total = entradas.aggregate(total=Sum('valor'))['total'] or 0
    
    return render(request, "core/imprimir_entradas.html", {
        "entradas": entradas,
        "total": total
    })

def imprimir_saidas(request):
    usuario_referencia = get_usuario_referencia(request)
    saidas = Movimentacao.objects.filter(tipo='S', usuario=usuario_referencia).order_by("-data")
    total = saidas.aggregate(total=Sum('valor'))['total'] or 0
    
    return render(request, "core/imprimir_saidas.html", {
        "saidas": saidas,
        "total": total
    })


@login_required
@colaborador_tem_permissao('estoque', 'ver')
def lista_produtos(request):
    from .utils import get_usuario_referencia
    from django.db.models import Q, Sum, Count
    
    usuario_referencia = get_usuario_referencia(request)
    
    busca = request.GET.get('busca', '').strip()
    ordenacao = request.GET.get('ordenacao', 'nome')
    variacao_valor = request.GET.get('variacao_valor', '')
    
    produtos = Produto.objects.filter(
        usuario=usuario_referencia
    ).prefetch_related('variacoes', 'variacoes__valores', 'variacoes__valores__tipo')
    
    if busca:
        produtos = produtos.filter(
            Q(nome__icontains=busca) | Q(sku_base__icontains=busca)
        )
    
    if variacao_valor:
        produtos = produtos.filter(
            Q(tem_variacao=False) |
            Q(tem_variacao=True, variacoes__valores__pk=variacao_valor, variacoes__ativo=True)
        ).distinct()
    
    if ordenacao == 'estoque_asc':
        from django.db.models import Case, When, Value, IntegerField
        produtos = produtos.annotate(
            estoque_order=Case(
                When(tem_variacao=False, then='quantidade'),
                default=Value(0),
                output_field=IntegerField(),
            )
        ).order_by('estoque_order', 'nome')
    elif ordenacao == 'estoque_desc':
        from django.db.models import Case, When, Value, IntegerField
        produtos = produtos.annotate(
            estoque_order=Case(
                When(tem_variacao=False, then='quantidade'),
                default=Value(0),
                output_field=IntegerField(),
            )
        ).order_by('-estoque_order', 'nome')
    elif ordenacao == 'preco':
        produtos = produtos.order_by('preco', 'nome')
    else:
        produtos = produtos.order_by('nome')
    
    from .models import ValorVariacao
    valores_disponiveis = ValorVariacao.objects.filter(
        tipo__produtos__usuario=usuario_referencia
    ).select_related('tipo').order_by('tipo__nome', 'valor')
    
    return render(request, 'core/estoque.html', {
        'produtos': produtos,
        'busca': busca,
        'ordenacao': ordenacao,
        'variacao_valor': variacao_valor,
        'valores_disponiveis': valores_disponiveis,
    })

def _processar_variacoes(request, produto, usuario_referencia):
    """Cria variacoes a partir dos dados do form unico de cadastro."""
    import json
    from itertools import product as itertools_product
    from .models import MovimentoEstoque, TipoVariacao, ValorVariacao, ProdutoVariacao
    
    def _safe_json(raw, default):
        try:
            return json.loads(raw) if raw else default
        except (json.JSONDecodeError, TypeError):
            return default
    
    tipos_ids = _safe_json(request.POST.get('tipos_variacao_ids'), [])
    valores_por_tipo = _safe_json(request.POST.get('valores_por_tipo'), {})
    quantidades = _safe_json(request.POST.get('quantidades_variacoes'), {})
    novos_tipos_nomes = _safe_json(request.POST.get('novos_tipos'), [])
    novos_valores_map = _safe_json(request.POST.get('novos_valores'), {})
    
    # --- 1. Criar novos tipos ---
    tipos_existentes = {
        t.nome.lower(): t
        for t in TipoVariacao.objects.filter(usuario=usuario_referencia)
    }
    for nome_tipo in novos_tipos_nomes:
        nome_lower = nome_tipo.strip().lower()
        if nome_lower not in tipos_existentes:
            tipo = TipoVariacao.objects.create(
                usuario=usuario_referencia,
                nome=nome_tipo.strip(),
                ordem=TipoVariacao.objects.filter(usuario=usuario_referencia).count() + 1,
            )
            tipos_existentes[nome_lower] = tipo
    
    # --- 2. Mapear IDs existentes -> objetos ---
    tipos_map = {}
    for tipo_id in tipos_ids:
        try:
            tipos_map[str(tipo_id)] = TipoVariacao.objects.get(
                id=int(tipo_id), usuario=usuario_referencia
            )
        except (TipoVariacao.DoesNotExist, ValueError):
            pass
    
    # --- 3. Criar novos valores ---
    valores_existentes = set(
        (v.tipo.id, v.valor.lower())
        for v in ValorVariacao.objects.filter(tipo__usuario=usuario_referencia)
    )
    
    for tipo_nome, valores_lista in novos_valores_map.items():
        tipo_obj = None
        for t in tipos_map.values():
            if t.nome.lower() == tipo_nome.strip().lower():
                tipo_obj = t
                break
        if tipo_obj is None:
            tipo_obj = tipos_existentes.get(tipo_nome.strip().lower())
        if tipo_obj:
            for valor_nome in valores_lista:
                valor_lower = valor_nome.strip().lower()
                if (tipo_obj.id, valor_lower) not in valores_existentes:
                    ValorVariacao.objects.create(
                        tipo=tipo_obj,
                        valor=valor_nome.strip(),
                        ordem=ValorVariacao.objects.filter(tipo=tipo_obj).count() + 1,
                    )
                    valores_existentes.add((tipo_obj.id, valor_lower))
    
    # --- 4. Montar valores por tipo com chave original ---
    # chave_original = str(id) para existentes, "novo_Nome" para novos
    # Precisamos disso para casar com as chaves do JS na grade
    
    # Mapa: tipo_id -> [(chave_original, ValorVariacao_obj), ...]
    valores_com_chave = {}
    
    # Valores existentes selecionados no form
    for tipo_id_str, valor_ids in valores_por_tipo.items():
        tipo_obj = tipos_map.get(tipo_id_str)
        if not tipo_obj:
            continue
        lista = []
        for vid in valor_ids:
            try:
                v = ValorVariacao.objects.get(id=int(vid), tipo=tipo_obj)
                lista.append((str(v.id), v))
            except (ValorVariacao.DoesNotExist, ValueError):
                pass
        valores_com_chave[tipo_obj.id] = lista
    
    # Valores novos (criados agora) - buscar no DB
    for tipo_nome, valores_lista in novos_valores_map.items():
        tipo_obj = None
        for t in tipos_map.values():
            if t.nome.lower() == tipo_nome.strip().lower():
                tipo_obj = t
                break
        if tipo_obj is None:
            tipo_obj = tipos_existentes.get(tipo_nome.strip().lower())
        if not tipo_obj:
            continue
        if tipo_obj.id not in valores_com_chave:
            valores_com_chave[tipo_obj.id] = []
        existentes_chaves = {ch for ch, _ in valores_com_chave[tipo_obj.id]}
        for valor_nome in valores_lista:
            try:
                v = ValorVariacao.objects.get(tipo=tipo_obj, valor__iexact=valor_nome.strip())
                chave = f"novo_{v.valor}"
                if chave not in existentes_chaves:
                    valores_com_chave[tipo_obj.id].append((chave, v))
                    existentes_chaves.add(chave)
            except ValorVariacao.DoesNotExist:
                pass
    
    # --- 5. Gerar combinacoes cartesianas ---
    tipos_ordem = sorted(valores_com_chave.keys())
    if not tipos_ordem:
        return
    
    listas_chave_valor = [valores_com_chave[tid] for tid in tipos_ordem]
    combinacoes = list(itertools_product(*listas_chave_valor))
    
    # --- 6. Criar ProdutoVariacao ---
    for combinacao in combinacoes:
        objs_valor = [v for _, v in combinacao]
        
        # Gerar SKU
        partes_sku = [produto.sku_base or produto.nome[:10].upper().replace(' ', '')]
        for v in objs_valor:
            partes_sku.append(v.valor[:5].upper().replace(' ', ''))
        sku = '-'.join(partes_sku)
        sku_base_sku = sku
        contador = 1
        while ProdutoVariacao.objects.filter(sku=sku).exists():
            sku = f"{sku_base_sku}-{contador}"
            contador += 1
        
        # Chave para buscar quantidade (mesma chave do JS)
        chaves = sorted([ch for ch, _ in combinacao])
        chave_qtd = '-'.join(chaves)
        qtd = int(quantidades.get(chave_qtd, 0))
        
        pv = ProdutoVariacao.objects.create(
            produto=produto, sku=sku, quantidade=qtd, ativo=True,
        )
        pv.valores.set(objs_valor)
        
        if qtd > 0:
            MovimentoEstoque.objects.create(
                produto=produto, quantidade=qtd, tipo='cadastro', usuario=request.user,
            )

@login_required
@colaborador_tem_permissao('estoque', 'editar')
def adicionar_produto(request):
    from .utils import get_usuario_referencia
    from .models import MovimentoEstoque
    import json
    
    usuario_referencia = get_usuario_referencia(request)
    
    if request.method == 'POST':
        form = ProdutoForm(request.POST, usuario=usuario_referencia)
        if form.is_valid():
            produto = form.save(commit=False)
            produto.usuario = usuario_referencia
            produto.save()
            form.save_m2m()
            
            if produto.tem_variacao:
                # Processar variacoes do form unico
                _processar_variacoes(request, produto, usuario_referencia)
                tipos_ids_raw = request.POST.get('tipos_variacao_ids', '[]')
                try:
                    tipos_ids = json.loads(tipos_ids_raw)
                except (json.JSONDecodeError, TypeError):
                    tipos_ids = []
                tipos_objs = TipoVariacao.objects.filter(id__in=tipos_ids, usuario=usuario_referencia)
                produto.tipos_variacao.set(tipos_objs)
            else:
                MovimentoEstoque.objects.create(
                    produto=produto,
                    quantidade=produto.quantidade,
                    tipo='cadastro',
                    usuario=request.user
                )

            LogSistema.objects.create(
                usuario=request.user,
                acao='C',
                modulo='Produtos / Estoque',
                descricao=f"Cadastrou o produto '{produto.nome}' com quantidade inicial de {produto.quantidade_total}"
            )
            
            messages.success(request, 'Produto adicionado com sucesso!')
            return redirect('estoque')
    else:
        form = ProdutoForm(usuario=usuario_referencia)
    
    tipos = TipoVariacao.objects.filter(usuario=usuario_referencia)
    return render(request, 'core/produto_form.html', {
        'form': form, 'tipos_disponiveis': tipos
    })

@login_required
@colaborador_tem_permissao('estoque', 'excluir')
@require_POST
def excluir_produto(request, id):
    usuario_referencia = get_usuario_referencia(request)
    produto = get_object_or_404(Produto, id=id, usuario=usuario_referencia)
    
    try:
        nome_produto = produto.nome
        produto.delete()

        LogSistema.objects.create(
            usuario=request.user,
            acao='D',
            modulo='Produtos / Estoque',
            descricao=f"Excluiu o produto '{nome_produto}' (ID: {id})"
        )

        messages.success(request, 'Produto excluído com sucesso!')
    except Exception as e:
        messages.error(request, f'Erro ao excluir produto: {str(e)}')
    
    return redirect('estoque')


@login_required
@colaborador_tem_permissao('estoque', 'editar')
def editar_produto(request, id):
    import json
    from .models import MovimentoEstoque
    usuario_referencia = get_usuario_referencia(request)
    produto = get_object_or_404(Produto, id=id, usuario=usuario_referencia)
    
    if request.method == 'POST':
        form = ProdutoForm(request.POST, instance=produto, usuario=usuario_referencia)
        if form.is_valid():
            form.save()

            if produto.tem_variacao:
                _processar_variacoes(request, produto, usuario_referencia)
                tipos_ids_raw = request.POST.get('tipos_variacao_ids', '[]')
                try:
                    tipos_ids = json.loads(tipos_ids_raw)
                except (json.JSONDecodeError, TypeError):
                    tipos_ids = []
                tipos_objs = TipoVariacao.objects.filter(id__in=tipos_ids, usuario=usuario_referencia)
                produto.tipos_variacao.set(tipos_objs)

            LogSistema.objects.create(
                usuario=request.user,
                acao='U',
                modulo='Produtos / Estoque',
                descricao=f"Editou informações do produto '{produto.nome}' (ID: {id})"
            )

            messages.success(request, 'Produto atualizado com sucesso!')
            return redirect('estoque')
    else:
        form = ProdutoForm(instance=produto, usuario=usuario_referencia)
    
    tipos = TipoVariacao.objects.filter(usuario=usuario_referencia)
    return render(request, 'core/produto_form.html', {
        'form': form, 'editar': True, 'produto': produto,
        'tipos_disponiveis': tipos
    })

@login_required
@colaborador_tem_permissao('estoque', 'editar')
def entrada_estoque(request, id):
    from .utils import get_usuario_referencia
    usuario_referencia = get_usuario_referencia(request)
    produto = get_object_or_404(Produto, id=id, usuario=usuario_referencia)
    
    if produto.tem_variacao:
        return redirect('produto_variacoes', produto_pk=produto.pk)
    
    if request.method == 'POST':
        form = EntradaEstoqueForm(request.POST)
        if form.is_valid():
            quantidade = form.cleaned_data['quantidade']
            produto.quantidade += quantidade
            produto.save()
            
            MovimentoEstoque.objects.create(
                produto=produto,
                quantidade=quantidade,
                tipo='entrada',
                usuario=request.user
            )

            LogSistema.objects.create(
                usuario=request.user,
                acao='U',
                modulo='Produtos / Estoque',
                descricao=f"Realizou entrada manual de {quantidade} unidades no estoque do produto '{produto.nome}'"
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
    from .utils import get_usuario_referencia
    usuario_referencia = get_usuario_referencia(request)
    
    movimentos = MovimentoEstoque.objects.filter(
        produto__usuario=usuario_referencia
    ).select_related('produto', 'variacao', 'usuario').order_by('-data')
    
    produtos = Produto.objects.filter(usuario=usuario_referencia)
    
    tipo_filter = request.GET.get('tipo')
    produto_filter = request.GET.get('produto')
    
    if tipo_filter and tipo_filter != 'todos':
        movimentos = movimentos.filter(tipo=tipo_filter)
    
    if produto_filter and produto_filter != 'todos':
        movimentos = movimentos.filter(produto_id=produto_filter)
    
    context = {
        'movimentos': movimentos,
        'produtos': produtos,
        'tipos_movimento': MovimentoEstoque.TIPO_MOVIMENTO
    }
    
    return render(request, 'core/historico_estoque.html', context)


@login_required
@colaborador_tem_permissao('vendas', 'editar')
def criar_nota_venda(request):
    from .utils import get_usuario_referencia
    
    usuario_referencia = get_usuario_referencia(request)
    if request.method == 'POST':
        form = NotaVendaForm(request.POST)
        if form.is_valid():
            nota = form.save(commit=False)
            nota.total = 0
            nota.usuario = usuario_referencia
            nota.usuario_executante = request.user
            nota.save()

            LogSistema.objects.create(
                usuario=request.user,
                acao='C',
                modulo='Vendas',
                descricao=f"Abriu uma nova nota de venda #{nota.id} para o cliente '{nota.cliente}'"
            )

            messages.success(request, 'Nota de venda criada com sucesso!')
            return redirect('adicionar_item_venda', nota_id=nota.id)
        else:
            print("Erros do formulário:", form.errors)
            messages.error(request, 'Erro no formulário. Verifique os dados.')
    else:
        form = NotaVendaForm()
    
    return render(request, 'core/nota_venda_form.html', {'form': form})

@login_required
@colaborador_tem_permissao('vendas', 'editar')
def adicionar_item_venda(request, nota_id):
    from .utils import get_usuario_referencia
    
    usuario_referencia = get_usuario_referencia(request)
    
    nota = get_object_or_404(
        NotaVenda, 
        pk=nota_id, 
        usuario=usuario_referencia
    )
    
    if request.method == 'POST':
        form = ItemVendaForm(request.POST, usuario=usuario_referencia)
        if form.is_valid():
            item = form.save(commit=False)
            item.nota = nota
            
            variacao = form.cleaned_data.get('variacao')
            if variacao:
                item.variacao = variacao
                item.preco_unitario = variacao.preco_efetivo
                if variacao.quantidade < item.quantidade:
                    messages.error(request, f'Estoque insuficiente para {item.produto.nome} ({variacao.sku}). Disponível: {variacao.quantidade}')
                    return redirect('adicionar_item_venda', nota_id=nota.id)
            else:
                item.preco_unitario = item.produto.preco
                if item.produto.quantidade < item.quantidade:
                    messages.error(request, f'Estoque insuficiente para {item.produto.nome}. Disponível: {item.produto.quantidade}')
                    return redirect('adicionar_item_venda', nota_id=nota.id)
            
            item.save()
            
            nota.total = sum(item.subtotal for item in nota.itemvenda_set.all())
            nota.save()

            desc_item = item.produto.nome
            if variacao:
                desc_item += f" [{variacao.sku}]"

            LogSistema.objects.create(
                usuario=request.user,
                acao='U',
                modulo='Vendas',
                descricao=f"Adicionou {item.quantidade}x do produto '{desc_item}' à nota de venda #{nota.id}"
            )
            
            messages.success(request, 'Item adicionado com sucesso!')
            return redirect('adicionar_item_venda', nota_id=nota.id)
    else:
        form = ItemVendaForm(usuario=usuario_referencia)
    
    produtos = Produto.objects.filter(usuario=usuario_referencia)
    produtos_disponiveis = []
    for p in produtos:
        if p.tem_variacao:
            if p.variacoes.filter(quantidade__gt=0, ativo=True).exists():
                produtos_disponiveis.append(p)
        elif p.quantidade > 0:
            produtos_disponiveis.append(p)
    
    itens_venda = nota.itemvenda_set.select_related('produto', 'variacao').all()
    
    return render(request, 'core/nota_venda.html', {
        'nota': nota,
        'form': form,
        'itens': itens_venda,  
        'produtos': produtos_disponiveis,
    })

@login_required
@colaborador_tem_permissao('vendas', 'editar')
def finalizar_venda(request, nota_id):
    from .utils import get_usuario_referencia
    usuario_referencia = get_usuario_referencia(request)
    nota = get_object_or_404(NotaVenda, pk=nota_id, usuario=usuario_referencia)
    
    itens = nota.itemvenda_set.all()
    if not itens.exists():
        messages.error(request, 'Não é possível finalizar uma venda sem itens!')
        return redirect('nota_venda', nota_id=nota_id)
    
    for item in itens:
        if item.variacao:
            if item.variacao.quantidade < item.quantidade:
                messages.error(request, f'Estoque insuficiente para {item.produto.nome} [{item.variacao.sku}]. Disponível: {item.variacao.quantidade}, Solicitado: {item.quantidade}')
                return redirect('adicionar_item_venda', nota_id=nota_id)
        else:
            if item.produto.quantidade < item.quantidade:
                messages.error(request, f'Estoque insuficiente para {item.produto.nome}. Disponível: {item.produto.quantidade}, Solicitado: {item.quantidade}')
                return redirect('adicionar_item_venda', nota_id=nota_id)
    
    if request.method == 'POST':
        forma_pagamento = request.POST.get('forma_pagamento')
        desconto_percentual = request.POST.get('desconto_percentual', '0')
        desconto_valor = request.POST.get('desconto_valor', '0')
        parcelas = request.POST.get('parcelas', '1')
        operadora_cartao = request.POST.get('operadora_cartao', '')
        maquina_cartao_id = request.POST.get('maquina_cartao', '')
        aplicar_taxa = request.POST.get('aplicar_taxa') == 'on'
        
        if not forma_pagamento:
            messages.error(request, 'Selecione uma forma de pagamento!')
            maquinas = MaquinaCartao.objects.filter(ativo=True)
            return render(request, 'core/finalizar_venda.html', {
                'nota': nota,
                'itens': itens,
                'maquinas': maquinas
            })
        
        try:
            desconto_percentual = Decimal(desconto_percentual)
            desconto_valor = Decimal(desconto_valor)
            parcelas = int(parcelas)
        except (ValueError, TypeError):
            desconto_percentual = Decimal(0)
            desconto_valor = Decimal(0)
            parcelas = 1
        
        if parcelas < 1:
            parcelas = 1
        
        if desconto_percentual > 0:
            desconto_final = (nota.total * desconto_percentual) / 100
        else:
            desconto_final = desconto_valor
        
        if desconto_final > nota.total:
            messages.error(request, 'Desconto não pode ser maior que o total da venda!')
            maquinas = MaquinaCartao.objects.filter(ativo=True)
            return render(request, 'core/finalizar_venda.html', {
                'nota': nota,
                'itens': itens,
                'maquinas': maquinas
            })
        
        total_base = nota.total - desconto_final

        taxa_maquina = Decimal(0)
        if maquina_cartao_id and forma_pagamento == 'cartao_credito':
            try:
                maquina = MaquinaCartao.objects.get(pk=maquina_cartao_id)
                taxa_maquina = maquina.get_taxa_credito_parcela(parcelas)
            except (MaquinaCartao.DoesNotExist, ValueError):
                taxa_maquina = Decimal(0)

        taxa_aplicada = (aplicar_taxa and taxa_maquina > 0 and forma_pagamento == 'cartao_credito')
        acrescimo_calculado = (total_base * taxa_maquina) / 100 if taxa_aplicada else Decimal(0)
        total_final = total_base + acrescimo_calculado

        nota.desconto = desconto_final
        nota.total_com_desconto = total_base
        nota.acrescimo = acrescimo_calculado
        nota.total_com_acrescimo = total_final
        nota.taxa_operadora = taxa_maquina if taxa_aplicada else Decimal(0)
        nota.parcelas = parcelas
        nota.operadora_cartao = operadora_cartao
        nota.forma_pagamento = forma_pagamento
        nota.status = 'finalizada'
        if maquina_cartao_id:
            nota.maquina_cartao_id = maquina_cartao_id
        nota.save()
        
        for item in itens:
            if item.variacao:
                item.variacao.quantidade -= item.quantidade
                item.variacao.save()
                MovimentoEstoque.objects.create(
                    produto=item.produto,
                    variacao=item.variacao,
                    quantidade=item.quantidade,
                    tipo='saida',
                    usuario=usuario_referencia
                )
            else:
                produto = item.produto
                produto.quantidade -= item.quantidade
                produto.save()
                MovimentoEstoque.objects.create(
                    produto=produto,
                    quantidade=item.quantidade,
                    tipo='saida',
                    usuario=usuario_referencia
                )
        
        Movimentacao.objects.create(
            tipo='E',
            valor=total_base,
            descricao=f"Venda #{nota.id} para {nota.cliente} - {nota.get_forma_pagamento_display()}",
            data=datetime.now().date(),
            usuario=usuario_referencia,
            forma_pagamento=forma_pagamento
        )

        desc_pagamento = nota.get_forma_pagamento_display()
        if forma_pagamento == 'cartao_credito' and parcelas > 1:
            desc_pagamento += f" ({parcelas}x R$ {(total_final / parcelas).quantize(Decimal('0.01'))})"
        if acrescimo_calculado > 0:
            desc_pagamento += f" [Taxa: {taxa_maquina}%]"

        LogSistema.objects.create(
            usuario=request.user,
            acao='U',
            modulo='Vendas',
            descricao=f"Finalizou a venda #{nota.id} para '{nota.cliente}'. Forma de Pgto: {desc_pagamento}. Total Líquido: R$ {total_final}"
        )
        
        messages.success(request, 'Venda finalizada com sucesso!')
        return redirect('dashboard')   
    maquinas = MaquinaCartao.objects.filter(ativo=True)
    return render(request, 'core/finalizar_venda.html', {
        'nota': nota,
        'itens': itens,
        'maquinas': maquinas
    })

@login_required
@colaborador_tem_permissao('vendas', 'editar')
def cancelar_venda(request, nota_id):
    nota = get_object_or_404(NotaVenda, pk=nota_id, usuario=request.user)
    
    if nota.status == 'finalizada':
        messages.error(request, 'Não é possível cancelar uma venda já finalizada!')
        return redirect('lista_todas_vendas')
    
    id_cancelado = nota.id
    cliente_cancelado = nota.cliente
    nota.delete()

    LogSistema.objects.create(
        usuario=request.user,
        acao='D',
        modulo='Vendas',
        descricao=f"Cancelou e excluiu o rascunho de venda #{id_cancelado} do cliente '{cliente_cancelado}'"
    )
    
    messages.success(request, 'Venda cancelada com sucesso!')
    return redirect('lista_todas_vendas')


@login_required
def aplicar_desconto_ajax(request):
    if request.method == 'POST':
        nota_id = request.POST.get('nota_id')
        tipo_desconto = request.POST.get('tipo_desconto')
        valor_desconto = request.POST.get('valor_desconto')
        
        if not all([nota_id, tipo_desconto, valor_desconto]):
            return JsonResponse({'success': False, 'error': 'Dados incompletos'})
        
        try:
            usuario_referencia = get_usuario_referencia(request)
            nota = get_object_or_404(NotaVenda, id=nota_id, usuario=usuario_referencia)
            valor_desconto = Decimal(valor_desconto)
            
            if tipo_desconto == 'percentual':
                desconto = (nota.total * valor_desconto) / 100
            else:
                desconto = valor_desconto
            
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
            
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Valor inválido'})
        except Exception:
            return JsonResponse({'success': False, 'error': 'Erro interno'})
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})


@login_required
def ver_nota_venda(request, nota_id):
    from .utils import get_usuario_referencia
    usuario_referencia = get_usuario_referencia(request)
    nota = get_object_or_404(NotaVenda, pk=nota_id, usuario=usuario_referencia)
    itens = nota.itemvenda_set.select_related('variacao').all()
    
    return render(request, 'core/nota_venda.html', {
        'nota': nota,
        'itens': itens,
        'produtos': Produto.objects.all()
    })


@login_required
def imprimir_recibo_venda(request, nota_id):
    from .utils import get_usuario_referencia
    usuario_referencia = get_usuario_referencia(request)
    nota = get_object_or_404(NotaVenda, pk=nota_id, usuario=usuario_referencia)
    try:
        perfil = Perfil.objects.get(usuario=usuario_referencia)
    except Perfil.DoesNotExist:
        perfil = None

    context = {
        'nota': nota,
        'itens': nota.itemvenda_set.select_related('variacao').all(),
        'data_emissao': timezone.now(),
        'perfil_empresa': perfil,
    }
    
    return render(request, 'core/recibo_impressao.html', context)


def _enviar_email_ativacao(request, user):
    token_obj = TokenVerificacao.gerar_token(user, 'ativacao', horas_validade=24)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    link = f"{request.scheme}://{request.get_host()}/contas/ativar/{uid}/{token_obj.token}/"
    html = render_to_string('registration/email_ativacao.html', {
        'user': user, 'link': link,
    })
    send_mail(
        subject='Ative sua conta - Sistema Fluxo de Caixa',
        message=f'Clique no link para ativar sua conta: {link}',
        from_email=None,
        recipient_list=[user.email],
        html_message=html,
        fail_silently=False,
    )


def _enviar_email_reset_senha(request, user):
    token_obj = TokenVerificacao.gerar_token(user, 'reset_senha', horas_validade=24)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    link = f"{request.scheme}://{request.get_host()}/contas/redefinir/{uid}/{token_obj.token}/"
    html = render_to_string('registration/email_reset_senha.html', {
        'user': user, 'link': link,
    })
    send_mail(
        subject='Redefina sua senha - Sistema Fluxo de Caixa',
        message=f'Clique no link para redefinir sua senha: {link}',
        from_email=None,
        recipient_list=[user.email],
        html_message=html,
        fail_silently=False,
    )


def register(request):
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            Perfil.objects.get_or_create(usuario=user, defaults={'Nome': user.get_full_name() or user.username})

            try:
                _enviar_email_ativacao(request, user)
                messages.success(request, 'Cadastro realizado! Verifique seu e-mail para ativar sua conta.')
            except Exception:
                messages.warning(request, 'Cadastro realizado, mas não foi possível enviar o e-mail de ativação. Solicite o reenvio.')

            LogSistema.objects.create(
                usuario=user,
                acao='C',
                modulo='Autenticação',
                descricao=f"Novo usuário cadastrado (pendente ativação): {user.username}"
            )
            return redirect('email_verificado')
    else:
        form = UsuarioForm()
    return render(request, 'registration/register.html', {'form': form})


def _decodificar_uid(uid_b64):
    try:
        return force_str(urlsafe_base64_decode(uid_b64))
    except (TypeError, ValueError, OverflowError):
        return None


def ativar_conta(request, uidb64, token):
    uid = _decodificar_uid(uidb64)
    user = None
    if uid:
        try:
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError):
            pass

    if user and not user.is_active:
        try:
            token_obj = TokenVerificacao.objects.get(usuario=user, token=token, tipo='ativacao')
            if token_obj.esta_valido():
                user.is_active = True
                user.save()
                token_obj.usado = True
                token_obj.save()
                perfil, _ = Perfil.objects.get_or_create(usuario=user, defaults={'Nome': user.get_full_name() or user.username})
                perfil.email_verificado = True
                perfil.save()
                messages.success(request, 'Conta ativada com sucesso! Faça login.')
                return redirect('login')
            else:
                messages.error(request, 'Link expirado. Solicite um novo link de ativação.')
                return redirect('reenviar_ativacao')
        except TokenVerificacao.DoesNotExist:
            pass

    messages.error(request, 'Link de ativação inválido.')
    return redirect('login')


def reenviar_ativacao(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if email:
            try:
                user = User.objects.get(email=email, is_active=False)
                _enviar_email_ativacao(request, user)
            except User.DoesNotExist:
                pass
        messages.success(request, 'Se o e-mail estiver cadastrado e pendente de ativação, você receberá um link.')
        return redirect('login')
    return render(request, 'registration/reenviar_ativacao.html')


@login_required
def verificar_email(request):
    user = request.user
    perfil = getattr(user, 'perfil', None)

    if perfil and perfil.email_verificado:
        return redirect('dashboard')

    if request.method == 'POST':
        if user.email:
            try:
                _enviar_email_ativacao(request, user)
                messages.success(request, f'E-mail de verificação enviado para {user.email}.')
            except Exception:
                messages.error(request, 'Erro ao enviar e-mail. Tente novamente.')
        else:
            email_informado = request.POST.get('email', '').strip()
            if email_informado:
                user.email = email_informado
                user.save()
                try:
                    _enviar_email_ativacao(request, user)
                    messages.success(request, f'E-mail de verificação enviado para {email_informado}.')
                except Exception:
                    messages.error(request, 'Erro ao enviar e-mail. Tente novamente.')
            else:
                messages.error(request, 'Informe um e-mail válido.')

    return render(request, 'registration/verificar_email.html', {'user': user})


def solicitar_reset_senha(request):
    if request.method == 'POST':
        form = SolicitarResetSenhaForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email, is_active=True)
                _enviar_email_reset_senha(request, user)
            except User.DoesNotExist:
                pass
            messages.success(request, 'Se o e-mail estiver cadastrado, você receberá um link para redefinir sua senha.')
            return redirect('login')
    else:
        form = SolicitarResetSenhaForm()
    return render(request, 'registration/password_reset_form.html', {'form': form})


def reset_senha_confirmar(request, uidb64, token):
    uid = _decodificar_uid(uidb64)
    user = None
    if uid:
        try:
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError):
            pass

    token_obj = None
    if user:
        try:
            token_obj = TokenVerificacao.objects.get(usuario=user, token=token, tipo='reset_senha')
        except TokenVerificacao.DoesNotExist:
            pass

    if not user or not token_obj or not token_obj.esta_valido():
        messages.error(request, 'Link de redefinição inválido ou expirado.')
        return redirect('solicitar_reset_senha')

    if request.method == 'POST':
        form = ResetSenhaForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data['nova_senha'])
            user.save()
            token_obj.usado = True
            token_obj.save()
            messages.success(request, 'Senha redefinida com sucesso! Faça login.')
            return redirect('login')
    else:
        form = ResetSenhaForm()

    return render(request, 'registration/password_reset_confirm.html', {'form': form})


@login_required
def change_password(request):
    usuario_referencia = get_usuario_referencia(request)
    if request.method == 'POST':
        form = CustomPasswordChangeForm(usuario_referencia, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)

            LogSistema.objects.create(
                usuario=request.user,
                acao='U',
                modulo='Autenticação',
                descricao=f"Alterou a sua senha de acesso com sucesso."
            )

            messages.success(request, 'Sua senha foi alterada com sucesso!')
            return redirect('dashboard')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Erro no campo '{field}': {error}")
    else:
        form = CustomPasswordChangeForm(usuario_referencia)

    return render(request, 'registration/password_change_form.html', {
        'form': form,
        'title': 'Alterar Senha'
    })

def lista_entradas(request):
    usuario_referencia = get_usuario_referencia(request)
    movimentacoes = Movimentacao.objects.filter(
        tipo='E',
        usuario=usuario_referencia
    ).order_by('-data')
    
    total = movimentacoes.aggregate(total=Sum('valor'))['total'] or 0
    
    return render(request, 'core/entrada_list.html', {
        'movimentacoes': movimentacoes,
        'total': total
    })
    
def lista_saidas(request):
    usuario_referencia = get_usuario_referencia(request)
    movimentacoes = Movimentacao.objects.filter(
        tipo='S',
        usuario=usuario_referencia
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
    usuario_referencia = get_usuario_referencia(request)
    item = get_object_or_404(ItemVenda, pk=pk, nota__usuario=usuario_referencia)
    
    if request.method == 'POST':
        if item.variacao:
            item.variacao.quantidade += item.quantidade
            item.variacao.save()
        else:
            produto = item.produto
            produto.quantidade += item.quantidade
            produto.save()
        
        nota = item.nota
        nome_produto = item.produto.nome
        qtd_removida = item.quantidade
        item.delete()
        
        nota.total = sum(item.subtotal for item in nota.itemvenda_set.all())
        nota.save()

        LogSistema.objects.create(
            usuario=request.user,
            acao='D',
            modulo='Vendas',
            descricao=f"Removeu {qtd_removida}x do produto '{nome_produto}' da nota de venda #{nota.id}"
        )
        
        messages.success(request, 'Item removido com sucesso!')
        return redirect('adicionar_item_venda', nota_id=nota.id)
    
    return render(request, 'core/confirmar_remocao_item.html', {'item': item})

@login_required
def user_logout(request):
    LogSistema.objects.create(
        usuario=request.user,
        acao='L',
        modulo='Autenticação',
        descricao=f"Usuário realizou logout (encerrou a sessão)."
    )
    logout(request)
    return redirect('logout')


@login_required
@colaborador_tem_permissao('vendas', 'ver')
def lista_todas_vendas(request):
    from .utils import get_usuario_referencia
    from django.contrib.auth.models import User
    from django.db.models import Q
    
    usuario_referencia = get_usuario_referencia(request)
    
    vendedores_ids = Colaborador.objects.filter(
        usuario_principal=usuario_referencia,
        ativo=True
    ).values_list('usuario_colaborador_id', flat=True)
    
    vendedores = User.objects.filter(
        Q(id=usuario_referencia.id) | Q(id__in=vendedores_ids)
    ).distinct()
    
    vendas = NotaVenda.objects.filter(usuario=usuario_referencia).prefetch_related('itemvenda_set__produto', 'itemvenda_set__variacao')
    
    status_filter = request.GET.get('status')
    vendedor_filter = request.GET.get('vendedor')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    if status_filter:
        vendas = vendas.filter(status=status_filter)
    
    if vendedor_filter:
        vendas = vendas.filter(
            Q(usuario_executante_id=vendedor_filter) | 
            Q(usuario_id=vendedor_filter, usuario_executante__isnull=True)
        )
    
    if data_inicio:
        vendas = vendas.filter(data__gte=data_inicio)
    
    if data_fim:
        data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d')
        data_fim_obj = data_fim_obj.replace(hour=23, minute=59, second=59)
        vendas = vendas.filter(data__lte=data_fim_obj)
    
    vendas = vendas.order_by('-data')
    
    total_vendas_count = vendas.count()
    total_vendas_valor = vendas.aggregate(total=Sum('total_com_desconto'))['total'] or 0
    
    context = {
        'vendas': vendas,
        'vendedores': vendedores,
        'total_vendas_count': total_vendas_count,
        'total_vendas_valor': total_vendas_valor,
        'STATUS_CHOICES': NotaVenda.STATUS_CHOICES,
    }
    return render(request, 'core/lista_todas_vendas.html', context)

@login_required
def editar_perfil(request):
    usuario = request.user
    perfil, _ = Perfil.objects.get_or_create(usuario=usuario, defaults={'Nome': usuario.get_full_name() or usuario.username})

    if request.method == 'POST':
        form = EditarPerfilForm(request.POST, request.FILES, instance=perfil, user=usuario)
        if form.is_valid():
            form.save()

            LogSistema.objects.create(
                usuario=request.user,
                acao='U',
                modulo='Configurações',
                descricao=f"Atualizou as informações do perfil corporativo."
            )

            messages.success(request, 'Perfil atualizado com sucesso!')
            return redirect('editar_perfil')
        else:
            print("Erros do formulário perfil:", form.errors)
            messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = EditarPerfilForm(instance=perfil, user=usuario)

    return render(request, 'registration/editar_perfil.html', {
        'form': form,
        'perfil': perfil,
        'title': 'Editar Perfil'
    })

@login_required
def imprimir_lista_vendas(request):
    from .utils import get_usuario_referencia
    from django.contrib.auth.models import User
    from django.db.models import Q, Count, Sum
    from datetime import datetime
    
    usuario_referencia = get_usuario_referencia(request)
    
    vendas = NotaVenda.objects.filter(usuario=usuario_referencia).prefetch_related('itemvenda_set__produto', 'itemvenda_set__variacao')
    
    status_filter = request.GET.get('status')
    vendedor_filter = request.GET.get('vendedor')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    if status_filter:
        vendas = vendas.filter(status=status_filter)
        status_filtro = dict(NotaVenda.STATUS_CHOICES).get(status_filter, status_filter)
    else:
        status_filtro = "Todos"
    
    if vendedor_filter:
        vendas = vendas.filter(
            Q(usuario_executante_id=vendedor_filter) | 
            Q(usuario_id=vendedor_filter, usuario_executante__isnull=True)
        )
        try:
            vendedor = User.objects.get(id=vendedor_filter)
            vendedor_filtro = vendedor.get_full_name()
        except User.DoesNotExist:
            vendedor_filtro = vendedor_filter
    else:
        vendedor_filtro = "Todos"
    
    if data_inicio:
        vendas = vendas.filter(data__gte=data_inicio)
    
    if data_fim:
        data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d')
        data_fim_obj = data_fim_obj.replace(hour=23, minute=59, second=59)
        vendas = vendas.filter(data__lte=data_fim_obj)
    
    vendas = vendas.order_by('-data')
    
    total_vendas_count = vendas.count()
    total_vendas_valor = vendas.aggregate(total=Sum('total_com_desconto'))['total'] or 0
    
    vendas_finalizadas = vendas.filter(status='finalizada').count()
    valor_finalizadas = vendas.filter(status='finalizada').aggregate(
        total=Sum('total_com_desconto'))['total'] or 0
    
    vendas_abertas = vendas.filter(status='aberta').count()
    valor_abertas = vendas.filter(status='aberta').aggregate(
        total=Sum('total_com_desconto'))['total'] or 0
    
    context = {
        'vendas': vendas,
        'total_vendas_count': total_vendas_count,
        'total_vendas_valor': total_vendas_valor,
        'vendas_finalizadas': vendas_finalizadas,
        'valor_finalizadas': valor_finalizadas,
        'vendas_abertas': vendas_abertas,
        'valor_abertas': valor_abertas,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'status_filtro': status_filtro,
        'vendedor_filtro': vendedor_filtro,
        'empresa_nome': "SUA EMPRESSA LTDA",
        'empresa_endereco': "Rua Principal, 123 - Centro",
        'empresa_telefone': "(11) 99999-9999",
        'empresa_email': "contato@empresa.com",
        'empresa_cnpj': "00.000.000/0001-00",
        'data_emissao': datetime.now().strftime("%d/%m/%Y %H:%M"),
        'usuario': request.user,
    }
    
    return render(request, 'core/imprimir_lista_vendas.html', context)


# =============================================================================
# VIEWS DE VARIAÇÕES (GRADE)
# =============================================================================

@login_required
@colaborador_tem_permissao('variacao', 'ver')
def tipo_variacao_list(request):
    usuario_referencia = get_usuario_referencia(request)
    tipos = TipoVariacao.objects.filter(usuario=usuario_referencia).annotate(
        qtd_valores=Count('valores')
    )
    return render(request, 'core/tipo_variacao_list.html', {'tipos': tipos})


@login_required
@colaborador_tem_permissao('variacao', 'editar')
def tipo_variacao_create(request):
    usuario_referencia = get_usuario_referencia(request)
    if request.method == 'POST':
        form = TipoVariacaoForm(request.POST, usuario=usuario_referencia)
        if form.is_valid():
            tipo = form.save()

            LogSistema.objects.create(
                usuario=request.user,
                acao='C',
                modulo='Produtos / Estoque',
                descricao=f"Criou o tipo de variação '{tipo.nome}'"
            )

            messages.success(request, f'Tipo de variação "{tipo.nome}" criado com sucesso!')
            return redirect('tipo_variacao_list')
    else:
        form = TipoVariacaoForm(usuario=usuario_referencia)
    return render(request, 'core/tipo_variacao_form.html', {'form': form, 'titulo': 'Novo Tipo de Variação'})


@login_required
@colaborador_tem_permissao('variacao', 'editar')
def tipo_variacao_edit(request, pk):
    usuario_referencia = get_usuario_referencia(request)
    tipo = get_object_or_404(TipoVariacao, pk=pk, usuario=usuario_referencia)
    if request.method == 'POST':
        form = TipoVariacaoForm(request.POST, instance=tipo, usuario=usuario_referencia)
        if form.is_valid():
            form.save()
            messages.success(request, f'Tipo de variação "{tipo.nome}" atualizado!')
            return redirect('tipo_variacao_list')
    else:
        form = TipoVariacaoForm(instance=tipo, usuario=usuario_referencia)
    return render(request, 'core/tipo_variacao_form.html', {'form': form, 'titulo': f'Editar: {tipo.nome}'})


@login_required
@colaborador_tem_permissao('variacao', 'excluir')
@require_POST
def tipo_variacao_delete(request, pk):
    usuario_referencia = get_usuario_referencia(request)
    tipo = get_object_or_404(TipoVariacao, pk=pk, usuario=usuario_referencia)
    
    if tipo.produtos.exists():
        messages.error(request, f'Não é possível excluir "{tipo.nome}" pois está associado a produtos.')
        return redirect('tipo_variacao_list')
    
    nome = tipo.nome
    tipo.delete()

    LogSistema.objects.create(
        usuario=request.user,
        acao='D',
        modulo='Produtos / Estoque',
        descricao=f"Excluiu o tipo de variação '{nome}'"
    )

    messages.success(request, f'Tipo de variação "{nome}" excluído!')
    return redirect('tipo_variacao_list')


@login_required
def tipo_variacao_valores(request, pk):
    usuario_referencia = get_usuario_referencia(request)
    tipo = get_object_or_404(TipoVariacao, pk=pk, usuario=usuario_referencia)
    valores = tipo.valores.all()

    if request.method == 'POST':
        form = ValorVariacaoForm(request.POST)
        if form.is_valid():
            valor = form.save(commit=False)
            valor.tipo = tipo
            try:
                valor.save()
                messages.success(request, f'Valor "{valor.valor}" adicionado!')
            except Exception:
                messages.error(request, f'O valor "{valor.valor}" já existe para este tipo.')
            return redirect('tipo_variacao_valores', pk=pk)
    else:
        form = ValorVariacaoForm()

    return render(request, 'core/tipo_variacao_valores.html', {
        'tipo': tipo, 'valores': valores, 'form': form
    })


@login_required
@require_POST
def valor_variacao_delete(request, pk):
    usuario_referencia = get_usuario_referencia(request)
    valor = get_object_or_404(ValorVariacao, pk=pk, tipo__usuario=usuario_referencia)
    tipo_pk = valor.tipo.pk
    
    if valor.produto_variacoes.exists():
        messages.error(request, f'Não é possível excluir "{valor.valor}" pois está em uso em variações de produtos.')
        return redirect('tipo_variacao_valores', pk=tipo_pk)
    
    nome = valor.valor
    valor.delete()
    messages.success(request, f'Valor "{nome}" excluído!')
    return redirect('tipo_variacao_valores', pk=tipo_pk)


@login_required
def produto_variacoes(request, produto_pk):
    usuario_referencia = get_usuario_referencia(request)
    produto = get_object_or_404(Produto, pk=produto_pk, usuario=usuario_referencia)
    variacoes = produto.variacoes.prefetch_related('valores__tipo').all()

    if not produto.tem_variacao:
        messages.info(request, 'Este produto não possui variações habilitadas.')
        return redirect('editar_produto', id=produto.pk)

    form = ProdutoVariacaoForm(produto=produto)

    if request.method == 'POST' and 'adicionar' in request.POST:
        form = ProdutoVariacaoForm(request.POST, produto=produto)
        if form.is_valid():
            variacao = form.save(commit=False)
            variacao.produto = produto
            variacao.save()
            form.save_m2m()

            LogSistema.objects.create(
                usuario=request.user,
                acao='C',
                modulo='Produtos / Estoque',
                descricao=f"Adicionou variação SKU '{variacao.sku}' ao produto '{produto.nome}'"
            )

            messages.success(request, f'Variação "{variacao.sku}" criada com sucesso!')
            return redirect('produto_variacoes', produto_pk=produto_pk)

    tipos = produto.tipos_variacao.all()
    tipos_vinculados_ids = list(tipos.values_list('pk', flat=True))
    todos_tipos = TipoVariacao.objects.filter(usuario=usuario_referencia).exclude(pk__in=tipos_vinculados_ids)
    valores_por_tipo = {}
    for tipo in tipos:
        valores_por_tipo[tipo.pk] = tipo.valores.all()

    return render(request, 'core/produto_variacoes.html', {
        'produto': produto,
        'variacoes': variacoes,
        'form': form,
        'tipos': tipos,
        'todos_tipos': todos_tipos,
        'valores_por_tipo': valores_por_tipo,
    })


@login_required
def api_tipo_valores(request, pk):
    """Retorna JSON com os valores de um tipo de variacao."""
    usuario_referencia = get_usuario_referencia(request)
    tipo = get_object_or_404(TipoVariacao, pk=pk, usuario=usuario_referencia)
    valores = list(tipo.valores.values('id', 'valor'))
    return JsonResponse({'tipo_nome': tipo.nome, 'valores': valores})


@login_required
def api_criar_valor(request):
    """Cria um valor de variacao e retorna JSON."""
    import json
    if request.method != 'POST':
        return JsonResponse({'erro': 'Metodo nao permitido'}, status=405)
    
    data = json.loads(request.body)
    tipo_id = data.get('tipo_id')
    valor_nome = data.get('valor', '').strip()
    
    if not tipo_id or not valor_nome:
        return JsonResponse({'erro': 'Dados invalidos'}, status=400)
    
    usuario_referencia = get_usuario_referencia(request)
    tipo = get_object_or_404(TipoVariacao, pk=tipo_id, usuario=usuario_referencia)
    
    valor, criado = ValorVariacao.objects.get_or_create(
        tipo=tipo,
        valor=valor_nome,
        defaults={'ordem': ValorVariacao.objects.filter(tipo=tipo).count() + 1}
    )
    
    return JsonResponse({'id': valor.id, 'valor': valor.valor, 'criado': criado})


@login_required
def adicionar_tipo_rapido(request, produto_pk):
    usuario_referencia = get_usuario_referencia(request)
    produto = get_object_or_404(Produto, pk=produto_pk, usuario=usuario_referencia)

    if request.method == 'POST':
        tipo_pk = request.POST.get('tipo_pk', '').strip()
        if not tipo_pk:
            messages.error(request, 'Selecione um tipo de variação.')
            return redirect('produto_variacoes', produto_pk=produto_pk)

        try:
            tipo = TipoVariacao.objects.get(pk=int(tipo_pk), usuario=usuario_referencia)
        except (TipoVariacao.DoesNotExist, ValueError):
            messages.error(request, 'Tipo de variação não encontrado.')
            return redirect('produto_variacoes', produto_pk=produto_pk)

        if tipo in produto.tipos_variacao.all():
            messages.info(request, f'Tipo "{tipo.nome}" já está vinculado ao produto.')
        else:
            produto.tipos_variacao.add(tipo)
            LogSistema.objects.create(
                usuario=request.user,
                acao='U',
                modulo='Produtos / Variações',
                descricao=f"Vinculou tipo de variação '{tipo.nome}' ao produto '{produto.nome}'"
            )
            messages.success(request, f'Tipo "{tipo.nome}" vinculado ao produto com sucesso!')

    return redirect('produto_variacoes', produto_pk=produto_pk)


@login_required
def adicionar_valor_rapido(request, produto_pk, tipo_pk):
    usuario_referencia = get_usuario_referencia(request)
    produto = get_object_or_404(Produto, pk=produto_pk, usuario=usuario_referencia)
    tipo = get_object_or_404(TipoVariacao, pk=tipo_pk, usuario=usuario_referencia)

    if request.method == 'POST':
        valor_texto = request.POST.get('valor', '').strip()
        if not valor_texto:
            messages.error(request, 'Informe o valor da variação.')
            return redirect('produto_variacoes', produto_pk=produto_pk)

        valor, criado = ValorVariacao.objects.get_or_create(
            tipo=tipo,
            valor=valor_texto,
        )

        if criado:
            LogSistema.objects.create(
                usuario=request.user,
                acao='C',
                modulo='Produtos / Variações',
                descricao=f"Criou valor '{valor_texto}' para o tipo '{tipo.nome}'"
            )
            messages.success(request, f'Valor "{valor_texto}" criado no tipo "{tipo.nome}".')
        else:
            messages.info(request, f'Valor "{valor_texto}" já existe no tipo "{tipo.nome}".')

    return redirect('produto_variacoes', produto_pk=produto_pk)


@login_required
@require_POST
def produto_variacao_delete(request, pk):
    usuario_referencia = get_usuario_referencia(request)
    variacao = get_object_or_404(ProdutoVariacao, pk=pk, produto__usuario=usuario_referencia)
    produto_pk = variacao.produto.pk

    if variacao.itens_venda.exists():
        messages.error(request, f'Não é possível excluir a variação "{variacao.sku}" pois ela já foi vendida.')
        return redirect('produto_variacoes', produto_pk=produto_pk)
    
    sku = variacao.sku
    variacao.delete()

    LogSistema.objects.create(
        usuario=request.user,
        acao='D',
        modulo='Produtos / Estoque',
        descricao=f"Excluiu a variação SKU '{sku}' do produto ID {produto_pk}"
    )

    messages.success(request, f'Variação "{sku}" excluída!')
    return redirect('produto_variacoes', produto_pk=produto_pk)


@login_required
def entrada_variacao_estoque(request, variacao_pk):
    usuario_referencia = get_usuario_referencia(request)
    variacao = get_object_or_404(
        ProdutoVariacao, pk=variacao_pk, produto__usuario=usuario_referencia
    )
    
    if request.method == 'POST':
        form = EntradaEstoqueForm(request.POST)
        if form.is_valid():
            quantidade = form.cleaned_data['quantidade']
            variacao.quantidade += quantidade
            variacao.save()
            
            MovimentoEstoque.objects.create(
                produto=variacao.produto,
                variacao=variacao,
                quantidade=quantidade,
                tipo='entrada',
                usuario=request.user
            )

            LogSistema.objects.create(
                usuario=request.user,
                acao='U',
                modulo='Produtos / Estoque',
                descricao=f"Entrada de {quantidade} un. na variação SKU '{variacao.sku}' do produto '{variacao.produto.nome}'"
            )
            
            messages.success(request, f'{quantidade} unidades adicionadas ao estoque de "{variacao.sku}"!')
            return redirect('produto_variacoes', produto_pk=variacao.produto.pk)
    else:
        form = EntradaEstoqueForm()
    
    return render(request, 'core/entrada_variacao_estoque.html', {
        'form': form,
        'variacao': variacao
    })


@login_required
def gerar_grade(request, produto_pk):
    usuario_referencia = get_usuario_referencia(request)
    produto = get_object_or_404(Produto, pk=produto_pk, usuario=usuario_referencia)

    tipos = produto.tipos_variacao.all()

    if not tipos.exists():
        messages.error(request, 'Selecione ao menos um tipo de variação no produto.')
        return redirect('editar_produto', id=produto.pk)

    if request.method != 'POST':
        return redirect('produto_variacoes', produto_pk=produto_pk)

    listas_valores = []

    for tipo in tipos:
        ids_selecionados = request.POST.getlist(f'valores_tipo_{tipo.pk}')
        if not ids_selecionados:
            continue

        valores = list(tipo.valores.filter(pk__in=ids_selecionados))
        if valores:
            listas_valores.append(valores)

    if not listas_valores:
        messages.error(request, 'Nenhum valor selecionado para gerar a grade.')
        return redirect('produto_variacoes', produto_pk=produto_pk)

    combinacoes = list(itertools_product(*listas_valores))

    criados = 0
    ja_existiam = 0
    for combo in combinacoes:
        partes_sku = [produto.sku_base or produto.nome[:4].upper().replace(' ', '')]
        for v in combo:
            partes_sku.append(v.valor[:3].upper().replace(' ', ''))
        sku = "-".join(partes_sku)

        if ProdutoVariacao.objects.filter(sku=sku).exists():
            ja_existiam += 1
            continue

        variacao = ProdutoVariacao.objects.create(
            produto=produto,
            sku=sku,
            quantidade=0,
        )
        variacao.valores.set(combo)
        criados += 1

    if criados > 0:
        LogSistema.objects.create(
            usuario=request.user,
            acao='C',
            modulo='Produtos / Estoque',
            descricao=f"Gerou grade automática com {criados} variações para o produto '{produto.nome}'"
        )
        msg = f'{criados} variação(ões) criada(s) com sucesso!'
        if ja_existiam > 0:
            msg += f' {ja_existiam} combinação(ões) já existia(m) e foi(foram) pulada(s).'
        messages.success(request, msg)
    else:
        messages.info(request, 'Todas as combinações selecionadas já existem para este produto.')
    
    return redirect('produto_variacoes', produto_pk=produto_pk)


# =============================================================================
# CORREÇÃO DE ESTOQUE
# =============================================================================

@login_required
@colaborador_tem_permissao('estoque', 'editar')
def corrigir_estoque(request, id):
    usuario_referencia = get_usuario_referencia(request)
    produto = get_object_or_404(Produto, id=id, usuario=usuario_referencia)

    if produto.tem_variacao:
        return redirect('produto_variacoes', produto_pk=produto.pk)

    if request.method == 'POST':
        form = CorrecaoEstoqueForm(request.POST)
        if form.is_valid():
            qtd_correta = form.cleaned_data['quantidade_correta']
            observacao = form.cleaned_data.get('observacao', '')
            qtd_atual = produto.quantidade
            diferenca = qtd_correta - qtd_atual

            if diferenca == 0:
                messages.info(request, 'O estoque já está com a quantidade correta.')
                return redirect('estoque')

            produto.quantidade = qtd_correta
            produto.save()

            MovimentoEstoque.objects.create(
                produto=produto,
                quantidade=diferenca,
                tipo='correcao',
                usuario=request.user
            )

            LogSistema.objects.create(
                usuario=request.user,
                acao='U',
                modulo='Produtos / Estoque',
                descricao=f"Corrigiu estoque do produto '{produto.nome}': {qtd_atual} → {qtd_correta}. Diferença: {diferenca:+d}"
            )

            if diferenca > 0:
                messages.success(request, f'Estoque corrigido! Adicionado {diferenca} un. (era {qtd_atual}, agora {qtd_correta}).')
            else:
                messages.warning(request, f'Estoque corrigido! Removido {abs(diferenca)} un. (era {qtd_atual}, agora {qtd_correta}).')
            return redirect('estoque')
    else:
        form = CorrecaoEstoqueForm()

    return render(request, 'core/corrigir_estoque.html', {
        'form': form,
        'produto': produto,
    })


@login_required
def corrigir_estoque_variacao(request, variacao_pk):
    usuario_referencia = get_usuario_referencia(request)
    variacao = get_object_or_404(
        ProdutoVariacao, pk=variacao_pk, produto__usuario=usuario_referencia
    )

    if request.method == 'POST':
        form = CorrecaoEstoqueForm(request.POST)
        if form.is_valid():
            qtd_correta = form.cleaned_data['quantidade_correta']
            observacao = form.cleaned_data.get('observacao', '')
            qtd_atual = variacao.quantidade
            diferenca = qtd_correta - qtd_atual

            if diferenca == 0:
                messages.info(request, 'O estoque já está com a quantidade correta.')
                return redirect('produto_variacoes', produto_pk=variacao.produto.pk)

            variacao.quantidade = qtd_correta
            variacao.save()

            MovimentoEstoque.objects.create(
                produto=variacao.produto,
                variacao=variacao,
                quantidade=diferenca,
                tipo='correcao',
                usuario=request.user
            )

            LogSistema.objects.create(
                usuario=request.user,
                acao='U',
                modulo='Produtos / Estoque',
                descricao=f"Corrigiu estoque da variação SKU '{variacao.sku}': {qtd_atual} → {qtd_correta}. Diferença: {diferenca:+d}"
            )

            if diferenca > 0:
                messages.success(request, f'Estoque corrigido! Adicionado {diferenca} un. (era {qtd_atual}, agora {qtd_correta}).')
            else:
                messages.warning(request, f'Estoque corrigido! Removido {abs(diferenca)} un. (era {qtd_atual}, agora {qtd_correta}).')
            return redirect('produto_variacoes', produto_pk=variacao.produto.pk)
    else:
        form = CorrecaoEstoqueForm()

    return render(request, 'core/corrigir_estoque_variacao.html', {
        'form': form,
        'variacao': variacao,
    })


# =============================================================================
# ESTOQUE BAIXO (PÁGINA COMPLETA)
# =============================================================================

@login_required
def estoque_baixo(request):
    from django.db.models import Max, Q
    from datetime import timedelta

    usuario_referencia = get_usuario_referencia(request)

    # Buscar configuracao de estoque baixo
    from .models import ConfigEstoqueBaixo
    config_estoque, _ = ConfigEstoqueBaixo.objects.get_or_create(
        usuario=usuario_referencia,
        defaults={
            'nome_empresa': usuario_referencia.get_full_name() or usuario_referencia.username,
            'limite_estoque_baixo': 5,
            'dias_movimentacao': 30,
        }
    )

    filtro_dias = request.GET.get('dias', '')
    limite = int(request.GET.get('limite', config_estoque.limite_estoque_baixo))

    # Produtos sem grade com estoque baixo
    produtos_sem_grade = Produto.objects.filter(
        usuario=usuario_referencia,
        tem_variacao=False,
        quantidade__lte=limite
    )

    # Variacoes (SKUs) com estoque baixo
    variacoes_baixo = ProdutoVariacao.objects.filter(
        produto__usuario=usuario_referencia,
        ativo=True,
        quantidade__lte=limite
    ).select_related('produto')

    # Montar lista unica
    itens = []

    for p in produtos_sem_grade:
        ultimo_mov = MovimentoEstoque.objects.filter(
            produto=p, variacao__isnull=True
        ).aggregate(ultima=Max('data'))['ultima']

        itens.append({
            'nome': p.nome,
            'sku': None,
            'variacao': None,
            'quantidade': p.quantidade,
            'produto_id': p.pk,
            'url': f'/estoque/editar/{p.pk}/',
            'ultima_movimentacao': ultimo_mov,
        })

    for v in variacoes_baixo:
        ultimo_mov = MovimentoEstoque.objects.filter(
            variacao=v
        ).aggregate(ultima=Max('data'))['ultima']

        itens.append({
            'nome': v.produto.nome,
            'sku': v.sku,
            'variacao': v.descricao_variacao,
            'quantidade': v.quantidade,
            'produto_id': v.produto.pk,
            'url': f'/produto/{v.produto.pk}/variacao/',
            'ultima_movimentacao': ultimo_mov,
        })

    # Filtrar por dias da ultima movimentacao
    if filtro_dias and filtro_dias != 'todas':
        try:
            dias = int(filtro_dias)
            corte = timezone.now() - timedelta(days=dias)
            itens = [
                i for i in itens
                if i['ultima_movimentacao'] and i['ultima_movimentacao'] >= corte
            ]
        except (ValueError, TypeError):
            pass

    itens.sort(key=lambda x: x['quantidade'])

    context = {
        'itens': itens,
        'total': len(itens),
        'filtro_dias': filtro_dias,
        'limite': limite,
    }
    return render(request, 'core/estoque_baixo.html', context)


# =============================================================================
# ORCAMENTOS
# =============================================================================

def _verificar_expiracao_orcamentos(usuario_referencia):
    """Atualiza para 'expirado' orcamentos com validade vencida."""
    Orcamento.objects.filter(
        usuario=usuario_referencia,
        status__in=['rascunho', 'pendente'],
        validade__lt=date.today()
    ).update(status='expirado')


@login_required
def lista_orcamentos(request):
    from django.db.models import Q

    usuario_referencia = get_usuario_referencia(request)
    _verificar_expiracao_orcamentos(usuario_referencia)

    status_filter = request.GET.get('status', '')

    orcamentos = Orcamento.objects.filter(
        usuario=usuario_referencia
    ).order_by('-data')

    if status_filter:
        orcamentos = orcamentos.filter(status=status_filter)

    context = {
        'orcamentos': orcamentos,
        'status_filter': status_filter,
        'status_choices': Orcamento.STATUS_CHOICES,
    }
    return render(request, 'core/lista_orcamentos.html', context)


@login_required
def criar_orcamento(request):
    from datetime import timedelta
    usuario_referencia = get_usuario_referencia(request)

    config_estoque, _ = ConfigEstoqueBaixo.objects.get_or_create(
        usuario=usuario_referencia,
        defaults={
            'nome_empresa': usuario_referencia.get_full_name() or usuario_referencia.username,
        }
    )

    if request.method == 'POST':
        form = OrcamentoForm(request.POST)
        if form.is_valid():
            orcamento = form.save(commit=False)
            orcamento.total = 0
            orcamento.usuario = usuario_referencia
            orcamento.usuario_executante = request.user

            if not orcamento.validade:
                orcamento.validade = date.today() + timedelta(days=config_estoque.dias_validade_orcamento)

            orcamento.save()

            LogSistema.objects.create(
                usuario=request.user,
                acao='C',
                modulo='Orçamentos',
                descricao=f"Criou orçamento #{orcamento.id} para o cliente '{orcamento.cliente}'"
            )

            messages.success(request, 'Orçamento criado com sucesso!')
            return redirect('adicionar_item_orcamento', orcamento_id=orcamento.id)
    else:
        form = OrcamentoForm(initial={
            'validade': date.today() + timedelta(days=config_estoque.dias_validade_orcamento),
        })

    return render(request, 'core/orcamento_form.html', {'form': form})


@login_required
def adicionar_item_orcamento(request, orcamento_id):
    usuario_referencia = get_usuario_referencia(request)

    orcamento = get_object_or_404(
        Orcamento,
        pk=orcamento_id,
        usuario=usuario_referencia
    )

    if request.method == 'POST':
        form = ItemOrcamentoForm(request.POST, usuario=usuario_referencia)
        if form.is_valid():
            item = form.save(commit=False)
            item.orcamento = orcamento

            variacao = form.cleaned_data.get('variacao')
            if variacao:
                item.variacao = variacao
                item.preco_unitario = variacao.preco_efetivo
            else:
                item.preco_unitario = item.produto.preco

            item.save()

            orcamento.total = sum(item.subtotal for item in orcamento.itemorcamento_set.all())
            orcamento.save()

            desc_item = item.produto.nome
            if variacao:
                desc_item += f" [{variacao.sku}]"

            LogSistema.objects.create(
                usuario=request.user,
                acao='U',
                modulo='Orçamentos',
                descricao=f"Adicionou {item.quantidade}x do produto '{desc_item}' ao orçamento #{orcamento.id}"
            )

            messages.success(request, 'Item adicionado com sucesso!')
            return redirect('adicionar_item_orcamento', orcamento_id=orcamento.id)
    else:
        form = ItemOrcamentoForm(usuario=usuario_referencia)

    produtos = Produto.objects.filter(usuario=usuario_referencia)
    itens = orcamento.itemorcamento_set.select_related('produto', 'variacao').all()

    return render(request, 'core/orcamento_itens.html', {
        'orcamento': orcamento,
        'form': form,
        'itens': itens,
        'produtos': produtos,
    })


@login_required
def remover_item_orcamento(request, pk):
    usuario_referencia = get_usuario_referencia(request)
    item = get_object_or_404(ItemOrcamento, pk=pk, orcamento__usuario=usuario_referencia)
    orcamento_id = item.orcamento.pk
    item.delete()

    orcamento = Orcamento.objects.get(pk=orcamento_id)
    orcamento.total = sum(item.subtotal for item in orcamento.itemorcamento_set.all())
    orcamento.save()

    messages.success(request, 'Item removido com sucesso!')
    return redirect('adicionar_item_orcamento', orcamento_id=orcamento_id)


@login_required
def finalizar_orcamento(request, orcamento_id):
    usuario_referencia = get_usuario_referencia(request)
    orcamento = get_object_or_404(Orcamento, pk=orcamento_id, usuario=usuario_referencia)

    itens = orcamento.itemorcamento_set.all()
    if not itens.exists():
        messages.error(request, 'Não é possível finalizar um orçamento sem itens!')
        return redirect('adicionar_item_orcamento', orcamento_id=orcamento.id)

    if request.method == 'POST':
        desconto_percentual = request.POST.get('desconto_percentual', '0')
        desconto_valor = request.POST.get('desconto_valor', '0')

        try:
            desconto_percentual = Decimal(desconto_percentual)
            desconto_valor = Decimal(desconto_valor)
        except (ValueError, TypeError):
            desconto_percentual = Decimal(0)
            desconto_valor = Decimal(0)

        if desconto_percentual > 0:
            desconto_final = (orcamento.total * desconto_percentual) / 100
        else:
            desconto_final = desconto_valor

        if desconto_final > orcamento.total:
            messages.error(request, 'Desconto não pode ser maior que o total do orçamento!')
            return render(request, 'core/finalizar_orcamento.html', {
                'orcamento': orcamento,
                'itens': itens,
            })

        orcamento.desconto = desconto_final
        orcamento.total_com_desconto = orcamento.total - desconto_final
        orcamento.status = 'pendente'
        orcamento.save()

        LogSistema.objects.create(
            usuario=request.user,
            acao='U',
            modulo='Orçamentos',
            descricao=f"Finalizou orçamento #{orcamento.id} para '{orcamento.cliente}'. Total: R$ {orcamento.total_com_desconto}"
        )

        messages.success(request, 'Orçamento finalizado com sucesso!')
        return redirect('lista_orcamentos')

    return render(request, 'core/finalizar_orcamento.html', {
        'orcamento': orcamento,
        'itens': itens,
    })


@login_required
def cancelar_orcamento(request, orcamento_id):
    usuario_referencia = get_usuario_referencia(request)
    orcamento = get_object_or_404(Orcamento, pk=orcamento_id, usuario=usuario_referencia)

    id_cancelado = orcamento.id
    cliente_cancelado = orcamento.cliente
    orcamento.delete()

    LogSistema.objects.create(
        usuario=request.user,
        acao='D',
        modulo='Orçamentos',
        descricao=f"Cancelou e excluiu o orçamento #{id_cancelado} do cliente '{cliente_cancelado}'"
    )

    messages.warning(request, f'Orçamento #{id_cancelado} cancelado com sucesso!')
    return redirect('lista_orcamentos')


@login_required
def alterar_status_orcamento(request, orcamento_id):
    usuario_referencia = get_usuario_referencia(request)
    orcamento = get_object_or_404(Orcamento, pk=orcamento_id, usuario=usuario_referencia)

    if request.method == 'POST':
        novo_status = request.POST.get('status')
        if novo_status in dict(Orcamento.STATUS_CHOICES):
            orcamento.status = novo_status
            orcamento.save()

            LogSistema.objects.create(
                usuario=request.user,
                acao='U',
                modulo='Orçamentos',
                descricao=f"Alterou status do orçamento #{orcamento.id} para '{orcamento.get_status_display()}'"
            )
            messages.success(request, f'Status alterado para {orcamento.get_status_display()}.')

    return redirect('lista_orcamentos')


@login_required
def ver_orcamento(request, orcamento_id):
    usuario_referencia = get_usuario_referencia(request)
    orcamento = get_object_or_404(Orcamento, pk=orcamento_id, usuario=usuario_referencia)

    if orcamento.validade and orcamento.validade < date.today() and orcamento.status in ['rascunho', 'pendente']:
        orcamento.status = 'expirado'
        orcamento.save()

    itens = orcamento.itemorcamento_set.select_related('produto', 'variacao').all()

    return render(request, 'core/ver_orcamento.html', {
        'orcamento': orcamento,
        'itens': itens,
    })


@login_required
def imprimir_orcamento(request, orcamento_id):
    usuario_referencia = get_usuario_referencia(request)
    orcamento = get_object_or_404(Orcamento, pk=orcamento_id, usuario=usuario_referencia)
    itens = orcamento.itemorcamento_set.select_related('produto', 'variacao').all()
    try:
        perfil = Perfil.objects.get(usuario=usuario_referencia)
    except Perfil.DoesNotExist:
        perfil = None

    return render(request, 'core/imprimir_orcamento.html', {
        'orcamento': orcamento,
        'itens': itens,
        'perfil_empresa': perfil,
    })


@login_required
def imprimir_orcamento_cupom(request, orcamento_id):
    usuario_referencia = get_usuario_referencia(request)
    orcamento = get_object_or_404(Orcamento, pk=orcamento_id, usuario=usuario_referencia)
    itens = orcamento.itemorcamento_set.select_related('produto', 'variacao').all()
    try:
        perfil = Perfil.objects.get(usuario=usuario_referencia)
    except Perfil.DoesNotExist:
        perfil = None

    return render(request, 'core/imprimir_orcamento_cupom.html', {
        'orcamento': orcamento,
        'itens': itens,
        'perfil_empresa': perfil,
    })


@login_required
def pdf_orcamento(request, orcamento_id):
    from django.http import HttpResponse
    from django.utils import formats
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm, cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from core.models import Perfil

    usuario_referencia = get_usuario_referencia(request)
    orcamento = get_object_or_404(Orcamento, pk=orcamento_id, usuario=usuario_referencia)
    itens = orcamento.itemorcamento_set.select_related('produto', 'variacao').all()

    try:
        perfil = Perfil.objects.get(usuario=usuario_referencia)
    except Perfil.DoesNotExist:
        perfil = None

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    elements = []

    # Header com dados da empresa
    if perfil and perfil.logotipo:
        try:
            img = Image(perfil.logotipo.path, width=4*cm, height=2*cm)
            img.hAlign = 'CENTER'
            elements.append(img)
            elements.append(Spacer(1, 6))
        except Exception:
            pass

    if perfil and perfil.Empresas:
        empresa_style = ParagraphStyle('Empresa', parent=styles['Normal'], fontSize=12, alignment=1, spaceAfter=2)
        elements.append(Paragraph(perfil.Empresas, empresa_style))
    if perfil and perfil.CNPJ:
        cnpj_style = ParagraphStyle('CNPJ', parent=styles['Normal'], fontSize=9, alignment=1, spaceAfter=2)
        elements.append(Paragraph(f"CNPJ: {perfil.CNPJ}", cnpj_style))
    if perfil and perfil.telefone:
        tel_style = ParagraphStyle('Tel', parent=styles['Normal'], fontSize=9, alignment=1, spaceAfter=6)
        elements.append(Paragraph(f"Tel: {perfil.telefone}", tel_style))

    title_style = ParagraphStyle('Title2', parent=styles['Title'], fontSize=18, spaceAfter=6)
    elements.append(Paragraph(f"ORÇAMENTO #{orcamento.id:06d}", title_style))
    elements.append(Spacer(1, 12))

    # Info
    info_style = ParagraphStyle('Info', parent=styles['Normal'], fontSize=10, leading=14)
    elements.append(Paragraph(f"<b>Cliente:</b> {orcamento.cliente}", info_style))
    elements.append(Paragraph(f"<b>Data:</b> {formats.date_format(orcamento.data, 'd/m/Y H:i')}", info_style))
    if orcamento.validade:
        elements.append(Paragraph(f"<b>Validade:</b> {formats.date_format(orcamento.validade, 'd/m/Y')}", info_style))
    elements.append(Paragraph(f"<b>Status:</b> {orcamento.get_status_display()}", info_style))
    if orcamento.observacao:
        elements.append(Paragraph(f"<b>Observação:</b> {orcamento.observacao}", info_style))
    elements.append(Spacer(1, 12))

    # Items table
    data = [['Produto', 'SKU', 'Qtd', 'Preço Unit.', 'Subtotal']]
    for item in itens:
        sku = item.variacao.sku if item.variacao else '-'
        nome = item.produto.nome
        if item.variacao:
            nome += f" ({item.variacao.descricao_variacao})"
        data.append([
            nome,
            sku,
            str(item.quantidade),
            f"R$ {item.preco_unitario:,.2f}",
            f"R$ {item.subtotal:,.2f}",
        ])

    # Totals
    data.append(['', '', '', 'Subtotal:', f"R$ {orcamento.total:,.2f}"])
    if orcamento.desconto > 0:
        data.append(['', '', '', 'Desconto:', f"- R$ {orcamento.desconto:,.2f}"])
        data.append(['', '', '', 'TOTAL:', f"R$ {orcamento.total_com_desconto:,.2f}"])

    table = Table(data, colWidths=[7*cm, 2.5*cm, 1.5*cm, 3*cm, 3*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a90d9')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f8f9fa')]),
        ('FONTSIZE', (-2, -1), (-1, -1), 11),
        ('SPAN', (0, -1), (3, -1)),
    ]))
    elements.append(table)

    doc.build(elements)

    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="orcamento_{orcamento.id:06d}.pdf"'
    return response


@login_required
@colaborador_tem_permissao('maquina_cartao', 'ver')
def lista_maquinas_cartao(request):
    maquinas = MaquinaCartao.objects.all()
    return render(request, 'core/maquina_cartao_lista.html', {'maquinas': maquinas})


def _maquina_form_context(form):
    taxa_parcelas = []
    sem_juros_set = set()
    cleaned = form.cleaned_data if form.is_bound else {}
    raw = cleaned.get('parcelas_sem_juros', '')
    if raw:
        sem_juros_set = {int(x.strip()) for x in raw.split(',') if x.strip().isdigit()}
    elif form.instance and form.instance.pk:
        sem_juros_set = set(form.instance.parcelas_sem_juros_list())

    sj_checks = []
    for n in range(1, 13):
        checked = 'checked' if n in sem_juros_set else ''
        sj_checks.append({
            'parcela': n,
            'id': f'id_parcelas_sem_juros_{n}',
            'widget': f'<input type="checkbox" class="form-check-input parcela-sj" id="id_parcelas_sem_juros_{n}" name="parcelas_sem_juros_{n}" {checked}>'
        })
        taxa_parcelas.append({
            'parcela': n,
            'field': form[f'taxa_{n}x']
        })

    return {'parcelas_sem_juros_checks': sj_checks, 'taxa_parcelas': taxa_parcelas}


@login_required
@colaborador_tem_permissao('maquina_cartao', 'editar')
def adicionar_maquina_cartao(request):
    if request.method == 'POST':
        form = MaquinaCartaoForm(request.POST)
        if form.is_valid():
            maquina = form.save()

            LogSistema.objects.create(
                usuario=request.user,
                acao='C',
                modulo='Vendas',
                descricao=f"Criou a máquina de cartão '{maquina.nome}'"
            )

            messages.success(request, f'Máquina "{maquina.nome}" cadastrada com sucesso!')
            return redirect('lista_maquinas_cartao')
    else:
        form = MaquinaCartaoForm()
    ctx = {'form': form, 'titulo': 'Nova Máquina de Cartão'}
    ctx.update(_maquina_form_context(form))
    return render(request, 'core/maquina_cartao_form.html', ctx)


@login_required
@colaborador_tem_permissao('maquina_cartao', 'editar')
def editar_maquina_cartao(request, pk):
    maquina = get_object_or_404(MaquinaCartao, pk=pk)
    if request.method == 'POST':
        form = MaquinaCartaoForm(request.POST, instance=maquina)
        if form.is_valid():
            form.save()

            LogSistema.objects.create(
                usuario=request.user,
                acao='U',
                modulo='Vendas',
                descricao=f"Editou a máquina de cartão '{maquina.nome}'"
            )

            messages.success(request, f'Máquina "{maquina.nome}" atualizada!')
            return redirect('lista_maquinas_cartao')
    else:
        form = MaquinaCartaoForm(instance=maquina)
    ctx = {'form': form, 'titulo': f'Editar: {maquina.nome}'}
    ctx.update(_maquina_form_context(form))
    return render(request, 'core/maquina_cartao_form.html', ctx)


@login_required
@colaborador_tem_permissao('maquina_cartao', 'excluir')
@require_POST
def excluir_maquina_cartao(request, pk):
    maquina = get_object_or_404(MaquinaCartao, pk=pk)
    nome = maquina.nome
    maquina.delete()

    LogSistema.objects.create(
        usuario=request.user,
        acao='D',
        modulo='Vendas',
        descricao=f"Excluiu a máquina de cartão '{nome}'"
    )

    messages.success(request, f'Máquina "{nome}" excluída!')
    return redirect('lista_maquinas_cartao')


@login_required
def api_maquina_taxa(request, pk):
    from django.http import JsonResponse
    maquina = get_object_or_404(MaquinaCartao, pk=pk)
    forma = request.GET.get('forma', '')
    parcela = int(request.GET.get('parcela', '1'))
    taxa = maquina.get_taxa_por_forma(forma, parcela)
    sem_juros = maquina.is_parcela_sem_juros(parcela) if forma == 'cartao_credito' else False
    return JsonResponse({
        'taxa': str(taxa),
        'sem_juros': sem_juros,
        'parcelas_sem_juros': maquina.parcelas_sem_juros,
    })