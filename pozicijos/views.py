# pozicijos/views.py
from django.db.models import Q, Count
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.core.exceptions import FieldError

from .models import Pozicija
from .forms import PozicijaForm, PozicijosKainaFormSet
from .schemas.columns import COLUMNS  # tavo columns.py


# ---- pagalbinės ----

def _get_visible_cols(request):
    cols_param = request.GET.get("cols")
    if cols_param:
        return [c for c in cols_param.split(",") if c]
    return [c["key"] for c in COLUMNS if c.get("default")]


def apply_filters(qs, request):
    """
    Globali paieška ir stulpelių filtrai.
    Filtruojam tik pagal tuos laukus, kurie yra modelyje.
    """
    model_fields = {f.name for f in Pozicija._meta.get_fields()}

    # globali
    g = (request.GET.get("q") or "").strip()
    if g:
      q_obj = Q()
      for col in COLUMNS:
          if not col.get("searchable"):
              continue
          key = col["key"]
          if key not in model_fields:
              continue
          q_obj |= Q(**{f"{key}__icontains": g})
      if q_obj:
          try:
              qs = qs.filter(q_obj)
          except FieldError:
              pass

    # stulpelių filtrai
    for key, value in request.GET.items():
        if not key.startswith("f[") or not key.endswith("]"):
            continue
        col_key = key[2:-1]
        val = value.strip()
        if not val:
            continue

        col = next((c for c in COLUMNS if c["key"] == col_key), None)
        if not col:
            continue
        if col_key not in model_fields:
            continue

        ftype = col.get("filter") or col.get("type") or "text"

        try:
            if ftype in ("text", "choice"):
                qs = qs.filter(**{f"{col_key}__icontains": val})
            elif ftype in ("date",):
                qs = qs.filter(**{col_key: val})
            elif ftype in ("number", "range"):
                if val.startswith(">="):
                    qs = qs.filter(**{f"{col_key}__gte": val[2:].strip()})
                elif val.startswith("<="):
                    qs = qs.filter(**{f"{col_key}__lte": val[2:].strip()})
                elif ".." in val:
                    lo, hi = val.split("..", 1)
                    if lo:
                        qs = qs.filter(**{f"{col_key}__gte": lo})
                    if hi:
                        qs = qs.filter(**{f"{col_key}__lte": hi})
                else:
                    qs = qs.filter(**{col_key: val})
            else:
                qs = qs.filter(**{f"{col_key}__icontains": val})
        except FieldError:
            continue

    return qs


# ---- sąrašas ----

def pozicijos_list(request):
    visible_cols = _get_visible_cols(request)

    qs = Pozicija.objects.all().order_by("-created", "-id")
    qs = apply_filters(qs, request)
    page_size = int(request.GET.get("page_size", 25) or 25)
    items = qs[:page_size]

    return render(
        request,
        "pozicijos/list.html",
        {
            "columns_schema": COLUMNS,
            "visible_cols": visible_cols,
            "items": items,
            "q": request.GET.get("q", ""),
            "f": {},
            "page_size": page_size,
        },
    )


def pozicijos_tbody(request):
    visible_cols = _get_visible_cols(request)
    qs = Pozicija.objects.all().order_by("-created", "-id")
    qs = apply_filters(qs, request)
    page_size = int(request.GET.get("page_size", 25) or 25)
    items = qs[:page_size]

    f_vals = {}
    for key, value in request.GET.items():
        if key.startswith("f[") and key.endswith("]"):
            f_vals[key[2:-1]] = value

    return render(
        request,
        "pozicijos/_tbody.html",
        {
            "items": items,
            "columns_schema": COLUMNS,
            "visible_cols": visible_cols,
            "f": f_vals,
        },
    )


def pozicijos_stats(request):
    qs = Pozicija.objects.all()
    qs = apply_filters(qs, request)

    agg = qs.values("klientas").annotate(cnt=Count("id")).order_by("-cnt")

    labels, values, total = [], [], 0
    for row in agg:
        lbl = row["klientas"] or "—"
        labels.append(lbl)
        values.append(row["cnt"])
        total += row["cnt"]

    return JsonResponse({"labels": labels, "values": values, "total": total})


# ---- CRUD ----

def pozicija_detail(request, pk):
    pozicija = get_object_or_404(Pozicija, pk=pk)
    kainos = pozicija.kainos.all()  # visos kainos šiai pozicijai
    return render(
        request,
        "pozicijos/detail.html",
        {
            "pozicija": pozicija,
            "kainos": kainos,
        },
    )


def pozicija_create(request):
    if request.method == "POST":
        form = PozicijaForm(request.POST)
        if form.is_valid():
            obj = form.save()
            return redirect("pozicijos:detail", pk=obj.pk)
    else:
        form = PozicijaForm()
    return render(request, "pozicijos/form.html", {"form": form})


def pozicija_edit(request, pk):
    obj = get_object_or_404(Pozicija, pk=pk)
    if request.method == "POST":
        form = PozicijaForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            return redirect("pozicijos:detail", pk=obj.pk)
    else:
        form = PozicijaForm(instance=obj)
    return render(request, "pozicijos/form.html", {"form": form, "pozicija": obj})


# ---- KAINOS kaip sename projekte ----

def pozicijos_kainos_redaguoti(request, pk):
    pozicija = get_object_or_404(Pozicija, pk=pk)

    if request.method == "POST":
        formset = PozicijosKainaFormSet(request.POST, instance=pozicija)
        if formset.is_valid():
            formset.save()
            # paskutinę aktualią užkeliame į pozicijos kaina_eur
            last = pozicija.kainos.filter(busena="aktuali").order_by("-created").first()
            if last:
                pozicija.kaina_eur = last.suma
                pozicija.save(update_fields=["kaina_eur"])
            return redirect("pozicijos:detail", pk=pozicija.pk)
    else:
        formset = PozicijosKainaFormSet(instance=pozicija)

    return render(
        request,
        "pozicijos/kainos_redaguoti.html",
        {
            "pozicija": pozicija,
            "formset": formset,
        },
    )
