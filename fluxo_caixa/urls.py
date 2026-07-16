from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    path('colaboradores/', include('colaborador.urls')),
    path('', views.dashboard, name='dashboard'),
    path('movimentacoes/<str:tipo>/', views.lista_movimentacoes, name='lista_movimentacoes'),
    path('entradas/', views.lista_movimentacoes, {'tipo': 'E'}, name='lista_movimentacoes'),
    path('saidas/', views.lista_movimentacoes, {'tipo': 'S'}, name='lista_movimentacoes'),
    path('movimentacao/adicionar/', views.adicionar_movimentacao, name='adicionar_movimentacao'),
    path('movimentacao/editar/<int:pk>/', views.editar_movimentacao, name='editar_movimentacao'),
    path('movimentacao/excluir/<int:pk>/', views.excluir_movimentacao, name='excluir_movimentacao'),
    path('relatorios/', views.relatorios, name='relatorios'),
    
    path('estoque/baixo/', views.estoque_baixo, name='estoque_baixo'),
    path('estoque/', views.lista_produtos, name='estoque'),
    path('produto/adicionar/', views.adicionar_produto, name='adicionar_produto'),
    path('estoque/excluir/<int:id>/', views.excluir_produto, name='excluir_produto'),
    path('estoque/editar/<int:id>/', views.editar_produto, name='editar_produto'),
    path('estoque/entrada/<int:id>/', views.entrada_estoque, name='entrada_estoque'),
    path('estoque/corrigir/<int:id>/', views.corrigir_estoque, name='corrigir_estoque'),
    path('estoque/historico/', views.historico_estoque, name='historico_estoque'),

    # Variações (Grade)
    path('variacao/tipos/', views.tipo_variacao_list, name='tipo_variacao_list'),
    path('variacao/tipos/novo/', views.tipo_variacao_create, name='tipo_variacao_create'),
    path('variacao/tipos/<int:pk>/editar/', views.tipo_variacao_edit, name='tipo_variacao_edit'),
    path('variacao/tipos/<int:pk>/excluir/', views.tipo_variacao_delete, name='tipo_variacao_delete'),
    path('variacao/tipos/<int:pk>/valores/', views.tipo_variacao_valores, name='tipo_variacao_valores'),
    path('variacao/valores/<int:pk>/excluir/', views.valor_variacao_delete, name='valor_variacao_delete'),
    path('produto/<int:produto_pk>/variacao/', views.produto_variacoes, name='produto_variacoes'),
    path('produto/<int:produto_pk>/tipo/<int:tipo_pk>/valor-rapido/', views.adicionar_valor_rapido, name='adicionar_valor_rapido'),
    path('produto/variacao/<int:pk>/excluir/', views.produto_variacao_delete, name='produto_variacao_delete'),
    path('produto/variacao/<int:variacao_pk>/entrada/', views.entrada_variacao_estoque, name='entrada_variacao_estoque'),
    path('produto/variacao/<int:variacao_pk>/corrigir/', views.corrigir_estoque_variacao, name='corrigir_estoque_variacao'),
    path('produto/<int:produto_pk>/gerar-grade/', views.gerar_grade, name='gerar_grade'),

    path('venda/<int:nota_id>/', views.ver_nota_venda, name='nota_venda'),
    path('venda/nova/', views.criar_nota_venda, name='criar_nota_venda'),
    path('venda/<int:nota_id>/itens/', views.adicionar_item_venda, name='adicionar_item_venda'),
    path('venda/<int:nota_id>/finalizar/', views.finalizar_venda, name='finalizar_venda'),
    path('venda/<int:nota_id>/cancelar/', views.cancelar_venda, name='cancelar_venda'),
    path('venda/aplicar-desconto/', views.aplicar_desconto_ajax, name='aplicar_desconto_ajax'),
    path('vendas/remover-item/<int:pk>/', views.remover_item_venda, name='remover_item_venda'),
    path('venda/recibo/<int:nota_id>/imprimir/', views.imprimir_recibo_venda, name='imprimir_recibo_venda'),
    path('venda/<int:nota_id>/', views.ver_nota_venda, name='nota_venda'),

    path("relatorios/imprimir_entradas/", views.imprimir_entradas, name="imprimir_entradas"),
    path("relatorios/imprimir_saidas/", views.imprimir_saidas, name="imprimir_saidas"),
    
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
    path('password_change/', auth_views.PasswordChangeView.as_view(template_name='registration/password_change_form.html'), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='registration/password_change_done.html'), name='password_change_done'),
    path('accounts/register/', views.register, name='register'),

    path('vendas/todas/', views.lista_todas_vendas, name='lista_todas_vendas'),
    path('vendas/imprimir-lista/', views.imprimir_lista_vendas, name='imprimir_lista_vendas'),

    # Orçamentos
    path('orcamentos/', views.lista_orcamentos, name='lista_orcamentos'),
    path('orcamento/novo/', views.criar_orcamento, name='criar_orcamento'),
    path('orcamento/<int:orcamento_id>/', views.ver_orcamento, name='ver_orcamento'),
    path('orcamento/<int:orcamento_id>/itens/', views.adicionar_item_orcamento, name='adicionar_item_orcamento'),
    path('orcamento/<int:orcamento_id>/finalizar/', views.finalizar_orcamento, name='finalizar_orcamento'),
    path('orcamento/<int:orcamento_id>/cancelar/', views.cancelar_orcamento, name='cancelar_orcamento'),
    path('orcamento/<int:orcamento_id>/status/', views.alterar_status_orcamento, name='alterar_status_orcamento'),
    path('orcamento/<int:orcamento_id>/imprimir/', views.imprimir_orcamento, name='imprimir_orcamento'),
    path('orcamento/<int:orcamento_id>/cupom/', views.imprimir_orcamento_cupom, name='imprimir_orcamento_cupom'),
    path('orcamento/<int:orcamento_id>/pdf/', views.pdf_orcamento, name='pdf_orcamento'),
    path('orcamento/remover-item/<int:pk>/', views.remover_item_orcamento, name='remover_item_orcamento'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
