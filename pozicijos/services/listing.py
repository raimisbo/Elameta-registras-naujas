from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Dict, List

from django.db.models import Q, QuerySet
from django.utils.dateparse import parse_date

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
    Decimal tipo filtro interpretacija.

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
    Integer tipo filtro interpretacija.

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

    Logika:
    - Jei ?cols=... yra pateiktas (pvz. iš localStorage/JS), laikom, kad tai vartotojo pasirinktas
      stulpelių rinkinys, BET:
        * išvalom nežinomus raktus (kad nelūžtų po refactor)
        * pridedam naujus default=True stulpelius, kurių tame rinkinyje dar nėra
    - Jei ?cols nėra – imami visi COLUMNS, kuriuose default=True.
    """
    known_keys = [c["key"] for c in COLUMNS]
    known_set = set(known_keys)
    default_keys = [c["key"] for c in COLUMNS if c.get("default")]

    cols_param = request.GET.get("cols")

    if not cols_param:
        return default_keys

    raw_list = [c for c in cols_param.split(",") if c]
    seen = set()
    cols: List[str] = []
    for k in raw_list:
        if k in known_set and k not in seen:
            cols.append(k)
            seen.add(k)

    if not cols:
        return default_keys

    for k in default_keys:
        if k not in seen:
            cols.append(k)
            seen.add(k)

    return cols


# =============================================================================
#  Filtrai
# =============================================================================

# Aiškiai atskiriam int „range“ laukus (kad ">5" veiktų kaip int).
INT_RANGE_FIELDS = {
    "atlikimo_terminas",
    "detaliu_kiekis_reme",
    "faktinis_kiekis_reme",
}

# created/updated – DateTime, filtruojam pagal __date (YYYY-MM-DD iš input type=date)
DATE_FIELDS_USE_DATE_LOOKUP = {"created", "updated"}


def apply_filters(qs: QuerySet, request) -> QuerySet:
    """
    Pritaiko globalų ir per-stulpelinius filtrus.

    Globalus:
      ?q=...  -> klientas/projektas/poz_kodas/poz_pavad (icontains)

    Per-stulpeliniai:
      ?f[field]=...
      remiamės COLUMNS schema: text/range/date
    """
    q_global = request.GET.get("q", "").strip()
    if q_global:
        qs = qs.filter(
            Q(klientas__icontains=q_global)
            | Q(projektas__icontains=q_global)
            | Q(poz_kodas__icontains=q_global)
            | Q(poz_pavad__icontains=q_global)
        )

    schema_by_key = {c["key"]: c for c in COLUMNS}

    for key, value in request.GET.items():
        if not key.startswith("f[") or not key.endswith("]"):
            continue

        field = key[2:-1]  # f[field] -> field
        value = (value or "").strip()
        if not value:
            continue

        col = schema_by_key.get(field)
        if not col:
            continue

        # virtualių nefiltruojam
        if col.get("type") == "virtual" or col.get("filter") is None:
            continue

        ftype = col.get("filter")

        if ftype == "text":
            qs = qs.filter(**{f"{field}__icontains": value})

        elif ftype == "range":
            # int arba decimal pagal lauką
            if field in INT_RANGE_FIELDS:
                qs = qs.filter(build_int_range_q(field, value))
            else:
                qs = qs.filter(build_numeric_range_q(field, value))

        elif ftype == "date":
            d = parse_date(value)
            if not d:
                continue
            if field in DATE_FIELDS_USE_DATE_LOOKUP:
                qs = qs.filter(**{f"{field}__date": d})
            else:
                qs = qs.filter(**{field: d})

        else:
            # fallback: exact
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
