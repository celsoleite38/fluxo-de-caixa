# Create your models here.
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.contrib.auth import get_user_model
#from .models import ItemVenda

class Usuario(AbstractUser):
    telefone = models.CharField(max_length=15, blank=True, null=True)
    
    def __str__(self):
        return self.get_full_name() or self.username

class Categoria(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=1, choices=(('E', 'Entrada'), ('S', 'Saída')))
    
    def __str__(self):
        return self.nome

class Produto(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    quantidade = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    
    def __str__(self):
        return f"{self.nome} (R${self.preco})"

class Movimentacao(models.Model):
    TIPO_CHOICES = (
        ('E', 'Entrada'),
        ('S', 'Saída'),
    )
    
    tipo = models.CharField(max_length=1, choices=TIPO_CHOICES)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    descricao = models.TextField()
    data = models.DateField()
    hora = models.TimeField(auto_now_add=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    
    class Meta:
        ordering = ['-data']
    
    def __str__(self):
        return f"{self.get_tipo_display()} - R${self.valor}"

class NotaVenda(models.Model):
    cliente = models.CharField(max_length=100)
    produtos = models.ManyToManyField(Produto, through='ItemVenda')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    data = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"Venda #{self.id} - {self.cliente}"

class ItemVenda(models.Model):
    nota = models.ForeignKey(NotaVenda, on_delete=models.CASCADE)
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    quantidade = models.IntegerField(validators=[MinValueValidator(1)])
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    
    @property
    def subtotal(self):
        """Calcula o subtotal do item (quantidade × preço unitário)"""
        return self.quantidade * self.preco_unitario
    
    def __str__(self):
        return f"{self.quantidade}x {self.produto.nome} - R${self.subtotal}"
    
    def save(self, *args, **kwargs):
        """Garante que o preço unitário seja sempre o preço atual do produto"""
        if not self.preco_unitario:
            self.preco_unitario = self.produto.preco
        super().save(*args, **kwargs)
    
class MovimentoEstoque(models.Model):
    TIPO_CHOICES = (
        ('entrada', 'Entrada'),
        ('saida', 'Saída'),
    )
    
    produto = models.ForeignKey('Produto', on_delete=models.CASCADE)
    quantidade = models.IntegerField()
    tipo = models.CharField(max_length=7, choices=TIPO_CHOICES)
    data = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True)
    
    def __str__(self):
        return f"{self.produto.nome} - {self.quantidade} ({self.tipo})"

