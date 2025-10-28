from django.db import models
from django.contrib.auth.models import AbstractUser, User
from django.core.validators import MinValueValidator
from django.contrib.auth import get_user_model







class Categoria(models.Model):
    usuario = models.ForeignKey(User, 
    on_delete=models.SET_NULL, 
    null=True, 
    related_name='%(class)s_executado')
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=1, choices=(('E', 'Entrada'), ('S', 'Saída')))
    
    def __str__(self):
        return self.nome

class Produto(models.Model):
    usuario = models.ForeignKey(User, 
    on_delete=models.SET_NULL, 
    null=True, 
    related_name='%(class)s_executado')
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
    
    FORMA_PAGAMENTO_CHOICES = (
        ('dinheiro', 'Dinheiro'),
        ('cartao_credito', 'Cartão de Crédito'),
        ('cartao_debito', 'Cartão de Débito'),
        ('pix', 'PIX'),
        ('transferencia', 'Transferência Bancária'),
    )
    
    tipo = models.CharField(max_length=1, choices=TIPO_CHOICES)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    descricao = models.TextField()
    data = models.DateField()
    hora = models.TimeField(auto_now_add=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    forma_pagamento = models.CharField(
        max_length=15, 
        choices=FORMA_PAGAMENTO_CHOICES,
        default='dinheiro'
    )

    class Meta:
        ordering = ['-data']
    
    def __str__(self):
        return f"{self.descricao} ({self.get_tipo_display()}) - R${self.valor}"

# models.pyf
class NotaVenda(models.Model):
    FORMA_PAGAMENTO_CHOICES = [
        ('dinheiro', 'Dinheiro'),
        ('cartao_credito', 'Cartão de Crédito'),
        ('cartao_debito', 'Cartão de Débito'),
        ('pix', 'PIX'),
        ('transferencia', 'Transferência Bancária'),
    ]
    
    STATUS_CHOICES = [
        ('aberta', 'Aberta'),
        ('finalizada', 'Finalizada'),
        ('cancelada', 'Cancelada'),
    ]
    
    cliente = models.CharField(max_length=100)
    produtos = models.ManyToManyField(Produto, through='ItemVenda')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # Novos campos
    desconto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_com_desconto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    forma_pagamento = models.CharField(max_length=20, choices=FORMA_PAGAMENTO_CHOICES, blank=False, null=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='aberta')
    data = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notas_venda')
    usuario_executante = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='notas_executadas')
    
    def __str__(self):
        return f"Venda #{self.id} - {self.cliente}"
    
    def get_forma_pagamento_display(self):
        if not self.forma_pagamento:
            return "Não informado"
        for valor, label in self.FORMA_PAGAMENTO_CHOICES:
            if valor == self.forma_pagamento:
                return label
        return 'DEsconhecido'

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
    TIPO_MOVIMENTO = (
        ('cadastro', 'Cadastro Inicial'),
        ('entrada', 'Entrada Avulsa'),
        ('saida', 'Saída'),
    )
    
    produto = models.ForeignKey('Produto', on_delete=models.CASCADE)
    quantidade = models.IntegerField()
    tipo = models.CharField(max_length=8, choices=TIPO_MOVIMENTO)
    data = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='%(class)s_executado'
    )
    
    def __str__(self):
        return f"{self.produto.nome} - {self.quantidade} ({self.tipo})"



class Perfil(models.Model):
    Nome = models.CharField(max_length=100)
    email = models.EmailField(max_length=254, blank=True, null=True)
    CNPJ = models.CharField(max_length=20, blank=True, null=True)
    Empresas = models.CharField(max_length=255, blank=True, null=True)
    endereco = models.CharField(max_length=255, blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    celular = models.CharField(max_length=20, blank=True, null=True)
    logotipo = models.ImageField(upload_to='logos/', blank=True, null=True)

    def __str__(self):
        return f"{self.user.nome} - Perfil"
