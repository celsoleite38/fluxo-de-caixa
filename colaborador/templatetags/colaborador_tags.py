from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Filtro para acessar um item de um dicionário pela chave
    """
    return dictionary.get(key)

@register.filter
def get_attr(obj, attr_name):
    """
    Filtro para acessar um atributo de um objeto dinamicamente
    """
    return getattr(obj, attr_name, None)