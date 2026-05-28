from django.contrib import admin
from .models import LogSistema

@admin.register(LogSistema)
class LogSistemaAdmin(admin.ModelAdmin):
    # Colunas que vão aparecer na listagem
    list_display = ('data_hora', 'usuario', 'get_acao_badge', 'modulo', 'descricao')
    
    # Filtros na lateral direita
    list_filter = ('acao', 'modulo', 'usuario', 'data_hora')
    
    # Barra de pesquisa por usuário ou descrição
    search_fields = ('usuario__username', 'modulo', 'descricao')
    
    # Desabilita a permissão de editar ou criar logs manualmente pelo admin por segurança
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False

    # Apenas um detalhe visual para mapear a ação por extenso na tabela
    def get_acao_badge(self, obj):
        return obj.get_acao_display()
    get_acao_badge.short_description = 'Ação'