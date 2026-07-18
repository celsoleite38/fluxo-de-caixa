from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.models import User
from .models import (
    Movimentacao, Categoria, Produto, NotaVenda, ItemVenda, Perfil,
    TipoVariacao, ValorVariacao, ProdutoVariacao, Orcamento, ItemOrcamento,
    MaquinaCartao
)


class UsuarioForm(UserCreationForm):
    telefone = forms.CharField(max_length=15, required=False)
    password1 = forms.CharField(label="Senha", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirmação de Senha", widget=forms.PasswordInput)
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'email', 'telefone', 'password1', 'password2']

class CustomPasswordChangeForm(PasswordChangeForm):
    pass

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nome', 'tipo']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.usuario = self.user
        if commit:
            instance.save()
        return instance


class ProdutoForm(forms.ModelForm):
    tipos_variacao_ids = forms.CharField(
        required=False, widget=forms.HiddenInput,
        help_text='JSON com IDs dos tipos de variacao selecionados'
    )
    valores_por_tipo = forms.CharField(
        required=False, widget=forms.HiddenInput,
        help_text='JSON {tipo_id: [valor_id, ...]}'
    )
    quantidades_variacoes = forms.CharField(
        required=False, widget=forms.HiddenInput,
        help_text='JSON {"valor_id1-valor_id2": quantidade}'
    )
    novos_tipos = forms.CharField(
        required=False, widget=forms.HiddenInput,
        help_text='JSON com nomes de novos tipos a criar'
    )
    novos_valores = forms.CharField(
        required=False, widget=forms.HiddenInput,
        help_text='JSON {tipo_nome: [valor1, ...]}'
    )

    class Meta:
        model = Produto
        fields = ['nome', 'descricao', 'preco', 'preco_compra', 'quantidade', 'tem_variacao',
                  'sku_base', 'unidade_medida']
        widgets = {
            'tem_variacao': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'onchange': 'toggleVariacao()'
            }),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'preco': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'preco_compra': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control'}),
            'sku_base': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: TNK-NIKE'}),
            'unidade_medida': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'UN, KG, LT'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        if self.usuario:
            self.tipos_disponiveis = TipoVariacao.objects.filter(usuario=self.usuario)
        else:
            self.tipos_disponiveis = TipoVariacao.objects.none()
    
    def save(self, commit=True):
        produto = super().save(commit=False)
        if self.usuario:
            produto.usuario = self.usuario
        if commit:
            produto.save()
            self.save_m2m()
        return produto


class MovimentacaoForm(forms.ModelForm):
    class Meta:
        model = Movimentacao
        fields = ['tipo', 'valor', 'descricao', 'data', 'forma_pagamento']
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'forma_pagamento': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['descricao'].required = True
        self.fields['forma_pagamento'].required = True


class NotaVendaForm(forms.ModelForm):
    class Meta:
        model = NotaVenda
        fields = ['cliente']
    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)

class ItemVendaForm(forms.ModelForm):
    variacao = forms.ModelChoiceField(
        queryset=ProdutoVariacao.objects.none(),
        required=False,
        empty_label='Sem variação',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = ItemVenda
        fields = ['produto', 'variacao', 'quantidade']

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        if self.usuario:
            produtos_com_estoque = Produto.objects.filter(usuario=self.usuario)
            from django.db.models import Q
            produtos_disponiveis = produtos_com_estoque.filter(
                Q(tem_variacao=False, quantidade__gt=0) |
                Q(tem_variacao=True, variacoes__quantidade__gt=0, variacoes__ativo=True)
            ).distinct()
            self.fields['produto'].queryset = produtos_disponiveis
            self.fields['variacao'].queryset = ProdutoVariacao.objects.filter(
                produto__usuario=self.usuario, ativo=True, quantidade__gt=0
            )

    def clean(self):
        cleaned_data = super().clean()
        produto = cleaned_data.get('produto')
        variacao = cleaned_data.get('variacao')

        if produto and produto.tem_variacao and not variacao:
            raise forms.ValidationError('Este produto possui variações. Selecione uma variação.')
        
        if produto and not produto.tem_variacao and variacao:
            raise forms.ValidationError('Este produto não possui variações. deixe o campo variação vazio.')

        if variacao and variacao.produto != produto:
            raise forms.ValidationError('A variação selecionada não pertence a este produto.')

        if variacao and variacao.quantidade <= 0:
            raise forms.ValidationError(f'Estoque insuficiente para a variação {variacao.sku}.')

        return cleaned_data


class EntradaEstoqueForm(forms.Form):
    quantidade = forms.IntegerField(
        min_value=1,
        label='Quantidade a adicionar',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Quantidade'
        })
    )


