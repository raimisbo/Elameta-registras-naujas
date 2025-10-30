from django.http import JsonResponse
from django.db.models import Count
from django.views.generic import TemplateView
from django.db.models import Q
from django.views.generic import DetailView
from django.utils.http import urlencode
from .schemas.columns import COLUMNS
from .models import Pozicija

def parse_filters(params):
    q = (params.get("q") or "").strip()
    f = {}
    for k, v in params.items():
        if k.startswith("f[") and k.endswith("]"):
            key = k[2:-1]
            if v.strip():
                f[key] = v.strip()
    cols = [c for c in (params.get("cols") or "").split(",") if c]
    page_size = int(params.get("page_size", 25) or 25)
    page = int(params.get("page", 1) or 1)
    return q, f, cols, page, page_size

def apply_filters(qs, q, f):
    # globalus
    if q:
        q_obj = Q()
        for c in COLUMNS:
            if c.get("searchable"):
                q_obj |= Q(**{f"{c['key']}__icontains": q})
        qs = qs.filter(q_obj)

    # per-stulpeliniai
    for key, val in f.items():
        col = next((c for c in COLUMNS if c["key"] == key), None)
        if not col:
            continue
        t = col["type"]
        s = val.strip()
        if t in ("text", "choice"):
            qs = qs.filter(**{f"{key}__icontains": s})
        elif t == "number":
            s = s.replace(" ", "")
            if ".." in s:
                lo, hi = s.split("..", 1)
                if lo: qs = qs.filter(**{f"{key}__gte": lo})
                if hi: qs = qs.filter(**{f"{key}__lte": hi})
            elif s.startswith(">="):
                qs = qs.filter(**{f"{key}__gte": s[2:]})
            elif s.startswith("<="):
                qs = qs.filter(**{f"{key}__lte": s[2:]})
            elif s.startswith(">"):
                qs = qs.filter(**{f"{key}__gt": s[1:]})
            elif s.startswith("<"):
                qs = qs.filter(**{f"{key}__lt": s[1:]})
            elif s.startswith("="):
                qs = qs.filter(**{f"{key}": s[1:]})
            else:
                qs = qs.filter(**{f"{key}": s})
        elif t == "date":
            s = s.replace(" ", "")
            if ".." in s:
                lo, hi = s.split("..", 1)
                if lo: qs = qs.filter(**{f"{key}__gte": lo})
                if hi: qs = qs.filter(**{f"{key}__lte": hi})
            else:
                qs = qs.filter(**{f"{key}": s})
    return qs

class PozicijuSarasasView(TemplateView):
    template_name = "pozicijos/list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        q, f, cols, page, page_size = parse_filters(self.request.GET)
        qs = apply_filters(Pozicija.objects.all(), q, f)

        total = qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        items = list(qs.order_by("id")[start:end])

        default_cols = [c["key"] for c in COLUMNS if c.get("default")]
        visible_cols = cols or default_cols

        ctx.update({
            "columns_schema": COLUMNS,
            "visible_cols": visible_cols,
            "items": items,
            "q": q,
            "f": f,
            "page": page,
            "page_size": page_size,
            "total": total,
        })
        return ctx

class PozicijuTbodyPartialView(TemplateView):
    template_name = "pozicijos/_tbody.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        q, f, cols, page, page_size = parse_filters(self.request.GET)
        qs = apply_filters(Pozicija.objects.all(), q, f)

        start = (page - 1) * page_size
        end = start + page_size
        items = list(qs.order_by("id")[start:end])

        ctx.update({
            "columns_schema": COLUMNS,
            "visible_cols": cols or [c["key"] for c in COLUMNS if c.get("default")],
            "items": items,
        })
        return ctx

class PozicijosKorteleView(TemplateView):
    """
    Kortelė vienai detalei (stub). Sekančiame žingsnyje pridėsim suvestines ir variantų lentelę.
    """
    template_name = "pozicijos/detail.html"

    def get_context_data(self, slug, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Čia galėsi filtruoti pagal detalės kodą ar slug (kai bus Detale modelis)
        ctx.update({
            "slug": slug,
            "columns_schema": COLUMNS,
            "visible_cols": [c["key"] for c in COLUMNS if c.get("default")],
            "items": Pozicija.objects.all().order_by("id")[:200],  # laikinas
        })
        return ctx

class PozicijuStatsView(TemplateView):
    """Grąžina skaičius grafikui pagal aktyvius filtrus: kiek eilučių per klientą."""
    def get(self, request, *args, **kwargs):
        q, f, cols, page, page_size = parse_filters(request.GET)
        qs = apply_filters(Pozicija.objects.all(), q, f)
        data = (
            qs.values("klientas")
              .annotate(cnt=Count("id"))
              .order_by("-cnt")[:12]
        )
        labels = [d["klientas"] or "—" for d in data]
        values = [d["cnt"] for d in data]
        return JsonResponse({"labels": labels, "values": values})


class PozicijaDetailView(DetailView):
    model = Pozicija
    template_name = "pozicijos/detail.html"
    context_object_name = "pozicija"