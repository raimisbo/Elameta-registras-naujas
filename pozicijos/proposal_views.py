# pozicijos/proposal_views.py
from __future__ import annotations

import io
import os
from datetime import datetime
from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from .models import Pozicija


# ===== LT šriftai ===========================================================

def _register_fonts() -> tuple[str, str]:
    """
    Pabandome paimti LT šriftus iš MEDIA_ROOT/fonts.
    Jei randam bent vieną .ttf/.otf – registruojam kaip LT-Regular (ir LT-Bold, jei yra antras).
    Jei nieko – liekam su numatytais Helvetica.
    """
    regular = "Helvetica"
    bold = "Helvetica-Bold"

    fonts_dir = os.path.join(settings.MEDIA_ROOT, "fonts")
    if not os.path.isdir(fonts_dir):
        return regular, bold

    font_files = [
        f for f in os.listdir(fonts_dir)
        if f.lower().endswith((".ttf", ".otf"))
    ]
    if not font_files:
        return regular, bold

    def register_font(alias: str, filename: str) -> str | None:
        path = os.path.join(fonts_dir, filename)
        try:
            pdfmetrics.registerFont(TTFont(alias, path))
            return alias
        except Exception:
            return None

    reg_alias = register_font("LT-Regular", font_files[0]) or regular
    bold_alias = reg_alias
    if len(font_files) > 1:
        bold_alias = register_font("LT-Bold", font_files[1]) or reg_alias

    return reg_alias, bold_alias


# ===== Pagalbiniai duomenų ruošėjai =========================================

def _build_field_rows(pozicija: Pozicija) -> list[tuple[str, str]]:
    """
    Paruošia (label, value) sąrašą iš visų Pozicija laukų.
    Tušti laukai praleidžiami. Tai praktiškai „visos opcijos iš kortelės“,
    tik be id/created/updated.
    """
    rows: list[tuple[str, str]] = []
    skip = {"id", "created", "updated"}

    for field in pozicija._meta.fields:
        if field.name in skip:
            continue
        value = getattr(pozicija, field.name, None)
        if value in (None, ""):
            continue
        label = str(field.verbose_name or field.name).capitalize()
        rows.append((label, value))
    return rows


def _get_kainos_for_pdf(pozicija: Pozicija):
    """
    Naudojam naują modelį KainosEilute (related_name='kainu_eilutes').
    Renkam tik aktualias eilutes.
    """
    return pozicija.kainu_eilutes.filter(busena="aktuali").order_by(
        "matas", "yra_fiksuota", "kiekis_nuo", "fiksuotas_kiekis", "galioja_nuo"
    )


# ===== Views: UI puslapis ====================================================

def proposal_prepare(request, pk: int):
    """
    UI puslapis pasiūlymo paruošimui (varnelės + pastabos).
    Nieko neredaguoja DB, tik ruošia GET parametrus PDF/HTML peržiūrai.
    """
    pozicija = get_object_or_404(Pozicija, pk=pk)

    show_prices = bool(request.GET.get("show_prices"))
    show_drawings = bool(request.GET.get("show_drawings"))
    notes = request.GET.get("notes", "")

    # QS stringas HTML / PDF nuorodoms
    params: dict[str, str] = {}
    if show_prices:
        params["show_prices"] = "1"
    if show_drawings:
        params["show_drawings"] = "1"
    if notes:
        params["notes"] = notes
    qs = urlencode(params)

    context = {
        "pozicija": pozicija,
        "show_prices": show_prices,
        "show_drawings": show_drawings,
        "notes": notes,
        "qs": qs,
    }
    return render(request, "pozicijos/proposal_prepare.html", context)


# ===== Views: PDF / HTML peržiūra ===========================================

