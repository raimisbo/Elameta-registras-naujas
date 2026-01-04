# pozicijos/views.py
from __future__ import annotations

from django.contrib import messages
from django.db import transaction
from django.db.models import Count, IntegerField, Value
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_POST
from django.views.decorators.clickjacking import xframe_options_sameorigin

from .services.import_csv import import_pozicijos_from_csv
from .models import Pozicija, PozicijosBrezinys, KainosEilute
from .forms import PozicijaForm, PozicijosBrezinysForm
from .forms_kainos import KainaFormSet
from .schemas.columns import COLUMNS
from .services.previews import regenerate_missing_preview
from .services.listing import (
    visible_cols_from_request,
    apply_filters,
    apply_sorting,
)


FORM_SUGGEST_FIELDS = [
    "klientas",
    "projektas",
    "metalas",
    "kabinimo_budas",
    "kabinimas_reme",
    "paruosimas",
    "padengimas",
    "padengimo_standartas",
    "spalva",
    "maskavimas",
    "testai_kokybe",
    "pakavimas",
    "instrukcija",
]


def _get_form_suggestions() -> dict[str, list[str]]:
    suggestions: dict[str, list[str]] = {}
    qs = Pozicija.objects.all()
    for field in FORM_SUGGEST_FIELDS:
        values = qs.order_by(field).values_list(field, flat=True).distinct()
        suggestions[field] = [v for v in values if v]
    return suggestions


