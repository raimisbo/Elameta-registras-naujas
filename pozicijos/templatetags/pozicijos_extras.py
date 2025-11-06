# pozicijos/templatetags/pozicijos_extras.py
from django import template

register = template.Library()


@register.filter
def get_attr(obj, attr_name):
    """
    Grąžina modelio atributo reikšmę pagal pavadinimą.
    Jei nėra – tuščia eilutė.
    """
    return getattr(obj, attr_name, "") or ""