def proposal_pdf(request, pk: int):
    """
    Jei ?preview=1 – grąžina HTML (peržiūra su CSS, kaip puslapis).
    Kitu atveju – sugeneruoja PDF per ReportLab, su LT šriftais ir logotipu.
    """
    pozicija = get_object_or_404(Pozicija, pk=pk)

    show_prices = bool(request.GET.get("show_prices"))
    show_drawings = bool(request.GET.get("show_drawings"))
    notes = request.GET.get("notes", "").strip()
    preview = bool(request.GET.get("preview"))

    field_rows = _build_field_rows(pozicija)
    kainos = _get_kainos_for_pdf(pozicija)
    brez = list(pozicija.breziniai.all())

    if preview:
        # HTML peržiūra – čia viskas su tavo baziniu CSS.
        ctx = {
            "pozicija": pozicija,
            "field_rows": field_rows,
            "kainos": kainos,
            "brez": brez,
            "show_prices": show_prices,
            "show_drawings": show_drawings,
            "notes": notes,
        }
        return render(request, "pozicijos/proposal_pdf.html", ctx)

    # ===== Tikras PDF =====
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    font_regular, font_bold = _register_fonts()

    # viršuje – logotipas + antraštė
    c.setFont(font_regular, 10)
    y = height - 30 * mm

    logo_path = os.path.join(settings.MEDIA_ROOT, "logo.png")
    if os.path.exists(logo_path):
        try:
            img = ImageReader(logo_path)
            c.drawImage(img, 20 * mm, height - 25 * mm,
                        width=40 * mm, preserveAspectRatio=True, mask="auto")
        except Exception:
            pass

    c.setFont(font_bold, 20)
    c.drawCentredString(width / 2, height - 20 * mm, "Pasiūlymas")

    c.setFont(font_regular, 10)
    c.drawRightString(width - 20 * mm, height - 20 * mm, f"Pozicija: {pozicija.poz_kodas}")
    if pozicija.poz_pavad:
        c.drawRightString(width - 20 * mm, height - 25 * mm, f"Detalė: {pozicija.poz_pavad}")

    y = height - 35 * mm
    c.line(20 * mm, y, width - 20 * mm, y)
    y -= 10

    # Pagrindinė informacija (visos kortelės opcijos, be tuščių)
    c.setFont(font_bold, 12)
    c.drawString(20 * mm, y, "Pagrindinė informacija")
    y -= 8
    c.setFont(font_regular, 10)

    for label, val in field_rows:
        text = f"{label}: {val}"
        if y < 30 * mm:
            c.showPage()
            c.setFont(font_regular, 10)
            y = height - 30 * mm
        c.drawString(20 * mm, y, text)
        y -= 12

    # Kainos
    if show_prices and kainos:
        if y < 60 * mm:
            c.showPage()
            c.setFont(font_regular, 10)
            y = height - 30 * mm

        c.setFont(font_bold, 12)
        c.drawString(20 * mm, y, "Kainos")
        y -= 8
        c.setFont(font_regular, 9)

        headers = ["Kaina €", "Matas", "Tipas", "Nuo", "Iki", "Fiks. kiekis", "Galioja nuo", "Galioja iki"]
        col_x = [20, 45, 65, 88, 110, 135, 165, 195]  # mm
        for hx, h in zip(col_x, headers):
            c.drawString(hx * mm, y, h)
        y -= 6
        c.line(20 * mm, y, (width - 20 * mm), y)
        y -= 8

        for k in kainos:
            if y < 30 * mm:
                c.showPage()
                c.setFont(font_regular, 9)
                y = height - 30 * mm
            tipas = "Fiksuota" if k.yra_fiksuota else "Intervalinė"
            c.drawString(col_x[0] * mm, y, f"{k.kaina}")
            c.drawString(col_x[1] * mm, y, k.matas)
            c.drawString(col_x[2] * mm, y, tipas)
            c.drawString(col_x[3] * mm, y, str(k.kiekis_nuo or "—"))
            c.drawString(col_x[4] * mm, y, str(k.kiekis_iki or "—"))
            c.drawString(col_x[5] * mm, y, str(k.fiksuotas_kiekis or "—"))
            c.drawString(col_x[6] * mm, y, k.galioja_nuo.strftime("%Y-%m-%d") if k.galioja_nuo else "—")
            c.drawString(col_x[7] * mm, y, k.galioja_iki.strftime("%Y-%m-%d") if k.galioja_iki else "—")
            y -= 10

    # Brėžinių miniatiūros (PDF'e naudojam originalų vaizdą)
    if show_drawings and brez:
        if y < 60 * mm:
            c.showPage()
            c.setFont(font_regular, 10)
            y = height - 30 * mm

        c.setFont(font_bold, 12)
        c.drawString(20 * mm, y, "Brėžinių miniatiūros")
        y -= 10

        thumb_w = 50 * mm
        thumb_h = 35 * mm
        x = 20 * mm

        for b in brez:
            if y < 40 * mm:
                c.showPage()
                c.setFont(font_regular, 10)
                y = height - 30 * mm
                x = 20 * mm

            img_path = None
            try:
                img_path = b.failas.path
            except Exception:
                img_path = None

            if img_path and os.path.exists(img_path):
                try:
                    c.drawImage(ImageReader(img_path), x, y - thumb_h,
                                width=thumb_w, height=thumb_h,
                                preserveAspectRatio=True, mask="auto")
                except Exception:
                    c.rect(x, y - thumb_h, thumb_w, thumb_h)
            else:
                c.rect(x, y - thumb_h, thumb_w, thumb_h)

            title = b.pavadinimas or b.filename
            c.drawString(x, y - thumb_h - 8, title[:40])

            x += thumb_w + 10 * mm
            if x + thumb_w > width - 20 * mm:
                x = 20 * mm
                y -= thumb_h + 20

    # Pastabos
    if notes:
        if y < 60 * mm:
            c.showPage()
            c.setFont(font_regular, 10)
            y = height - 30 * mm

        c.setFont(font_bold, 12)
        c.drawString(20 * mm, y, "Pastabos / sąlygos")
        y -= 10
        c.setFont(font_regular, 10)

        for line in notes.splitlines():
            if y < 30 * mm:
                c.showPage()
                c.setFont(font_regular, 10)
                y = height - 30 * mm
            c.drawString(20 * mm, y, line)
            y -= 12

    # data apačioje
    c.setFont(font_regular, 8)
    c.drawRightString(width - 20 * mm, 15 * mm, datetime.now().strftime("%Y-%m-%d %H:%M"))

    c.showPage()
    c.save()

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="pasiulymas_{pozicija.poz_kodas}.pdf"'
    return response
