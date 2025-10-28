from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    # Removido: path('accounts/', include('django.contrib.auth.urls')),
    # Configuração explícita para login e logout com o template customizado
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
    
    path('estoque/', views.lista_produtos, name='estoque'),
    path('produto/adicionar/', views.adicionar_produto, name='adicionar_produto'),
    path('estoque/excluir/<int:id>/', views.excluir_produto, name='excluir_produto'),
    path('estoque/editar/<int:id>/',views.editar_produto , name='editar_produto'),
    path('estoque/entrada/<int:id>/', views.entrada_estoque, name='entrada_estoque'),
    path('estoque/historico/', views.historico_estoque, name='historico_estoque'),

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
]