class CorrecaoEstoqueForm(forms.Form):
    quantidade_correta = forms.IntegerField(
        min_value=0,
        label='Quantidade correta em estoque',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Quantidade que deveria estar'
        })
    )
    observacao = forms.CharField(
        max_length=255,
        required=False,
        label='Observação (opcional)',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: Digitei errado na entrada anterior'
        })
    )


class TipoVariacaoForm(forms.ModelForm):
    class Meta:
        model = TipoVariacao
        fields = ['nome']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Tamanho, Cor, Sabor...'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.usuario:
            instance.usuario = self.usuario
        if commit:
            instance.save()
        return instance


class ValorVariacaoForm(forms.ModelForm):
    class Meta:
        model = ValorVariacao
        fields = ['valor']
        widgets = {
            'valor': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 38, Vermelho, Chocolate...'
            }),
        }


class ProdutoVariacaoForm(forms.ModelForm):
    valores = forms.ModelMultipleChoiceField(
        queryset=ValorVariacao.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=True,
        label='Valores da Variação'
    )

    class Meta:
        model = ProdutoVariacao
        fields = ['sku', 'preco', 'quantidade', 'ativo', 'valores']
        widgets = {
            'sku': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: TNK-38-VMD'
            }),
            'preco': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Deixe vazio para usar o preço base'
            }),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.produto = kwargs.pop('produto', None)
        super().__init__(*args, **kwargs)
        if self.produto:
            tipos = self.produto.tipos_variacao.all()
            self.fields['valores'].queryset = ValorVariacao.objects.filter(tipo__in=tipos)
        if self.instance and self.instance.pk:
            self.fields['valores'].initial = self.instance.valores.all()


class EditarPerfilForm(forms.ModelForm):
    name = forms.CharField(label='Nome', max_length=150, required=False)
    email = forms.EmailField(required=True)

    class Meta:
        model = Perfil
        fields = ['CNPJ', 'Empresas', 'email', 'logotipo', 'endereco', 'telefone', 'celular']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['name'].initial = self.user.first_name

    def save(self, commit=True):
        perfil = super().save(commit=False)
        perfil.usuario = self.user
        perfil.Nome = self.cleaned_data.get('name', '')
        if commit:
            perfil.save()
            if self.user:
                self.user.first_name = self.cleaned_data.get('name', '')
                self.user.email = self.cleaned_data.get('email', '')
                self.user.save()
        return perfil


class OrcamentoForm(forms.ModelForm):
    class Meta:
        model = Orcamento
        fields = ['cliente', 'validade', 'observacao']
        widgets = {
            'cliente': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do cliente'}),
            'validade': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'observacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Observações (opcional)'}),
        }


