# pozicijos/kainos_views.py
from __future__ import annotations

from django.contrib import messages
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from .models import Pozicija, KainosEilute
from .forms_kainos import KainaFormSet
from .services.kainos import set_aktuali


@require_http_methods(["GET", "POST"])
def kainos_list(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Vieno lango kainų redagavimas (variantas A – formset ant Pozicija).

    - Rodomos visos pasirinktos pozicijos kainos (pasirenkama būsenos/mato filtras).
    - Viename puslapyje galima:
        * kurti naujas eilutes,
        * redaguoti esamas,
        * pažymėti trynimui.
    - Jeigu eilutei nustatoma busena='aktuali', set_aktuali pasirūpina, kad:
        * toje grupėje liktų tik viena „aktuali“,
        * senos būtų „sena“ ir, jei įmanoma, patrumpintas jų galiojimas,
        * pozicija.kaina_eur būtų atnaujinta (sąrašo stulpeliui).
    """
    pozicija = get_object_or_404(Pozicija, pk=pk)

    busena = request.GET.get("busena", "")
    matas = request.GET.get("matas", "")

    base_qs = KainosEilute.objects.filter(pozicija=pozicija)

    if busena:
        base_qs = base_qs.filter(busena=busena)
    if matas:
        base_qs = base_qs.filter(matas=matas)

    # aiški rikiuotė – ta pati, kaip istorijai/logikai
    qs = base_qs.order_by(
        "matas",
        "yra_fiksuota",
        "kiekis_nuo",
        "fiksuotas_kiekis",
        "prioritetas",
        "-created",
    )

    if request.method == "POST":
        formset = KainaFormSet(request.POST, instance=pozicija, queryset=qs)
        if formset.is_valid():
            with transaction.atomic():
                # Trinamos eilutės
                for form in formset.deleted_forms:
                    if form.instance.pk:
                        form.instance.delete()

                # Išsaugomos / sukuriamos eilutės
                instances = formset.save(commit=False)
                for inst in instances:
                    inst.pozicija = pozicija
                    inst.save()

                # Po saugojimo – pritaikom „aktuali“ logiką ten, kur reikia
                for inst in instances:
                    if inst.busena == "aktuali":
                        # save=False, nes inst jau išsaugotas; set_aktuali tvarko senas ir pozicija.kaina_eur
                        set_aktuali(inst, save=False)

            messages.success(request, "Kainos išsaugotos.")
            return redirect("pozicijos:kainos_list", pk=pozicija.pk)
        else:
            messages.error(request, "Patikrinkite formos klaidas.")
    else:
        formset = KainaFormSet(instance=pozicija, queryset=qs)

    context = {
        "pozicija": pozicija,
        "formset": formset,
        "busena": busena,
        "matas": matas,
    }
    return render(request, "pozicijos/kainos_list.html", context)


def kaina_create(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Istoriškai buvęs atskiras „naujos kainos“ puslapis.
    Dabar visas valdymas vyksta viename lange, todėl peradresuojam.
    """
    return redirect("pozicijos:kainos_list", pk=pk)


def kaina_update(request: HttpRequest, id: int) -> HttpResponse:
    """
    Istoriškai buvęs atskiras redagavimo puslapis – peradresuojam į bendrą sąrašą.
    """
    k = get_object_or_404(KainosEilute, pk=id)
    return redirect("pozicijos:kainos_list", pk=k.pozicija_id)


@require_POST
def kaina_set_aktuali(request: HttpRequest, id: int) -> HttpResponse:
    """
    Jei šis URL naudojamas atskirai – pažymi eilutę kaip „aktuali“ ir sutvarko konfliktus.
    """
    k = get_object_or_404(KainosEilute, pk=id)
    set_aktuali(k)  # čia jau pats išsaugo ir atnaujina pozicija.kaina_eur
    messages.success(request, "Kaina pažymėta kaip aktuali.")
    return redirect("pozicijos:kainos_list", pk=k.pozicija_id)


@require_POST
def kaina_delete(request: HttpRequest, id: int) -> HttpResponse:
    """
    Paprastas trynimas (šiuo metu formset'e naudojam DELETE checkbox'ą, bet URL paliekam).
    """
    k = get_object_or_404(KainosEilute, pk=id)
    poz_id = k.pozicija_id
    k.delete()
    messages.success(request, "Kainos eilutė ištrinta.")
    return redirect("pozicijos:kainos_list", pk=poz_id)


def kaina_history(request: HttpRequest, id: int) -> HttpResponse:
    """
    Vienos KainosEilute įrašo istorija (simple_history).

    Rodo:
      - kada kaina sukurta / keista / ištrinta (history_type)
      - reikšmes tuo metu (kaina, matas, kiekiai, busena ir pan.)
      - kas keitė (history_user, jei yra)
    """
    kaina = get_object_or_404(KainosEilute, pk=id)
    history_qs = kaina.history.all().order_by("-history_date")

    context = {
        "pozicija": kaina.pozicija,
        "kaina": kaina,
        "history": history_qs,
    }
    return render(request, "pozicijos/kaina_history.html", context)
