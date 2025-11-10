# pozicijos/kainos_views.py
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse

from .models import Pozicija, PozicijosKaina
from .forms_kainos import PozicijosKainaForm


def kainos_list(request, pk):
    """
    Visos konkrečios pozicijos kainos.
    """
    pozicija = get_object_or_404(Pozicija, pk=pk)
    kainos = pozicija.kainos.all().order_by("-created", "-id")  # naujesnės viršuj
    return render(
        request,
        "pozicijos/kainos_list.html",
        {"pozicija": pozicija, "kainos": kainos},
    )


def kaina_add(request, pk):
    """
    Pridėti naują kainos įrašą šitai pozicijai.
    """
    pozicija = get_object_or_404(Pozicija, pk=pk)

    if request.method == "POST":
        form = PozicijosKainaForm(request.POST)
        if form.is_valid():
            k = form.save(commit=False)
            k.pozicija = pozicija
            k.save()
            return redirect("pozicijos:kainos_list", pk=pozicija.pk)
    else:
        form = PozicijosKainaForm()

    return render(
        request,
        "pozicijos/kaina_form.html",
        {"form": form, "pozicija": pozicija, "mode": "add"},
    )


def kaina_edit(request, pk, kaina_id):
    """
    Redaguot esamą kainos įrašą.
    """
    pozicija = get_object_or_404(Pozicija, pk=pk)
    kaina = get_object_or_404(PozicijosKaina, pk=kaina_id, pozicija=pozicija)

    if request.method == "POST":
        form = PozicijosKainaForm(request.POST, instance=kaina)
        if form.is_valid():
            form.save()
            return redirect("pozicijos:kainos_list", pk=pozicija.pk)
    else:
        form = PozicijosKainaForm(instance=kaina)

    return render(
        request,
        "pozicijos/kaina_form.html",
        {"form": form, "pozicija": pozicija, "mode": "edit", "kaina": kaina},
    )


def kaina_delete(request, pk, kaina_id):
    pozicija = get_object_or_404(Pozicija, pk=pk)
    kaina = get_object_or_404(PozicijosKaina, pk=kaina_id, pozicija=pozicija)

    if request.method == "POST":
        kaina.delete()
        return redirect("pozicijos:kainos_list", pk=pozicija.pk)

    return render(
        request,
        "pozicijos/kaina_delete_confirm.html",
        {"pozicija": pozicija, "kaina": kaina},
    )
