# pozicijos/kainos_views.py
from decimal import Decimal
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.contrib import messages
from django.views.decorators.http import require_POST

from .models import Pozicija, KainosEilute
from .forms_kainos import KainaForm
from .services.kainos import KainosCreateData, create_or_update_kaina, set_aktuali


def kainos_list(request, pk):
    pozicija = get_object_or_404(Pozicija, pk=pk)
    qs = KainosEilute.objects.filter(pozicija=pozicija).order_by("-created")

    busena = request.GET.get("busena")
    if busena:
        qs = qs.filter(busena=busena)
    matas = request.GET.get("matas")
    if matas:
        qs = qs.filter(matas=matas)

    ctx = {
        "pozicija": pozicija,
        "kainos": qs,
        "busena": busena or "",
        "matas": matas or "",
    }
    return render(request, "pozicijos/kainos_list.html", ctx)


def kaina_create(request, pk):
    pozicija = get_object_or_404(Pozicija, pk=pk)
    if request.method == "POST":
        form = KainaForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            create_or_update_kaina(KainosCreateData(
                pozicija=pozicija,
                kaina=data["kaina"],
                matas=data["matas"],
                yra_fiksuota=data["yra_fiksuota"],
                fiksuotas_kiekis=data.get("fiksuotas_kiekis"),
                kiekis_nuo=data.get("kiekis_nuo"),
                kiekis_iki=data.get("kiekis_iki"),
                galioja_nuo=data.get("galioja_nuo"),
                galioja_iki=data.get("galioja_iki"),
                busena=data["busena"],
                prioritetas=data["prioritetas"],
                pastaba=data.get("pastaba"),
            ))
            messages.success(request, "Kaina išsaugota.")
            return redirect("pozicijos:kainos_list", pk=pozicija.pk)
    else:
        form = KainaForm()
    return render(request, "pozicijos/kaina_form.html", {"form": form, "pozicija": pozicija})


def kaina_update(request, id):
    k = get_object_or_404(KainosEilute, pk=id)
    pozicija = k.pozicija
    if request.method == "POST":
        form = KainaForm(request.POST, instance=k)
        if form.is_valid():
            k = form.save()
            if k.busena == "aktuali":
                set_aktuali(k)
            messages.success(request, "Kaina atnaujinta.")
            return redirect("pozicijos:kainos_list", pk=pozicija.pk)
    else:
        form = KainaForm(instance=k)
    return render(request, "pozicijos/kaina_form.html", {"form": form, "pozicija": pozicija, "obj": k})


@require_POST
def kaina_set_aktuali(request, id):
    k = get_object_or_404(KainosEilute, pk=id)
    set_aktuali(k)
    messages.success(request, "Pažymėta „Aktuali“. Konfliktinės eilutės pasendintos.")
    return redirect("pozicijos:kainos_list", pk=k.pozicija.pk)


def kaina_delete(request, id):
    k = get_object_or_404(KainosEilute, pk=id)
    pozicija = k.pozicija
    if request.method == "POST":
        k.delete()
        messages.success(request, "Įrašas pašalintas.")
        return redirect("pozicijos:kainos_list", pk=pozicija.pk)
    return render(request, "pozicijos/confirm_delete.html", {"obj": k, "back_url": reverse("pozicijos:kainos_list", args=[pozicija.pk])})
