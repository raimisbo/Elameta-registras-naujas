from django import template
register = template.Library()

@register.filter
def dict_get(d, key):
    """Saugiai grąžina d[key] arba '' jei nėra / None."""
    try:
        return (d or {}).get(key, "")
    except Exception:
        return ""