class ItemOrcamentoForm(forms.ModelForm):
    variacao = forms.ModelChoiceField(
        queryset=ProdutoVariacao.objects.none(),
        required=False,
        empty_label='Sem variação',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = ItemOrcamento
        fields = ['produto', 'variacao', 'quantidade']
        widgets = {
            'produto': forms.Select(attrs={'class': 'form-select'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'value': '1'}),
        }

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        if self.usuario:
            self.fields['produto'].queryset = Produto.objects.filter(usuario=self.usuario)

    def clean(self):
        cleaned_data = super().clean()
        produto = cleaned_data.get('produto')
        variacao = cleaned_data.get('variacao')
        quantidade = cleaned_data.get('quantidade')

        if produto and quantidade:
            if variacao:
                if variacao.quantidade < quantidade:
                    raise forms.ValidationError(
                        f'Estoque insuficiente para {produto.nome} ({variacao.sku}). '
                        f'Disponível: {variacao.quantidade}'
                    )
            else:
                if produto.quantidade < quantidade:
                    raise forms.ValidationError(
                        f'Estoque insuficiente para {produto.nome}. '
                        f'Disponível: {produto.quantidade}'
                    )
        return cleaned_data


class MaquinaCartaoForm(forms.ModelForm):
    parcelas_sem_juros_1 = forms.BooleanField(required=False, label='1x',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input parcela-sj'}))
    parcelas_sem_juros_2 = forms.BooleanField(required=False, label='2x',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input parcela-sj'}))
    parcelas_sem_juros_3 = forms.BooleanField(required=False, label='3x',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input parcela-sj'}))
    parcelas_sem_juros_4 = forms.BooleanField(required=False, label='4x',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input parcela-sj'}))
    parcelas_sem_juros_5 = forms.BooleanField(required=False, label='5x',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input parcela-sj'}))
    parcelas_sem_juros_6 = forms.BooleanField(required=False, label='6x',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input parcela-sj'}))
    parcelas_sem_juros_7 = forms.BooleanField(required=False, label='7x',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input parcela-sj'}))
    parcelas_sem_juros_8 = forms.BooleanField(required=False, label='8x',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input parcela-sj'}))
    parcelas_sem_juros_9 = forms.BooleanField(required=False, label='9x',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input parcela-sj'}))
    parcelas_sem_juros_10 = forms.BooleanField(required=False, label='10x',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input parcela-sj'}))
    parcelas_sem_juros_11 = forms.BooleanField(required=False, label='11x',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input parcela-sj'}))
    parcelas_sem_juros_12 = forms.BooleanField(required=False, label='12x',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input parcela-sj'}))

    class Meta:
        model = MaquinaCartao
        fields = ['nome', 'parcelas_sem_juros',
                  'taxa_1x', 'taxa_2x', 'taxa_3x', 'taxa_4x', 'taxa_5x', 'taxa_6x',
                  'taxa_7x', 'taxa_8x', 'taxa_9x', 'taxa_10x', 'taxa_11x', 'taxa_12x',
                  'taxa_debito', 'taxa_pix', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'parcelas_sem_juros': forms.HiddenInput(),
            'taxa_1x': forms.NumberInput(attrs={'class': 'form-control taxa-parcela', 'step': '0.01', 'min': '0', 'max': '100'}),
            'taxa_2x': forms.NumberInput(attrs={'class': 'form-control taxa-parcela', 'step': '0.01', 'min': '0', 'max': '100'}),
            'taxa_3x': forms.NumberInput(attrs={'class': 'form-control taxa-parcela', 'step': '0.01', 'min': '0', 'max': '100'}),
            'taxa_4x': forms.NumberInput(attrs={'class': 'form-control taxa-parcela', 'step': '0.01', 'min': '0', 'max': '100'}),
            'taxa_5x': forms.NumberInput(attrs={'class': 'form-control taxa-parcela', 'step': '0.01', 'min': '0', 'max': '100'}),
            'taxa_6x': forms.NumberInput(attrs={'class': 'form-control taxa-parcela', 'step': '0.01', 'min': '0', 'max': '100'}),
            'taxa_7x': forms.NumberInput(attrs={'class': 'form-control taxa-parcela', 'step': '0.01', 'min': '0', 'max': '100'}),
            'taxa_8x': forms.NumberInput(attrs={'class': 'form-control taxa-parcela', 'step': '0.01', 'min': '0', 'max': '100'}),
            'taxa_9x': forms.NumberInput(attrs={'class': 'form-control taxa-parcela', 'step': '0.01', 'min': '0', 'max': '100'}),
            'taxa_10x': forms.NumberInput(attrs={'class': 'form-control taxa-parcela', 'step': '0.01', 'min': '0', 'max': '100'}),
            'taxa_11x': forms.NumberInput(attrs={'class': 'form-control taxa-parcela', 'step': '0.01', 'min': '0', 'max': '100'}),
            'taxa_12x': forms.NumberInput(attrs={'class': 'form-control taxa-parcela', 'step': '0.01', 'min': '0', 'max': '100'}),
            'taxa_debito': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'taxa_pix': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            sem_juros = self.instance.parcelas_sem_juros_list()
            for i in range(1, 13):
                self.fields[f'parcelas_sem_juros_{i}'].initial = i in sem_juros

    def clean(self):
        cleaned_data = super().clean()
        sem_juros = []
        for i in range(1, 13):
            if cleaned_data.get(f'parcelas_sem_juros_{i}'):
                sem_juros.append(str(i))
        cleaned_data['parcelas_sem_juros'] = ','.join(sem_juros) if sem_juros else '1'
        return cleaned_data


class SolicitarResetSenhaForm(forms.Form):
    email = forms.EmailField(
        label='E-mail cadastrado',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'seu@email.com.br'}),
    )


class ResetSenhaForm(forms.Form):
    nova_senha = forms.CharField(
        label='Nova Senha',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    confirmar_senha = forms.CharField(
        label='Confirmar Nova Senha',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )

    def clean(self):
        cleaned_data = super().clean()
        s1 = cleaned_data.get('nova_senha')
        s2 = cleaned_data.get('confirmar_senha')
        if s1 and s2 and s1 != s2:
            raise forms.ValidationError('As senhas não coincidem.')
        return cleaned_data
