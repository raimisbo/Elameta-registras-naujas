# pozicijos/views.py
from __future__ import annotations

from django.contrib import messages
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_POST
from django.views.decorators.clickjacking import xframe_options_sameorigin

from .services.import_csv import import_pozicijos_from_csv
from .models import Pozicija, PozicijosBrezinys
from .forms import PozicijaForm, PozicijosBrezinysForm
from .schemas.columns import COLUMNS
from .services.previews import generate_preview_for_instance
from .services.listing import (
    visible_cols_from_request,
    apply_filters,
    apply_sorting,
)


# Laukai, kuriems formoje rodysim pasiūlymus iš DB (datalist)
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


# =============================================================================
#  Pagalbinė funkcija formos pasiūlymams (datalist)
# =============================================================================

def _get_form_suggestions() -> dict[str, list[str]]:
    """
    Iš DB ištraukiam unikalias reikšmes tekstiniams laukams, kad formoje būtų
    datalist pasiūlymai. Nefiltruojam pagal jokį klientą/projektą – tiesiog
    visos kada nors naudotos reikšmės.
    """
    suggestions: dict[str, list[str]] = {}

    qs = Pozicija.objects.all()
    for field in FORM_SUGGEST_FIELDS:
        values = (
            qs.order_by(field)
            .values_list(field, flat=True)
            .distinct()
        )
        # pašalinam tuščias reikšmes
        suggestions[field] = [v for v in values if v]

    return suggestions


# =============================================================================
#  Pozicijų sąrašas + AJAX tbody + statistika (donut)
# =============================================================================

def pozicijos_list(request):
    visible_cols = visible_cols_from_request(request)
    q = request.GET.get("q", "").strip()
    page_size = int(request.GET.get("page_size", 25))

    # perskaitom sort + dir, kad perduotume į šabloną
    current_sort = request.GET.get("sort", "")   # pvz. "klientas"
    current_dir = request.GET.get("dir", "asc")  # "asc" arba "desc"

    qs = Pozicija.objects.all()
    qs = apply_filters(qs, request)
    qs = apply_sorting(qs, request)[:page_size]

    context = {
        "columns_schema": COLUMNS,
        "visible_cols": visible_cols,
        "items": qs,
        "q": q,
        "page_size": page_size,
        "f": request.GET,  # šablonas naudoja dict_get
        "current_sort": current_sort,
        "current_dir": current_dir,
    }
    return render(request, "pozicijos/list.html", context)


def pozicijos_tbody(request):
    visible_cols = visible_cols_from_request(request)
    page_size = int(request.GET.get("page_size", 25))

    current_sort = request.GET.get("sort", "")
    current_dir = request.GET.get("dir", "asc")

    qs = Pozicija.objects.all()
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

    data = (
        qs.values("klientas")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")
    )

    labels: list[str] = []
    values: list[int] = []
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


# =============================================================================
#  Pozicijos kortelė + create/edit formos
# =============================================================================

def pozicija_detail(request, pk):
    poz = get_object_or_404(Pozicija, pk=pk)

    # VISI brėžiniai (įskaitant .stp / .step) šiai pozicijai
    breziniai = PozicijosBrezinys.objects.filter(pozicija=poz).order_by("id")

    # AKTUALIOS kainos (rodom kortelėje)
    kainos_akt = poz.aktualios_kainos()

    context = {
        "pozicija": poz,
        "columns_schema": COLUMNS,   # jei ateity norėsim eiti per schemą
        "breziniai": breziniai,      # <- svarbu: čia keliauja į detail.html
        "kainos_akt": kainos_akt,    # lentelė „Kainos (aktualios)“
    }
    return render(request, "pozicijos/detail.html", context)




def pozicija_create(request):
    if request.method == "POST":
        form = PozicijaForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save()
            return redirect("pozicijos:detail", pk=obj.pk)
    else:
        form = PozicijaForm()

    context = {
        "form": form,
        "pozicija": None,
        "suggestions": _get_form_suggestions(),
    }
    return render(request, "pozicijos/form.html", context)


def pozicija_edit(request, pk):
    poz = get_object_or_404(Pozicija, pk=pk)
    if request.method == "POST":
        form = PozicijaForm(request.POST, request.FILES, instance=poz)
        if form.is_valid():
            form.save()
            return redirect("pozicijos:detail", pk=poz.pk)
    else:
        form = PozicijaForm(instance=poz)

    context = {
        "form": form,
        "pozicija": poz,
        "suggestions": _get_form_suggestions(),
    }
    return render(request, "pozicijos/form.html", context)


# =============================================================================
#  Brėžiniai: upload + delete + 3D
# =============================================================================

@require_POST
def brezinys_upload(request, pk):
    poz = get_object_or_404(Pozicija, pk=pk)
    if request.method == "POST" and request.FILES.get("failas"):
        f = request.FILES["failas"]
        title = request.POST.get("pavadinimas", "").strip()
        br = PozicijosBrezinys.objects.create(
            pozicija=poz,
            failas=f,
            pavadinimas=title,
        )
        # Po įkėlimo – bandome sugeneruoti preview
        res = generate_preview_for_instance(br)
        if not res.ok:
            messages.info(
                request,
                f"Įkelta. Peržiūros sugeneruoti nepavyko: {res.message}",
            )
        else:
            messages.success(request, "Įkelta ir sugeneruota peržiūra.")
    return redirect("pozicijos:detail", pk=poz.pk)


def brezinys_delete(request, pk, bid):
    poz = get_object_or_404(Pozicija, pk=pk)
    br = get_object_or_404(PozicijosBrezinys, pk=bid, pozicija=poz)
    br.delete()
    return redirect("pozicijos:detail", pk=pk)


@xframe_options_sameorigin
def brezinys_3d(request, pk, bid):
    """
    Pilnas 3D peržiūros puslapis su Online3DViewer website versija.
    Naudoja .stp failą tiesiai iš media (brezinys.failas.url).
    """
    poz = get_object_or_404(Pozicija, pk=pk)
    br = get_object_or_404(PozicijosBrezinys, pk=bid, pozicija=poz)
    return render(
        request,
        "pozicijos/brezinys_3d.html",
        {
            "pozicija": poz,
            "brezinys": br,
        },
    )


# =============================================================================
#  CSV importas (slaptas)
# =============================================================================

def pozicijos_import_csv(request):
    """
    Slaptas CSV importo puslapis.
    Jokių nuorodų UI – pasiekiamas tik per URL /pozicijos/_import_csv/.
    """
    result = None
    dry_run = False

    if request.method == "POST":
        dry_run = bool(request.POST.get("dry_run"))
        uploaded = request.FILES.get("file")
        if not uploaded:
            messages.error(request, "Pasirink CSV failą.")
        else:
            result = import_pozicijos_from_csv(uploaded, dry_run=dry_run)

    return render(
        request,
        "pozicijos/import_csv.html",
        {
            "result": result,
            "dry_run": dry_run,
        },
    )
