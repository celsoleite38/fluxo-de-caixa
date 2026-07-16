from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.models import User
from .models import (
    Movimentacao, Categoria, Produto, NotaVenda, ItemVenda, Perfil,
    TipoVariacao, ValorVariacao, ProdutoVariacao, Orcamento, ItemOrcamento
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
    class Meta:
        model = Produto
        fields = ['nome', 'descricao', 'preco', 'quantidade', 'tem_variacao',
                  'tipos_variacao', 'sku_base', 'unidade_medida']
        widgets = {
            'tem_variacao': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tipos_variacao': forms.CheckboxSelectMultiple(),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'preco': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control'}),
            'sku_base': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: TNK-NIKE'}),
            'unidade_medida': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'UN, KG, LT'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        if self.usuario:
            self.fields['tipos_variacao'].queryset = TipoVariacao.objects.filter(usuario=self.usuario)
    
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
            produtos_sem_variacao = produtos_com_estoque.filter(
                tem_variacao=False, quantidade__gt=0
            )
            produtos_com_variacao = produtos_com_estoque.filter(
                tem_variacao=True, variacoes__quantidade__gt=0, variacoes__ativo=True
            ).distinct()
            self.fields['produto'].queryset = produtos_sem_variacao | produtos_com_variacao

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
