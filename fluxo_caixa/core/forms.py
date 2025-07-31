from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from .models import Usuario, Movimentacao, Categoria, Produto, NotaVenda, ItemVenda

class UsuarioForm(UserCreationForm):
    telefone = forms.CharField(max_length=15, required=False)
    password1 = forms.CharField(label="Senha", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirmação de Senha", widget=forms.PasswordInput)
    
    class Meta:
        model = Usuario
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
    
from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from .models import Usuario, Movimentacao, Categoria, Produto, NotaVenda, ItemVenda

class UsuarioForm(UserCreationForm):
    telefone = forms.CharField(max_length=15, required=False)
    password1 = forms.CharField(label="Senha", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirmação de Senha", widget=forms.PasswordInput)
    
    class Meta:
        model = Usuario
        fields = ['username', 'first_name', 'email', 'telefone', 'password1', 'password2']

class CustomPasswordChangeForm(PasswordChangeForm):
    pass

class MovimentacaoForm(forms.ModelForm):
    class Meta:
        model = Movimentacao
        fields = ['tipo', 'valor', 'descricao', 'data']
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['descricao'].required = False

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

class ItemVendaForm(forms.ModelForm):
    class Meta:
        model = ItemVenda
        fields = ['produto', 'quantidade']

class EntradaEstoqueForm(forms.Form):
    quantidade = forms.IntegerField(
        min_value=1,
        label='Quantidade a adicionar',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Quantidade'
        })
    )