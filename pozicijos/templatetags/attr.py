from django import template

register = template.Library()


@register.filter
def attr(obj, name):
    """
    {{ object|attr:"laukas" }} – saugiai.
    """
    if not obj or not name:
        return ""
    return getattr(obj, name, "") or ""
