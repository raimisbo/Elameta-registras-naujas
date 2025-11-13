# pozicijos/proposal_views.py
from urllib.parse import urlencode

from django.conf import settings
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.urls import reverse

from .models import Pozicija
from .schemas.columns import COLUMNS  # tavo 25+ stulpelių aprašas


def _get_logo_url(request):
    """
    Bandom rodyti /media/logo.png, jei jis yra.
    Jei pas tave kitas pavadinimas – pareguliuosim.
    """
    media_url = getattr(settings, "MEDIA_URL", "/media/")
    return request.build_absolute_uri(media_url + "logo.png")


def proposal_prepare(request, pk):
    """
    Čia ateina iš mygtuko „Parengti pasiūlymą“.
    Puslapis tiesiog parodo formą su varnelėmis.
    Po POST – nukreipia į pdf/peržiūros vaizdą su parametrais.
    """
    pozicija = get_object_or_404(Pozicija, pk=pk)

    if request.method == "POST":
        show_prices = "show_prices" in request.POST
        show_drawings = "show_drawings" in request.POST
        notes = request.POST.get("notes", "").strip()

        base_url = reverse("pozicijos:pdf", args=[pozicija.pk])
        params = {}
        if show_prices:
            params["show_prices"] = "1"
        if show_drawings:
            params["show_drawings"] = "1"
        if notes:
            params["notes"] = notes

        query = urlencode(params)
        url = f"{base_url}?{query}" if query else base_url
        return redirect(url)

    # GET – rodom formą
    context = {
        "pozicija": pozicija,
        "default_show_prices": True,
        "default_show_drawings": True,
        "default_notes": "",
    }
    return render(request, "pozicijos/proposal_prepare.html", context)


def proposal_pdf(request, pk):
    """
    Galutinis pasiūlymo vaizdas – iš čia jau galima daryti PDF (wkhtmltopdf, weasyprint ir pan.)
    """
    pozicija = get_object_or_404(Pozicija, pk=pk)

    show_prices = request.GET.get("show_prices") in ("1", "true", "on")
    show_drawings = request.GET.get("show_drawings") in ("1", "true", "on")
    notes = request.GET.get("notes", "").strip()

    kainos = pozicija.kainos.all() if show_prices else []
    brez = pozicija.breziniai.all() if show_drawings else []

    context = {
        "pozicija": pozicija,
        "columns": COLUMNS,
        "kainos": kainos,
        "brez": brez,
        "show_prices": show_prices,
        "show_drawings": show_drawings,
        "notes": notes,
        "now": timezone.now(),
        "logo_url": _get_logo_url(request),
    }
    return render(request, "pozicijos/proposal_pdf.html", context)
