# pozicijos/templatetags/attr.py
from django import template

register = template.Library()

@register.filter(name="attr")
def attr(obj, path: str):
    """
    Saugus getter'is šablonams:
      {{ obj|attr:"laukas" }}
      {{ obj|attr:"a.b.c" }}  # įdėtiniai keliai
    Palaiko dict'us, objektų atributus ir beargumentes funkcijas/@property.
    Grąžina "" jei kelio nėra arba reikšmė None.
    """
    if obj is None or not path:
        return ""
    try:
        parts = str(path).split(".")
        val = obj
        for p in parts:
            if isinstance(val, dict):
                val = val.get(p, "")
            else:
                val = getattr(val, p, "")
            if callable(val):
                try:
                    val = val()  # beargumentė funkcija arba @property
                except TypeError:
                    # turi argumentų – nešaukiam
                    pass
        return "" if val is None else val
    except Exception:
        return ""
