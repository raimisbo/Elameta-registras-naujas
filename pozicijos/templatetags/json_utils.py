import json
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def tojson(value):
    return mark_safe(json.dumps(value, ensure_ascii=False))
