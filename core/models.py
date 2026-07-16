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


class TipoVariacao(models.Model):
    """Ex: Tamanho, Cor, Sabor, Estilo, Gênero"""
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tipos_variacao')
    nome = models.CharField(max_length=50)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('usuario', 'nome')
        ordering = ['ordem']

    def __str__(self):
        return self.nome


class ValorVariacao(models.Model):
    """Ex: 38, 40, Vermelho, Preto, Tradicional"""
    tipo = models.ForeignKey(TipoVariacao, on_delete=models.CASCADE, related_name='valores')
    valor = models.CharField(max_length=50)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('tipo', 'valor')
        ordering = ['ordem']

    def __str__(self):
        return f"{self.tipo.nome}: {self.valor}"


class Produto(models.Model):
    usuario = models.ForeignKey(User, 
    on_delete=models.SET_NULL, 
    null=True, 
    related_name='%(class)s_executado')
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    quantidade = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    tem_variacao = models.BooleanField(default=False)
    tipos_variacao = models.ManyToManyField(TipoVariacao, blank=True, related_name='produtos')
    sku_base = models.CharField(max_length=20, blank=True, default='')
    unidade_medida = models.CharField(max_length=20, blank=True, default='UN')

    @property
    def quantidade_total(self):
        if self.tem_variacao:
            return sum(v.quantidade for v in self.variacoes.filter(ativo=True))
        return self.quantidade

    @property
    def preco_minimo(self):
        if self.tem_variacao:
            precos = [v.preco_efetivo for v in self.variacoes.filter(ativo=True)]
            return min(precos) if precos else self.preco
        return self.preco

    def __str__(self):
        if self.tem_variacao:
            return f"{self.nome} (Grade)"
        return f"{self.nome} (R${self.preco})"


class ProdutoVariacao(models.Model):
    """Cada linha = um SKU único (combinação de valores de variação)"""
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='variacoes')
    sku = models.CharField(max_length=50, unique=True)
    valores = models.ManyToManyField(ValorVariacao, related_name='produto_variacoes')
    preco = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    quantidade = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ['sku']

    def __str__(self):
        return self.sku

    @property
    def preco_efetivo(self):
        return self.preco if self.preco is not None else self.produto.preco

    @property
    def descricao_variacao(self):
        partes = [str(v) for v in self.valores.all().select_related('tipo')]
        return " | ".join(partes)


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
        return 'Desconhecido'

class ItemVenda(models.Model):
    nota = models.ForeignKey(NotaVenda, on_delete=models.CASCADE)
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    variacao = models.ForeignKey(ProdutoVariacao, on_delete=models.SET_NULL, null=True, blank=True, related_name='itens_venda')
    quantidade = models.IntegerField(validators=[MinValueValidator(1)])
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    
    @property
    def subtotal(self):
        return self.quantidade * self.preco_unitario

    @property
    def nome_produto_display(self):
        if self.variacao:
            return f"{self.produto.nome} ({self.variacao.descricao_variacao})"
        return self.produto.nome

    @property
    def sku_display(self):
        if self.variacao:
            return self.variacao.sku
        return "-"
    
    def __str__(self):
        if self.variacao:
            return f"{self.quantidade}x {self.produto.nome} [{self.variacao.sku}] - R${self.subtotal}"
        return f"{self.quantidade}x {self.produto.nome} - R${self.subtotal}"
    
    def save(self, *args, **kwargs):
        if not self.preco_unitario:
            if self.variacao:
                self.preco_unitario = self.variacao.preco_efetivo
            else:
                self.preco_unitario = self.produto.preco
        super().save(*args, **kwargs)
    
