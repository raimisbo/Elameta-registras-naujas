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
    Vieno lauko (plotas/svoris) filtro interpretacija, kai ateina per f[field]:

      "10..20"  -> >=10 ir <=20
      ">5"      -> >=5
      "<12.5"   -> <=12.5
      "15"      -> ==15

    Kablelį leidžiam kaip dešimtainį skirtuką: "12,5" -> 12.5.
    Jei išraiška nekorektiška – grąžinam tuščią Q() (t.y. nefiltuojam).
    """
    raw = (expr or "").strip()
    if not raw:
        return Q()

    # leisti kablelį kaip dešimtainį skirtuką
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
            # paprastas skaičius – reiškia lygų
            value = Decimal(raw)
            min_val = value
            max_val = value

    except (InvalidOperation, ValueError):
        # blogai įvestas skaičius – nedarom filtro, bet ir nekertam klaidos
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
    Atkuria, kurie stulpeliai turi būti rodomi, pagal ?cols=...
    Jei nieko nėra – imami visi COLUMNS, kuriuose default=True.

    Elgesys toks pats, kaip senajame _visible_cols_from_request.
    """
    cols_param = request.GET.get("cols")
    if cols_param:
        return [c for c in cols_param.split(",") if c]
    return [c["key"] for c in COLUMNS if c.get("default")]


# =============================================================================
#  Filtrai
# =============================================================================

def apply_filters(qs: QuerySet, request) -> QuerySet:
    """
    Pritaiko globalų ir per-stulpelinius filtrus.

    Globalus:
      ?q=...  -> klientas/projektas/poz_kodas/poz_pavad (icontains)

    Per-stulpeliniai:
      ?f[klientas]=...   -> icontains
      ?f[plotas]=10..20  -> numeric range per build_numeric_range_q
      ir t.t.

    Logika paimta iš seno pozicijos/views.py (_apply_filters),
    kad niekas „nepasikeistų po refaktoringo“.
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

        # tekstiniai filtrai – icontains (kaip seniau)
        if field in [
            "klientas", "projektas", "poz_kodas", "poz_pavad",
            "metalas", "padengimas", "spalva",
            "pakavimas", "maskavimas", "testai_kokybe",
        ]:
            qs = qs.filter(**{f"{field}__icontains": value})

        # skaitmeniniai filtrai su min..max, >, <, == sintakse
        elif field in ["plotas", "svoris"]:
            qs = qs.filter(build_numeric_range_q(field, value))

        # visi kiti – tikslus atitikimas (lygiai taip, kaip buvo)
        else:
            qs = qs.filter(**{field: value})

    return qs


# =============================================================================
#  Rikiavimas
# =============================================================================

def apply_sorting(qs: QuerySet, request) -> QuerySet:
    """
    Rikiavimas pagal ?sort=key&dir=asc/desc

      - sort: vienas iš COLUMNS key (pvz. 'klientas', 'poz_kodas', 'kaina_eur', ...)
      - virtualūs key (pvz. 'brez_count', 'dok_count') ignoruojami.
      - jei sort nėra arba neatpažįstamas -> pagal naujausią (created desc, id desc)

    Tai yra tiesiog perkelta senojo _apply_sorting logika.
    """
    sort = request.GET.get("sort")
    direction = request.GET.get("dir", "asc")

    # Jei niekas nenurodyta – laikomės seno default'o
    if not sort:
        return qs.order_by("-created", "-id")

    field = SORTABLE_FIELDS.get(sort)
    if not field:
        # jei prašo rikiuoti pagal virtualų ar neegzistuojantį – grįžtam prie default
        return qs.order_by("-created", "-id")

    if direction == "desc":
        field = "-" + field

    # Antrinis rikiavimas pagal id, kad būtų stabilu
    return qs.order_by(field, "-id")
