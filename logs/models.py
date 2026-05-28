from django.db import models
from django.contrib.auth.models import User

class LogSistema(models.Model):
    ACOES_CHOICES = [
        ('C', 'Criar / Cadastrar'),
        ('U', 'Editar / Atualizar'),
        ('D', 'Excluir'),
        ('L', 'Login / Acesso'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Usuário")
    data_hora = models.DateTimeField(auto_now_add=True, verbose_name="Data e Hora")
    acao = models.CharField(max_length=1, choices=ACOES_CHOICES, verbose_name="Ação")
    modulo = models.CharField(max_length=100, verbose_name="Módulo / Setor")
    descricao = models.TextField(verbose_name="Descrição da Alteração")

    class Meta:
        verbose_name = "Log do Sistema"
        verbose_name_plural = "Logs do Sistema"
        ordering = ['-data_hora'] # Mostra sempre os mais recentes primeiro

    def __str__(self):
        return f"{self.usuario.username} - {self.get_acao_display()} em {self.modulo}"