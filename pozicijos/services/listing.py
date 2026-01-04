# pozicijos/services/listing.py
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Dict, List

from django.db.models import Q, QuerySet

from ..schemas.columns import COLUMNS


# Kurie stulpeliai gali būti rikiuojami – pagal key -> realų DB lauką.
# Virtualūs ('brez_count', 'dok_count', ir pan.) čia nepatenka.
SORTABLE_FIELDS: Dict[str, str] = {
    c["key"]: c.get("order_field", c["key"])
    for c in COLUMNS
    if c.get("type") != "virtual"
}


def build_numeric_range_q(field_name: str, expr: str) -> Q:
    """
    Decimal tipo (plotas/svoris) filtro interpretacija.

    Palaikoma:
      "10..20"   -> >=10 ir <=20
      ">5"       -> >=5
      ">=5"      -> >=5
      "<12.5"    -> <=12.5
      "<=12.5"   -> <=12.5
      "15"       -> ==15
      "=15"      -> ==15

    Kablelį leidžiam kaip dešimtainį skirtuką: "12,5" -> 12.5.
    Jei išraiška nekorektiška – grąžinam tuščią Q().
    """
    raw = (expr or "").strip()
    if not raw:
        return Q()

    raw = raw.replace(",", ".")

    min_val = None
    max_val = None

    try:
        if ".." in raw:
            left, right = raw.split("..", 1)
            left = left.strip()
            right = right.strip()
            if left:
                min_val = Decimal(left)
            if right:
                max_val = Decimal(right)

        elif raw.startswith(">="):
            value = Decimal(raw[2:].strip())
            min_val = value

        elif raw.startswith("<="):
            value = Decimal(raw[2:].strip())
            max_val = value

        elif raw.startswith("="):
            value = Decimal(raw[1:].strip())
            min_val = value
            max_val = value

        elif raw[0] in (">", "<"):
            op = raw[0]
            val_str = raw[1:].strip()
            if not val_str:
                return Q()
            value = Decimal(val_str)
            if op == ">":
                min_val = value
            else:
                max_val = value

        else:
            value = Decimal(raw)
            min_val = value
            max_val = value

    except (InvalidOperation, ValueError):
        return Q()

    q = Q()
    if min_val is not None:
        q &= Q(**{f"{field_name}__gte": min_val})
    if max_val is not None:
        q &= Q(**{f"{field_name}__lte": max_val})
    return q


def build_int_range_q(field_name: str, expr: str) -> Q:
    """
    Integer tipo (pvz. atlikimo_terminas darbo dienomis) filtro interpretacija.

    Palaikoma:
      "10..20", ">5", ">=5", "<12", "<=12", "15", "=15"
    """
    raw = (expr or "").strip()
    if not raw:
        return Q()

    min_val = None
    max_val = None

    try:
        if ".." in raw:
            left, right = raw.split("..", 1)
            left = left.strip()
            right = right.strip()
            if left:
                min_val = int(left)
            if right:
                max_val = int(right)

        elif raw.startswith(">="):
            min_val = int(raw[2:].strip())

        elif raw.startswith("<="):
            max_val = int(raw[2:].strip())

        elif raw.startswith("="):
            v = int(raw[1:].strip())
            min_val = v
            max_val = v

        elif raw[0] in (">", "<"):
            op = raw[0]
            val_str = raw[1:].strip()
            if not val_str:
                return Q()
            v = int(val_str)
            if op == ">":
                min_val = v
            else:
                max_val = v

        else:
            v = int(raw)
            min_val = v
            max_val = v

    except ValueError:
        return Q()

    q = Q()
    if min_val is not None:
        q &= Q(**{f"{field_name}__gte": min_val})
    if max_val is not None:
        q &= Q(**{f"{field_name}__lte": max_val})
    return q


# =============================================================================
#  Stulpelių matomumas
# =============================================================================

def visible_cols_from_request(request) -> List[str]:
    """
    Atkuria, kurie stulpeliai turi būti rodomi.

    Taisyklės (SVARBU dėl sinchronizacijos su JS):
    - Jei request'e NĖRA 'cols' parametro: naudojam schema default=True (serverinis fallback).
    - Jei request'e YRA 'cols' parametras: laikom jį autoritetingu ir GRĄŽINAM TIK TĄ SĄRAŠĄ
      (išvalę nežinomus key + dedupe), NIEKO papildomai nepridedam.

    Taip išvengiam situacijos, kai:
    - frontas rodo 6 "Numatytuosius" stulpelius,
    - o backas į tbody prideda papildomų default=True stulpelių,
    - ir tada "Kaina" pradeda rodyti ne tą stulpelį.
    """
    known_keys = [c["key"] for c in COLUMNS]
    known_set = set(known_keys)
    default_keys = [c["key"] for c in COLUMNS if c.get("default")]

    # kritinis skirtumas: tikrinam parametrų buvimą, ne reikšmės "truthiness"
    if "cols" not in request.GET:
        return default_keys

    cols_param = request.GET.get("cols", "")

    # Parse + dedupe (išlaikom eiliškumą)
    raw_list = [c for c in (cols_param or "").split(",") if c]
    seen = set()
    cols: List[str] = []
    for k in raw_list:
        if k in known_set and k not in seen:
            cols.append(k)
            seen.add(k)

    # jei buvo pateikta, bet po valymo nieko neliko – grąžinam tuščią (kad nesusiveltų stulpeliai)
    return cols


# =============================================================================
#  Filtrai
# =============================================================================

def apply_filters(qs: QuerySet, request) -> QuerySet:
    """
    Pritaiko globalų ir per-stulpelinius filtrus.

    Globalus:
      ?q=...  -> klientas/projektas/poz_kodas/poz_pavad (icontains)

    Per-stulpeliniai:
      ?f[field]=...
    """
    q_global = request.GET.get("q", "").strip()
    if q_global:
        qs = qs.filter(
            Q(klientas__icontains=q_global)
            | Q(projektas__icontains=q_global)
            | Q(poz_kodas__icontains=q_global)
            | Q(poz_pavad__icontains=q_global)
        )

    for key, value in request.GET.items():
        if not key.startswith("f["):
            continue

        field = key[2:-1]  # f[field] -> field
        value = (value or "").strip()
        if not value:
            continue

        # tekstiniai filtrai – icontains
        if field in [
            "klientas", "projektas", "poz_kodas", "poz_pavad",
            "metalas", "padengimas", "spalva",
            "pakavimas", "maskavimas", "testai_kokybe",
        ]:
            qs = qs.filter(**{f"{field}__icontains": value})

        # Decimal range
        elif field in ["plotas", "svoris"]:
            qs = qs.filter(build_numeric_range_q(field, value))

        # Integer range (darbo dienos)
        elif field in ["atlikimo_terminas"]:
            qs = qs.filter(build_int_range_q(field, value))

        # visi kiti – tikslus atitikimas
        else:
            qs = qs.filter(**{field: value})

    return qs


# =============================================================================
#  Rikiavimas
# =============================================================================

def apply_sorting(qs: QuerySet, request) -> QuerySet:
    """
    Rikiavimas pagal ?sort=key&dir=asc/desc
    """
    sort = request.GET.get("sort")
    direction = request.GET.get("dir", "asc")

    if not sort:
        return qs.order_by("-created", "-id")

    field = SORTABLE_FIELDS.get(sort)
    if not field:
        return qs.order_by("-created", "-id")

    if direction == "desc":
        field = "-" + field

    return qs.order_by(field, "-id")
