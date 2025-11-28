# pozicijos/views.py
from django.contrib import messages
from django.db.models import Q, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_POST
from django.views.decorators.clickjacking import xframe_options_sameorigin

from decimal import Decimal, InvalidOperation

from .services.import_csv import import_pozicijos_from_csv
from .models import Pozicija, PozicijosBrezinys
from .forms import PozicijaForm, PozicijosBrezinysForm
from .schemas.columns import COLUMNS
from .services.previews import generate_preview_for_instance
from . import proposal_views  # pasiūlymo parengimui / pdf


# Kurie stulpeliai gali būti rikiuojami – pagal key -> realų DB lauką.
# Virtualūs ('brez_count', 'dok_count', ir pan.) čia nepatenka.
SORTABLE_FIELDS = {
    c["key"]: c.get("order_field", c["key"])
    for c in COLUMNS
    if c.get("type") != "virtual"
}


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


def _get_form_suggestions():
    """
    Surenka unikalius tekstinius laukų variantus iš esamų Pozicija įrašų,
    kad forma galėtų rodyti pasiūlymus (datalist).
    """
    qs = Pozicija.objects.all()
    suggestions = {}
    for field in FORM_SUGGEST_FIELDS:
        values = (
            qs.order_by(field)
            .values_list(field, flat=True)
            .exclude(**{f"{field}__isnull": True})
            .exclude(**{field: ""})
            .distinct()
        )
        suggestions[field] = list(values)
    return suggestions


# ==== Skaitinis filtras Plotas / Svoris: min..max, >, <, == ==================

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

    # LT vartotojas dažnai rašo kablelį; Decimal nori taško
    s = raw.replace(",", ".").strip()

    min_val = None
    max_val = None

    try:
        if ".." in s:
            left, right = s.split("..", 1)
            left = left.strip()
            right = right.strip()
            if left:
                min_val = Decimal(left)
            if right:
                max_val = Decimal(right)
        elif s.startswith(">"):
            val = s[1:].strip()
            if val:
                min_val = Decimal(val)
        elif s.startswith("<"):
            val = s[1:].strip()
            if val:
                max_val = Decimal(val)
        else:
            # tikslus skaičius – traktuojam kaip == value
            value = Decimal(s)
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

        # tekstiniai filtrai – icontains
        if field in [
            "klientas", "projektas", "poz_kodas", "poz_pavad",
            "metalas", "padengimas", "spalva",
            "pakavimas", "maskavimas", "testai_kokybe",
        ]:
            qs = qs.filter(**{f"{field}__icontains": value})

        # skaitmeniniai filtrai su min..max, >, <, == sintakse
        elif field in ["plotas", "svoris"]:
            qs = qs.filter(build_numeric_range_q(field, value))

        # visi kiti – tikslus atitikimas
        else:
            qs = qs.filter(**{field: value})

    return qs


def _apply_sorting(qs, request):
    """
    Rikiavimas pagal ?sort=key&dir=asc/desc
    - sort: vienas iš COLUMNS key (pvz. 'klientas', 'poz_kodas', 'kaina_eur', ...)
    - virtualūs key (pvz. 'brez_count', 'dok_count') ignoruojami.
    - jei sort nėra arba neatpažįstamas -> pagal naujausią (created desc, id desc)
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


def pozicijos_list(request):
    visible_cols = _visible_cols_from_request(request)
    q = request.GET.get("q", "").strip()
    page_size = int(request.GET.get("page_size", 25))

    # perskaitom sort + dir, kad perduotume į šabloną
    current_sort = request.GET.get("sort", "")   # pvz. 'klientas'
    current_dir = request.GET.get("dir", "asc")  # 'asc' arba 'desc'

    qs = Pozicija.objects.all()
    qs = _apply_filters(qs, request)
    qs = _apply_sorting(qs, request)[:page_size]

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
    visible_cols = _visible_cols_from_request(request)
    page_size = int(request.GET.get("page_size", 25))

    current_sort = request.GET.get("sort", "")
    current_dir = request.GET.get("dir", "asc")

    qs = Pozicija.objects.all()
    qs = _apply_filters(qs, request)
    qs = _apply_sorting(qs, request)[:page_size]

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

    # AKTUALIOS kainos (rodom kortelėje)
    kainos_akt = poz.aktualios_kainos()

    context = {
        "pozicija": poz,
        "columns_schema": COLUMNS,   # kad detail‘e eitume per visą schemą
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


@require_POST
def brezinys_upload(request, pk):
    poz = get_object_or_404(Pozicija, pk=pk)
    if request.method == "POST" and request.FILES.get("failas"):
        f = request.FILES["failas"]
        title = request.POST.get("pavadinimas", "").strip()
        br = PozicijosBrezinys.objects.create(pozicija=poz, failas=f, pavadinimas=title)
        # Po įkėlimo – bandome sugeneruoti preview
        res = generate_preview_for_instance(br)
        if not res.ok:
            messages.info(request, f"Įkelta. Peržiūros sugeneruoti nepavyko: {res.message}")
        else:
            messages.success(request, "Įkelta ir sugeneruota peržiūra.")
    return redirect("pozicijos:detail", pk=poz.pk)


def brezinys_delete(request, pk, bid):
    poz = get_object_or_404(Pozicija, pk=pk)
    br = get_object_or_404(PozicijosBrezinys, pk=bid, pozicija=poz)
    br.delete()
    return redirect("pozicijos:detail", pk=pk)


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
