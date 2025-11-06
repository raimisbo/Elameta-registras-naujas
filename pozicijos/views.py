# pozicijos/views.py
from django.http import HttpResponse, JsonResponse
from django.views.generic import TemplateView, DetailView, CreateView, UpdateView
from django.db.models import Q, Count
from django.template.loader import render_to_string
from django.urls import reverse_lazy

from .models import Pozicija
from .schemas.columns import COLUMNS
from .forms import PozicijaForm


def parse_filters(params):
    q = (params.get("q") or "").strip()
    f = {}
    for k, v in params.items():
        if k.startswith("f[") and k.endswith("]"):
            key = k[2:-1]
            val = v.strip()
            if val:
                f[key] = val

    cols_param = (params.get("cols") or "").strip()
    cols = [c for c in cols_param.split(",") if c]

    try:
        page_size = int(params.get("page_size") or 50)
    except ValueError:
        page_size = 50

    try:
        page = int(params.get("page") or 1)
    except ValueError:
        page = 1

    return q, f, cols, page, page_size


def apply_filters(qs, q, f):
    # globali paieška
    if q:
        q_obj = Q()
        for col in COLUMNS:
            if col.get("searchable"):
                q_obj |= Q(**{f"{col['key']}__icontains": q})
        qs = qs.filter(q_obj)

    # stulpeliniai filtrai
    for key, val in f.items():
        col = next((c for c in COLUMNS if c["key"] == key), None)
        if not col:
            continue

        field_name = col["key"]
        ftype = col.get("filter")

        if ftype == "range":
            expr = val.replace(" ", "")
            if ".." in expr:
                lo, hi = expr.split("..", 1)
                if lo:
                    qs = qs.filter(**{f"{field_name}__gte": lo})
                if hi:
                    qs = qs.filter(**{f"{field_name}__lte": hi})
            elif expr.startswith(">="):
                num = expr[2:]
                qs = qs.filter(**{f"{field_name}__gte": num})
            elif expr.startswith("<="):
                num = expr[2:]
                qs = qs.filter(**{f"{field_name}__lte": num})
            else:
                qs = qs.filter(**{field_name: expr})
        elif ftype == "date":
            qs = qs.filter(**{f"{field_name}": val})
        else:
            qs = qs.filter(**{f"{field_name}__icontains": val})

    return qs


class PozicijuSarasasView(TemplateView):
    template_name = "pozicijos/list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q, f, cols, page, page_size = parse_filters(self.request.GET)

        qs = Pozicija.objects.all()
        qs = apply_filters(qs, q, f)

        start = (page - 1) * page_size
        end = start + page_size
        items = qs.order_by("id")[start:end]

        default_cols = [c["key"] for c in COLUMNS if c.get("default")]
        visible_cols = cols or default_cols

        ctx.update({
            "items": items,
            "columns_schema": COLUMNS,
            "visible_cols": visible_cols,
            "q": q,
            "f": f,
            "page": page,
            "page_size": page_size,
        })
        return ctx


class PozicijuTbodyPartialView(TemplateView):
    """
    Grąžina tik <tbody> fragmentą AJAX'ui.
    """
    def get(self, request, *args, **kwargs):
        q, f, cols, page, page_size = parse_filters(request.GET)
        qs = Pozicija.objects.all()
        qs = apply_filters(qs, q, f)

        start = (page - 1) * page_size
        end = start + page_size
        items = qs.order_by("id")[start:end]

        default_cols = [c["key"] for c in COLUMNS if c.get("default")]
        visible_cols = cols or default_cols

        html = render_to_string(
            "pozicijos/_tbody.html",
            {
                "items": items,
                "columns_schema": COLUMNS,
                "visible_cols": visible_cols,
            },
            request=request,
        )
        return HttpResponse(html)


class PozicijuStatsView(TemplateView):
    """
    JSON donut grafikui: kiek įrašų pagal klientą + bendras filtruotų įrašų skaičius.
    """
    def get(self, request, *args, **kwargs):
        q, f, cols, page, page_size = parse_filters(request.GET)
        qs = Pozicija.objects.all()
        qs = apply_filters(qs, q, f)

        total = qs.count()

        data = (
            qs.values("klientas")
              .annotate(cnt=Count("id"))
              .order_by("-cnt")[:12]
        )

        labels = [d["klientas"] or "—" for d in data]
        values = [d["cnt"] for d in data]

        return JsonResponse({
            "labels": labels,
            "values": values,
            "total": total,
        })


class PozicijaDetailView(DetailView):
    model = Pozicija
    template_name = "pozicijos/detail.html"
    context_object_name = "pozicija"


class PozicijosKorteleView(DetailView):
    """
    /pozicijos/detale/<slug>/ variantas
    """
    model = Pozicija
    template_name = "pozicijos/detail.html"
    context_object_name = "pozicija"
    slug_field = "poz_kodas"
    slug_url_kwarg = "slug"


class PozicijaCreateView(CreateView):
    model = Pozicija
    form_class = PozicijaForm
    template_name = "pozicijos/form.html"
    success_url = reverse_lazy("pozicijos:list")


class PozicijaUpdateView(UpdateView):
    model = Pozicija
    form_class = PozicijaForm
    template_name = "pozicijos/form.html"
    success_url = reverse_lazy("pozicijos:list")