class MovimentoEstoque(models.Model):
    TIPO_MOVIMENTO = (
        ('cadastro', 'Cadastro Inicial'),
        ('entrada', 'Entrada Avulsa'),
        ('saida', 'Saída'),
        ('correcao', 'Correção de Estoque'),
    )
    
    produto = models.ForeignKey('Produto', on_delete=models.CASCADE)
    variacao = models.ForeignKey(ProdutoVariacao, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimentos')
    quantidade = models.IntegerField()
    tipo = models.CharField(max_length=8, choices=TIPO_MOVIMENTO)
    data = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='%(class)s_executado'
    )

    @property
    def descricao_display(self):
        if self.variacao:
            return f"{self.produto.nome} [{self.variacao.sku}]"
        return self.produto.nome
    
    def __str__(self):
        if self.variacao:
            return f"{self.produto.nome} [{self.variacao.sku}] - {self.quantidade} ({self.tipo})"
        return f"{self.produto.nome} - {self.quantidade} ({self.tipo})"


class Orcamento(models.Model):
    STATUS_CHOICES = [
        ('rascunho', 'Rascunho'),
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('recusado', 'Recusado'),
        ('expirado', 'Expirado'),
    ]

    cliente = models.CharField(max_length=100)
    produtos = models.ManyToManyField(Produto, through='ItemOrcamento')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    desconto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_com_desconto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='rascunho')
    validade = models.DateField(null=True, blank=True, help_text='Data de validade do orçamento')
    observacao = models.TextField(blank=True, null=True)
    data = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orcamentos')
    usuario_executante = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='orcamentos_executados')

    def __str__(self):
        return f"Orçamento #{self.id} - {self.cliente}"

    @property
    def status_badge(self):
        badges = {
            'rascunho': 'bg-secondary',
            'pendente': 'bg-warning text-dark',
            'aprovado': 'bg-success',
            'recusado': 'bg-danger',
            'expirado': 'bg-dark',
        }
        return badges.get(self.status, 'bg-secondary')


class ItemOrcamento(models.Model):
    orcamento = models.ForeignKey(Orcamento, on_delete=models.CASCADE)
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    variacao = models.ForeignKey(ProdutoVariacao, on_delete=models.SET_NULL, null=True, blank=True, related_name='itens_orcamento')
    quantidade = models.IntegerField(validators=[MinValueValidator(1)])
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        return self.quantidade * self.preco_unitario

    @property
    def nome_produto_display(self):
        if self.variacao:
            return f"{self.produto.nome} ({self.variacao.descricao_variacao})"
        return self.produto.nome

    @property
    def sku_display(self):
        if self.variacao:
            return self.variacao.sku
        return "-"

    def __str__(self):
        if self.variacao:
            return f"{self.quantidade}x {self.produto.nome} [{self.variacao.sku}] - R${self.subtotal}"
        return f"{self.quantidade}x {self.produto.nome} - R${self.subtotal}"

    def save(self, *args, **kwargs):
        if not self.preco_unitario:
            if self.variacao:
                self.preco_unitario = self.variacao.preco_efetivo
            else:
                self.preco_unitario = self.produto.preco
        super().save(*args, **kwargs)


class Perfil(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil', null=True, blank=True)
    Nome = models.CharField(max_length=100)
    email = models.EmailField(max_length=254, blank=True, null=True)
    CNPJ = models.CharField(max_length=20, blank=True, null=True)
    Empresas = models.CharField(max_length=255, blank=True, null=True)
    endereco = models.CharField(max_length=255, blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    celular = models.CharField(max_length=20, blank=True, null=True)
    logotipo = models.ImageField(upload_to='logos/', blank=True, null=True)

    def __str__(self):
        return f"{self.Nome} - Perfil"

    @property
    def nome_empresa(self):
        return self.Empresas or self.Nome or ''


class ConfigEstoqueBaixo(models.Model):
    usuario = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='config_estoque'
    )
    nome_empresa = models.CharField(max_length=200, blank=True, null=True)
    limite_estoque_baixo = models.PositiveIntegerField(
        default=5,
        help_text='Quantidade máxima para considerar estoque baixo'
    )
    dias_movimentacao = models.PositiveIntegerField(
        default=30,
        help_text='Dias para filtrar última movimentação no dashboard'
    )
    dias_validade_orcamento = models.PositiveIntegerField(
        default=15,
        help_text='Dias de validade padrão para orçamentos'
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuração de Estoque Baixo'
        verbose_name_plural = 'Configurações de Estoque Baixo'

    def __str__(self):
        return f"{self.nome_empresa or self.usuario.username} - Estoque Baixo"
