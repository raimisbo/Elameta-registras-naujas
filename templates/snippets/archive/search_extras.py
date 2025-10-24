# detaliu_registras/templatetags/search_extras.py
import re
from django import template
from django.utils.html import escape, mark_safe

register = template.Library()

@register.filter
def highlight(value, query):
    """
    Paryškina (wrap <mark>) visus 'query' pasirodymus 'value' tekste (case-insensitive).
    Saugus XSS atžvilgiu: pirma escapinam tekstą, tada įterpiam <mark>.
    Jei query tuščias / None – grąžinam pradinį tekstą.
    """
    if value is None:
        return ""
    text = str(value)

    if not query:
        # Nieko neparyškinam – tik escape
        return escape(text)

    pattern = re.escape(str(query))
    # Escape'inam visą tekstą, kad būtų saugu, o po to įdedam <mark> aplink atitikmenis
    escaped = escape(text)

    # Pakeitimą darom jau ant escapinto teksto
    regex = re.compile(pattern, re.IGNORECASE)

    def repl(m):
        return f"<mark>{m.group(0)}</mark>"

    highlighted = regex.sub(repl, escaped)
    return mark_safe(highlighted)
