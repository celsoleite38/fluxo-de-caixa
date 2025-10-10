from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class Colaborador(models.Model):
    usuario_principal = models.ForeignKey(User, on_delete=models.CASCADE, related_name='colaboradores')
    usuario_colaborador = models.OneToOneField(User, on_delete=models.CASCADE, related_name='pertence_a')
    data_criacao = models.DateTimeField(auto_now_add=True)
    ativo = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Colaborador: {self.usuario_colaborador.username} → {self.usuario_principal.username}"
    
    class Meta:
        verbose_name = 'Colaborador'
        verbose_name_plural = 'Colaboradores'
        unique_together = ['usuario_principal', 'usuario_colaborador']



class UserLimit(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_limit')
    max_users = models.PositiveIntegerField(
        default=2,
        verbose_name='Máximo de Colaboradores',
        help_text='Número máximo de colaboradores que este usuário pode criar'
    )
    can_create_users = models.BooleanField(
        default=True,
        verbose_name='Pode criar colaboradores',
        help_text='Se este usuário tem permissão para criar novos colaboradores'
    )
    
    def __str__(self):
        return f"Limite de {self.user.username}: {self.max_users} colaboradores"
    
    class Meta:
        verbose_name = 'Limite de Colaboradores'
        verbose_name_plural = 'Limites de Colaboradores'

class UserCreationRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='creation_requests')
    requested_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_requests')
    approved_at = models.DateTimeField(null=True, blank=True)
    additional_users_requested = models.PositiveIntegerField(default=1)
    
    def __str__(self):
        return f"Solicitação de {self.user.username} - {self.additional_users_requested} usuários"
    
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    is_usuario_principal = models.BooleanField(default=False, verbose_name='É usuário principal')
    pode_gerenciar_colaboradores = models.BooleanField(default=False, verbose_name='Pode gerenciar colaboradores')
    
    def __str__(self):
        return f"Perfil de {self.user.username}"
    

class PermissaoColaborador(models.Model):
    MODULOS_CHOICES = [
        ('vendas', 'Vendas'),
        ('estoque', 'Estoque'),
        ('financeiro', 'Financeiro'),
        ('clientes', 'Clientes'),
        ('relatorios', 'Relatórios'),
    ]
    
    colaborador = models.ForeignKey(Colaborador, on_delete=models.CASCADE, related_name='permissoes')
    modulo = models.CharField(max_length=20, choices=MODULOS_CHOICES)
    pode_ver = models.BooleanField(default=False, verbose_name='Pode Ver')
    pode_editar = models.BooleanField(default=False, verbose_name='Pode Editar')
    pode_excluir = models.BooleanField(default=False, verbose_name='Pode Excluir')
    
    class Meta:
        unique_together = ['colaborador', 'modulo']