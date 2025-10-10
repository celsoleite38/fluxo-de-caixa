from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from .models import User, Movimentacao, Categoria, Produto, NotaVenda, ItemVenda, Perfil
from django.contrib.auth.models import User
from django import forms
from django.contrib.auth.models import User


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
        super(CategoriaForm, self).__init__(*args, **kwargs)
    
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
        fields = ['nome', 'descricao', 'preco', 'quantidade']

class NotaVendaForm(forms.ModelForm):
    class Meta:
        model = NotaVenda
        fields = ['cliente']
    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)

class ItemVendaForm(forms.ModelForm):
    class Meta:
        model = ItemVenda
        fields = ['produto', 'quantidade']

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
        super(CategoriaForm, self).__init__(*args, **kwargs)
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.usuario = self.user
        if commit:
            instance.save()
        return instance
    


class UsuarioForm(UserCreationForm):
    telefone = forms.CharField(max_length=15, required=False)
    password1 = forms.CharField(label="Senha", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirmação de Senha", widget=forms.PasswordInput)
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'email', 'telefone', 'password1', 'password2']

class CustomPasswordChangeForm(PasswordChangeForm):
    pass

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
        super(CategoriaForm, self).__init__(*args, **kwargs)
    
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
        fields = ['nome', 'descricao', 'preco', 'quantidade']
    
    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        produto = super().save(commit=False)
        if self.usuario:
            produto.usuario = self.usuario
        if commit:
            produto.save()
        return produto

class NotaVendaForm(forms.ModelForm):
    class Meta:
        model = NotaVenda
        fields = ['cliente']

class ItemVendaForm(forms.ModelForm):
    class Meta:
        model = ItemVenda
        fields = ['produto', 'quantidade']
        
    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        
        # Filtra os produtos apenas do usuário logado
        if self.usuario:
            self.fields['produto'].queryset = Produto.objects.filter(
                usuario=self.usuario, 
                quantidade__gt=0
            )

class EntradaEstoqueForm(forms.Form):
    quantidade = forms.IntegerField(
        min_value=1,
        label='Quantidade a adicionar',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Quantidade'
        })
    )
    
# forms.py


class EditarPerfilForm(forms.ModelForm):
    name = forms.CharField(label='Nome', max_length=150)

    class Meta:
        model = Perfil
        fields = ['Nome', 'CNPJ', 'Empresas', 'email', 'logotipo', 'endereco', 'telefone', 'celular']

    def save(self, commit=True):
        perfil = super().save(commit=False)
        # Atualiza o nome e email do User
        perfil.user.username = self.cleaned_data.get('name')
        if commit:
            perfil.user.save()
            perfil.save()
        return perfil

