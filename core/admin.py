from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import ConfigEstoqueBaixo
from colaborador.models import Colaborador


class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ('username', 'email', 'name', 'telefone', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Informações Pessoais', {'fields': ('first_name', 'last_name', 'email', 'telefone')}),
        ('Permissões', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Datas Importantes', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'first_name', 'last_name', 'telefone', 'is_staff', 'is_active'),
        }),
    )
    search_fields = ('username', 'first_name', 'last_name', 'email', 'telefone')
    ordering = ('username',)


@admin.register(ConfigEstoqueBaixo)
class ConfigEstoqueBaixoAdmin(admin.ModelAdmin):
    list_display = ('nome_empresa', 'usuario', 'limite_estoque_baixo', 'dias_movimentacao', 'atualizado_em')
    list_filter = ('limite_estoque_baixo', 'dias_movimentacao')
    search_fields = ('nome_empresa', 'usuario__username')
    readonly_fields = ('criado_em', 'atualizado_em')
    ordering = ('nome_empresa',)

    fieldsets = (
        (None, {
            'fields': ('usuario', 'nome_empresa')
        }),
        ('Limites de Estoque', {
            'fields': ('limite_estoque_baixo', 'dias_movimentacao'),
            'description': 'Configure os limites de estoque baixo para esta empresa/usuário'
        }),
        ('Orçamentos', {
            'fields': ('dias_validade_orcamento',),
            'description': 'Dias de validade padrão para orçamentos desta empresa'
        }),
        ('Datas', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        ids_colaboradores = Colaborador.objects.values_list('usuario_colaborador_id', flat=True)
        return qs.exclude(usuario_id__in=ids_colaboradores)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'usuario':
            ids_colaboradores = Colaborador.objects.values_list('usuario_colaborador_id', flat=True)
            kwargs['queryset'] = User.objects.exclude(pk__in=ids_colaboradores)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

