# pozicijos/templatetags/json_utils.py
import json
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def tojson(value):
    """
    Saugiai paverčia Python objektą į JSON.
    Naudojimas šablone:
      {{ columns_schema|tojson }}
    """
    return mark_safe(json.dumps(value, ensure_ascii=False))
