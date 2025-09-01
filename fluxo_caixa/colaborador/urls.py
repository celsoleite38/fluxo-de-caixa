from django.urls import path
from . import views

app_name = 'colaborador'

urlpatterns = [
    path('', views.colaborador_list, name='colaborador_list'),
    path('novo/', views.colaborador_create, name='colaborador_create'),
    path('editar/<int:user_id>/', views.colaborador_edit, name='colaborador_edit'),
    path('excluir/<int:user_id>/', views.colaborador_delete, name='colaborador_delete'),
    path('solicitar-mais/', views.request_more_users, name='request_more_users'),
    path('solicitacoes/', views.user_requests, name='user_requests'),
    path('aprovar/<int:request_id>/', views.approve_request, name='approve_request'),
    
    path('vendas/', views.vendas, name='vendas'),
    path('estoque/', views.estoque, name='estoque'),
    #path('financeiro/', views.financeiro, name='financeiro'),
    #path('relatorios/', views.relatorios, name='relatorios'),
    path('permissoes/', views.gerenciar_permissoes, name='gerenciar_permissoes'),
    path('permissoes/colaborador/<int:colaborador_id>/', views.gerenciar_permissoes, name='gerenciar_permissoes_colaborador'),
]