def _safe_int(value, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _base_list_qs():
    """
    Centralizuojam: sąrašui anotacijos (brez_count).
    Dok_count kol kas neturim modelio – paliekam 0, kad stulpelis nelūžtų.
    """
    return (
        Pozicija.objects.all()
        .annotate(brez_count=Count("breziniai", distinct=True))
        .annotate(dok_count=Value(0, output_field=IntegerField()))
    )


def pozicijos_list(request):
    visible_cols = visible_cols_from_request(request)
    q = request.GET.get("q", "").strip()
    page_size = _safe_int(request.GET.get("page_size", 25), 25)

    current_sort = request.GET.get("sort", "")
    current_dir = request.GET.get("dir", "asc")

    qs = _base_list_qs()
    qs = apply_filters(qs, request)
    qs = apply_sorting(qs, request)[:page_size]

    context = {
        "columns_schema": COLUMNS,
        "visible_cols": visible_cols,
        "items": qs,
        "q": q,
        "page_size": page_size,
        "f": request.GET,
        "current_sort": current_sort,
        "current_dir": current_dir,
    }
    return render(request, "pozicijos/list.html", context)


def pozicijos_tbody(request):
    visible_cols = visible_cols_from_request(request)
    page_size = _safe_int(request.GET.get("page_size", 25), 25)

    current_sort = request.GET.get("sort", "")
    current_dir = request.GET.get("dir", "asc")

    qs = _base_list_qs()
    qs = apply_filters(qs, request)
    qs = apply_sorting(qs, request)[:page_size]

    return render(
        request,
        "pozicijos/_tbody.html",
        {
            "columns_schema": COLUMNS,
            "visible_cols": visible_cols,
            "items": qs,
            "current_sort": current_sort,
            "current_dir": current_dir,
        },
    )


def pozicijos_stats(request):
    qs = Pozicija.objects.all()
    qs = apply_filters(qs, request)

    data = qs.values("klientas").annotate(cnt=Count("id")).order_by("-cnt")

    labels: list[str] = []
    values: list[int] = []
    total = 0
    for row in data:
        name = row["klientas"] or "Nepriskirta"
        labels.append(name)
        values.append(row["cnt"])
        total += row["cnt"]

    return JsonResponse({"labels": labels, "values": values, "total": total})


def pozicija_detail(request, pk):
    poz = get_object_or_404(Pozicija, pk=pk)
    breziniai = PozicijosBrezinys.objects.filter(pozicija=poz).order_by("id")
    kainos_akt = poz.aktualios_kainos()

    context = {
        "pozicija": poz,
        "columns_schema": COLUMNS,
        "breziniai": breziniai,
        "kainos_akt": kainos_akt,
    }
    return render(request, "pozicijos/detail.html", context)


def _sync_kaina_eur_from_lines(poz: Pozicija) -> None:
    akt = poz.aktualios_kainos().first()
    poz.kaina_eur = akt.kaina if akt else None
    poz.save(update_fields=["kaina_eur", "updated"])


def pozicija_create(request):
    pozicija = None

    if request.method == "POST":
        form = PozicijaForm(request.POST, request.FILES)
        formset = KainaFormSet(request.POST, prefix="kainos", queryset=KainosEilute.objects.none())

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                pozicija = form.save()

                formset.instance = pozicija
                instances = formset.save(commit=False)
                for inst in instances:
                    inst.pozicija = pozicija
                    inst.save()
                for f in formset.deleted_forms:
                    if f.instance.pk:
                        f.instance.delete()

                _sync_kaina_eur_from_lines(pozicija)

            messages.success(request, "Pozicija sukurta.")
            return redirect("pozicijos:detail", pk=pozicija.pk)
        else:
            messages.error(request, "Patikrinkite formos klaidas.")
    else:
        form = PozicijaForm()
        formset = KainaFormSet(prefix="kainos", queryset=KainosEilute.objects.none())

    context = {
        "form": form,
        "pozicija": pozicija,
        "suggestions": _get_form_suggestions(),
        "kainos_formset": formset,
    }
    return render(request, "pozicijos/form.html", context)


def pozicija_edit(request, pk):
    pozicija = get_object_or_404(Pozicija, pk=pk)

    qs = KainosEilute.objects.filter(pozicija=pozicija).order_by(
        "matas",
        "yra_fiksuota",
        "kiekis_nuo",
        "fiksuotas_kiekis",
        "prioritetas",
        "-created",
    )

    if request.method == "POST":
        form = PozicijaForm(request.POST, request.FILES, instance=pozicija)
        formset = KainaFormSet(request.POST, prefix="kainos", instance=pozicija, queryset=qs)

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()

                instances = formset.save(commit=False)
                for inst in instances:
                    inst.pozicija = pozicija
                    inst.save()
                for f in formset.deleted_forms:
                    if f.instance.pk:
                        f.instance.delete()

                _sync_kaina_eur_from_lines(pozicija)

            messages.success(request, "Pozicija atnaujinta.")
            return redirect("pozicijos:detail", pk=pozicija.pk)
        else:
            messages.error(request, "Patikrinkite formos klaidas.")
    else:
        form = PozicijaForm(instance=pozicija)
        formset = KainaFormSet(prefix="kainos", instance=pozicija, queryset=qs)

    context = {
        "form": form,
        "pozicija": pozicija,
        "suggestions": _get_form_suggestions(),
        "kainos_formset": formset,
    }
    return render(request, "pozicijos/form.html", context)


@require_POST
def brezinys_upload(request, pk):
    poz = get_object_or_404(Pozicija, pk=pk)
    if request.FILES.get("failas"):
        f = request.FILES["failas"]
        title = request.POST.get("pavadinimas", "").strip()
        br = PozicijosBrezinys.objects.create(pozicija=poz, failas=f, pavadinimas=title)

        # STEP/STP – preview sąmoningai nenaudojam
        if not br.is_step:
            res = regenerate_missing_preview(br)
            if res.ok:
                messages.success(request, "Įkelta. Miniatiūra paruošta.")
            else:
                messages.info(request, f"Įkelta. Miniatiūros sugeneruoti nepavyko: {res.message}")
        else:
            messages.success(request, "Įkelta. STEP/STP miniatiūra nenaudojama (rodoma 3D ikona).")

    return redirect("pozicijos:detail", pk=poz.pk)


@require_POST
def brezinys_delete(request, pk, bid):
    poz = get_object_or_404(Pozicija, pk=pk)
    br = get_object_or_404(PozicijosBrezinys, pk=bid, pozicija=poz)
    br.delete()
    return redirect("pozicijos:detail", pk=pk)


@xframe_options_sameorigin
def brezinys_3d(request, pk, bid):
    poz = get_object_or_404(Pozicija, pk=pk)
    br = get_object_or_404(PozicijosBrezinys, pk=bid, pozicija=poz)
    return render(request, "pozicijos/brezinys_3d.html", {"pozicija": poz, "brezinys": br})


def pozicijos_import_csv(request):
    result = None
    dry_run = False

    if request.method == "POST":
        dry_run = bool(request.POST.get("dry_run"))
        uploaded = request.FILES.get("file")
        if not uploaded:
            messages.error(request, "Pasirink CSV failą.")
        else:
            result = import_pozicijos_from_csv(uploaded, dry_run=dry_run)

    return render(request, "pozicijos/import_csv.html", {"result": result, "dry_run": dry_run})
