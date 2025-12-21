# pozicijos/kainos_views.py
from __future__ import annotations

from urllib.parse import urlencode

from django.contrib import messages
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from .models import Pozicija, KainosEilute
from .forms_kainos import KainaFormSet
from .services.kainos import set_aktuali


def _get_filters(request: HttpRequest) -> tuple[str, str]:
    """
    Filtrai gali ateiti:
      - per GET (įprastas filtravimas),
      - per POST hidden laukus (_busena, _matas), kad po išsaugojimo grįžtume į tą patį filtrą.
    """
    if request.method == "POST":
        busena = (request.POST.get("_busena") or "").strip()
        matas = (request.POST.get("_matas") or "").strip()
        return busena, matas

    busena = (request.GET.get("busena") or "").strip()
    matas = (request.GET.get("matas") or "").strip()
    return busena, matas


def _redirect_with_filters(pozicija_id: int, busena: str, matas: str) -> HttpResponse:
    base = reverse("pozicijos:kainos_list", kwargs={"pk": pozicija_id})
    params: dict[str, str] = {}
    if busena:
        params["busena"] = busena
    if matas:
        params["matas"] = matas

    if params:
        return redirect(base + "?" + urlencode(params))
    return redirect(base)


@require_http_methods(["GET", "POST"])
def kainos_list(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Vieno lango kainų redagavimas (formset ant Pozicija).

    - busena filtras: DB reikšmės yra "aktuali" / "sena"
    - matas filtras: "Vnt." / "kg" / "komplektas"
    """
    pozicija = get_object_or_404(Pozicija, pk=pk)

    busena, matas = _get_filters(request)

    base_qs = KainosEilute.objects.filter(pozicija=pozicija)

    # Filtrai (tik DB reikšmės)
    if busena:
        base_qs = base_qs.filter(busena=busena)
    if matas:
        base_qs = base_qs.filter(matas=matas)

    qs = base_qs.order_by(
        "matas",
        "yra_fiksuota",
        "kiekis_nuo",
        "fiksuotas_kiekis",
        "prioritetas",
        "-created",
    )

    # Naudojam vienodą prefix, kaip kitur (pozicija_create/edit) – mažiau painiavos
    prefix = "kainos"

    if request.method == "POST":
        formset = KainaFormSet(request.POST, instance=pozicija, queryset=qs, prefix=prefix)
        if formset.is_valid():
            with transaction.atomic():
                # Trinimai
                for form in formset.deleted_forms:
                    if form.instance.pk:
                        form.instance.delete()

                # Save / create
                instances = formset.save(commit=False)
                for inst in instances:
                    inst.pozicija = pozicija
                    inst.save()

                # Konfliktų tvarkymas „aktuali“ logikai
                for inst in instances:
                    if inst.busena == "aktuali":
                        # inst jau išsaugotas; set_aktuali tvarko senas ir atnaujina pozicija.kaina_eur
                        set_aktuali(inst, save=False)

            messages.success(request, "Kainos išsaugotos.")
            return _redirect_with_filters(pozicija.pk, busena, matas)

        messages.error(request, "Patikrinkite formos klaidas.")
    else:
        formset = KainaFormSet(instance=pozicija, queryset=qs, prefix=prefix)

    context = {
        "pozicija": pozicija,
        "formset": formset,
        "busena": busena,
        "matas": matas,
    }
    return render(request, "pozicijos/kainos_list.html", context)


def kaina_create(request: HttpRequest, pk: int) -> HttpResponse:
    return redirect("pozicijos:kainos_list", pk=pk)


def kaina_update(request: HttpRequest, id: int) -> HttpResponse:
    k = get_object_or_404(KainosEilute, pk=id)
    return redirect("pozicijos:kainos_list", pk=k.pozicija_id)


@require_POST
def kaina_set_aktuali(request: HttpRequest, id: int) -> HttpResponse:
    k = get_object_or_404(KainosEilute, pk=id)
    set_aktuali(k)
    messages.success(request, "Kaina pažymėta kaip aktuali.")
    return redirect("pozicijos:kainos_list", pk=k.pozicija_id)


@require_POST
def kaina_delete(request: HttpRequest, id: int) -> HttpResponse:
    k = get_object_or_404(KainosEilute, pk=id)
    poz_id = k.pozicija_id
    k.delete()
    messages.success(request, "Kainos eilutė ištrinta.")
    return redirect("pozicijos:kainos_list", pk=poz_id)


def kaina_history(request: HttpRequest, id: int) -> HttpResponse:
    kaina = get_object_or_404(KainosEilute, pk=id)
    history_qs = kaina.history.all().order_by("-history_date")

    context = {
        "pozicija": kaina.pozicija,
        "kaina": kaina,
        "history": history_qs,
    }
    return render(request, "pozicijos/kaina_history.html", context)
