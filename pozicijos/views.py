# pozicijos/views.py
from django.db.models import Q, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_POST

from .models import Pozicija, PozicijosBrezinys
from .forms import PozicijaForm, PozicijosBrezinysForm
from .schemas.columns import COLUMNS
from . import proposal_views  # pasiūlymo parengimui / pdf


def _visible_cols_from_request(request):
    cols_param = request.GET.get("cols")
    if cols_param:
        return [c for c in cols_param.split(",") if c]
    return [c["key"] for c in COLUMNS if c.get("default")]


def _apply_filters(qs, request):
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
        field = key[2:-1]
        value = value.strip()
        if not value:
            continue

        if field in [
            "klientas", "projektas", "poz_kodas", "poz_pavad",
            "metalas", "padengimas", "spalva",
            "pakavimas", "maskavimas", "testai_kokybe",
        ]:
            qs = qs.filter(**{f"{field}__icontains": value})
        else:
            qs = qs.filter(**{field: value})

    return qs


def pozicijos_list(request):
    visible_cols = _visible_cols_from_request(request)
    q = request.GET.get("q", "").strip()
    page_size = int(request.GET.get("page_size", 25))

    qs = Pozicija.objects.all()
    qs = _apply_filters(qs, request)
    qs = qs.order_by("-created", "-id")[:page_size]

    context = {
        "columns_schema": COLUMNS,
        "visible_cols": visible_cols,
        "items": qs,
        "q": q,
        "page_size": page_size,
        "f": request.GET,  # šablonas naudoja dict_get
    }
    return render(request, "pozicijos/list.html", context)


def pozicijos_tbody(request):
    visible_cols = _visible_cols_from_request(request)
    page_size = int(request.GET.get("page_size", 25))

    qs = Pozicija.objects.all()
    qs = _apply_filters(qs, request)
    qs = qs.order_by("-created", "-id")[:page_size]

    return render(
        request,
        "pozicijos/_tbody.html",
        {
            "columns_schema": COLUMNS,
            "visible_cols": visible_cols,
            "items": qs,
        },
    )


def pozicijos_stats(request):
    qs = Pozicija.objects.all()
    qs = _apply_filters(qs, request)

    data = (
        qs.values("klientas")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")
    )

    labels = []
    values = []
    total = 0
    for row in data:
        name = row["klientas"] or "Nepriskirta"
        labels.append(name)
        values.append(row["cnt"])
        total += row["cnt"]

    return JsonResponse(
        {
            "labels": labels,
            "values": values,
            "total": total,
        }
    )


def pozicija_detail(request, pk):
    poz = get_object_or_404(Pozicija, pk=pk)
    return render(
        request,
        "pozicijos/detail.html",
        {
            "pozicija": poz,
            "columns_schema": COLUMNS,  # ← kad matytum VISAS eilutes
        },
    )


def pozicija_create(request):
    if request.method == "POST":
        form = PozicijaForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save()
            return redirect("pozicijos:detail", pk=obj.pk)
    else:
        form = PozicijaForm()
    return render(request, "pozicijos/form.html", {"form": form})


def pozicija_edit(request, pk):
    poz = get_object_or_404(Pozicija, pk=pk)
    if request.method == "POST":
        form = PozicijaForm(request.POST, request.FILES, instance=poz)
        if form.is_valid():
            form.save()
            return redirect("pozicijos:detail", pk=poz.pk)
    else:
        form = PozicijaForm(instance=poz)
    return render(request, "pozicijos/form.html", {"form": form, "pozicija": poz})


@require_POST
def brezinys_upload(request, pk):
    poz = get_object_or_404(Pozicija, pk=pk)
    form = PozicijosBrezinysForm(request.POST, request.FILES)
    if form.is_valid():
        br = form.save(commit=False)
        br.pozicija = poz
        br.save()
    return redirect("pozicijos:detail", pk=pk)


def brezinys_delete(request, pk, bid):
    poz = get_object_or_404(Pozicija, pk=pk)
    br = get_object_or_404(PozicijosBrezinys, pk=bid, pozicija=poz)
    br.delete()
    return redirect("pozicijos:detail", pk=pk)
