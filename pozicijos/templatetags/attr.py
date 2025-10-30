from django import template

register = template.Library()

@register.filter
def attr(obj, name):
    """
    Naudojimas: {{ object|attr:"lauko_pavadinimas" }}
    Saugiai grąžina atributo reikšmę arba tuščią stringą.
    """
    if not obj or not name:
        return ""
    return getattr(obj, name, "")
