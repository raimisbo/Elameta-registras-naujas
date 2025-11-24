# pozicijos/proposal_views.py
from __future__ import annotations

import io
import os
from datetime import datetime
from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth

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
    Paruošia (label, value) sąrašą iš visų Pozicija laukų HTML peržiūrai.
    Tušti laukai praleidžiami. Tai naudojama tik proposal_pdf.html šablone.
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
        rows.append((label, str(value)))
    return rows


def _get_kainos_for_pdf(pozicija: Pozicija):
    """
    Naudojam naują modelį KainosEilute (related_name='kainu_eilutes').
    Renkam tik aktualias eilutes.
    """
    return pozicija.kainu_eilutes.filter(busena="aktuali").order_by(
        "matas", "yra_fiksuota", "kiekis_nuo", "fiksuotas_kiekis", "galioja_nuo"
    )


def _normalize_multiline(text: str) -> str:
    """Sutvarkom CR/LF kombinacijas, kad neliktų „keistų“ simbolių."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _draw_wrapped_text(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    max_width: float,
    font_name: str,
    font_size: float,
    page_width: float,
    page_height: float,
    bottom_margin: float,
    leading: float | None = None,
) -> float:
    """
    Teksto laužymas pagal realų plotį. Grąžina naują y poziciją.
    Jei pritrūksta vietos – kuriamas naujas puslapis (be papildomo headerio).
    """
    if leading is None:
        leading = font_size * 1.3

    c.setFont(font_name, font_size)
    text = _normalize_multiline(text)
    paragraphs = text.split("\n")

    for para in paragraphs:
        words = para.split()
        if not words:
            # tuščia eilutė
            if y - leading < bottom_margin:
                c.showPage()
                c.setFont(font_name, font_size)
                y = page_height - 30 * mm
            y -= leading
            continue

        line = words[0]
        for w in words[1:]:
            test_line = f"{line} {w}"
            if stringWidth(test_line, font_name, font_size) <= max_width:
                line = test_line
            else:
                if y - leading < bottom_margin:
                    c.showPage()
                    c.setFont(font_name, font_size)
                    y = page_height - 30 * mm
                c.drawString(x, y, line)
                y -= leading
                line = w

        if y - leading < bottom_margin:
            c.showPage()
            c.setFont(font_name, font_size)
            y = page_height - 30 * mm
        c.drawString(x, y, line)
        y -= leading

    return y


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
    poz_pastabos = (pozicija.pastabos or "").strip()

    if preview:
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

    margin_left = 20 * mm
    margin_right = 20 * mm
    bottom_margin = 20 * mm

    # Viršutinė pilka juosta
    top_bar_h = 18 * mm
    c.setFillColor(colors.HexColor("#f3f4f6"))
    c.rect(0, height - top_bar_h, width, top_bar_h, stroke=0, fill=1)

    # Logo kairėje
    c.setFillColor(colors.HexColor("#111827"))
    logo_path = os.path.join(settings.MEDIA_ROOT, "logo.png")
    if os.path.exists(logo_path):
        try:
            img = ImageReader(logo_path)
            logo_w = 26 * mm
            logo_h = 10 * mm
            y_logo = height - top_bar_h + (top_bar_h - logo_h) / 2
            c.drawImage(
                img,
                margin_left,
                y_logo,
                width=logo_w,
                height=logo_h,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception:
            pass

    # Rekvizitai – dešinė pilkos juostos pusė (lygiuojam į dešinę)
    company_name = getattr(settings, "OFFER_COMPANY_NAME", "") or "UAB Elameta"
    line1 = getattr(settings, "OFFER_COMPANY_LINE1", "")
    line2 = getattr(settings, "OFFER_COMPANY_LINE2", "")
    right_x = width - margin_right

    c.setFont(font_bold, 11)
    c.drawRightString(right_x, height - 7 * mm, company_name)

    c.setFont(font_regular, 8)
    y_company = height - 11 * mm
    if line1:
        c.drawRightString(right_x, y_company, line1)
        y_company -= 4 * mm
    if line2:
        c.drawRightString(right_x, y_company, line2)

    # Pavadinimas "PASIŪLYMAS" – simetriškas tarpas nuo juostos ir iki turinio
    top_bottom_y = height - top_bar_h
    d = 10 * mm  # atstumas virš ir po pavadinimo
    title_y = top_bottom_y - d

    c.setFont(font_bold, 20)
    c.setFillColor(colors.HexColor("#111827"))
    c.drawCentredString(width / 2, title_y, "PASIŪLYMAS")

    # Data po pavadinimu, dešinėje
    c.setFont(font_regular, 9)
    date_y = title_y - 5 * mm
    c.drawRightString(
        width - margin_right,
        date_y,
        datetime.now().strftime("Data: %Y-%m-%d"),
    )

    # Turinio pradžia – simetriškai žemiau pavadinimo
    y = title_y - d

    # horizontali linija
    c.setStrokeColor(colors.HexColor("#e5e7eb"))
    c.setLineWidth(0.5)
    c.line(margin_left, y, width - margin_right, y)
    y -= 16

    # Pagrindinė informacija – antraštė
    c.setFont(font_bold, 14)
    c.setFillColor(colors.HexColor("#111827"))
    c.drawString(margin_left, y, "Pagrindinė informacija")
    y -= 8
    c.setStrokeColor(colors.HexColor("#e5e7eb"))
    c.line(margin_left, y, width - margin_right, y)
    y -= 14

    # Dviejų kolonų lentelė
    c.setFont(font_regular, 10)
    label_color = colors.HexColor("#374151")
    value_color = colors.HexColor("#111827")

    col_gap = 12 * mm
    col_width = (width - margin_left - margin_right - col_gap) / 2

    left_label_x = margin_left
    left_value_x = margin_left + 30 * mm
    right_label_x = margin_left + col_width + col_gap
    right_value_x = right_label_x + 30 * mm
    row_h = 12

    left_rows = [
        ("Klientas:", pozicija.klientas or ""),
        ("Kodas:", pozicija.poz_kodas or ""),
        ("Plotas:", f"{pozicija.plotas}" if pozicija.plotas is not None else ""),
        (
            "Dabartinė kaina:",
            f"€ {pozicija.kaina_eur}" if pozicija.kaina_eur is not None else "",
        ),
    ]
    right_rows = [
        ("Projektas:", pozicija.projektas or ""),
        ("Pavadinimas:", pozicija.poz_pavad or ""),
        ("Pakavimas:", pozicija.pakavimas or ""),
    ]

    max_rows = max(len(left_rows), len(right_rows))
    for i in range(max_rows):
        row_y = y - i * row_h
        if row_y < bottom_margin + 40:
            c.showPage()
            c.setFont(font_regular, 10)
            row_y = height - 40 * mm

        if i < len(left_rows):
            label, val = left_rows[i]
            if val:
                c.setFillColor(label_color)
                c.drawString(left_label_x, row_y, label)
                c.setFillColor(value_color)
                c.drawString(left_value_x, row_y, str(val))

        if i < len(right_rows):
            label, val = right_rows[i]
            if val:
                c.setFillColor(label_color)
                c.drawString(right_label_x, row_y, label)
                c.setFillColor(value_color)
                c.drawString(right_value_x, row_y, str(val))

    # daugiau oro po pagrindinės informacijos
    y = y - max_rows * row_h - 20

    # Pozicijos pastabos
    if poz_pastabos:
        c.setFont(font_bold, 13)
        c.setFillColor(colors.HexColor("#111827"))
        c.drawString(margin_left, y, "Pozicijos pastabos")
        y -= 8
        c.setStrokeColor(colors.HexColor("#e5e7eb"))
        c.line(margin_left, y, width - margin_right, y)
        y -= 10

        c.setFillColor(colors.HexColor("#111827"))
        y = _draw_wrapped_text(
            c=c,
            text=poz_pastabos,
            x=margin_left,
            y=y,
            max_width=width - margin_left - margin_right,
            font_name=font_regular,
            font_size=10,
            page_width=width,
            page_height=height,
            bottom_margin=bottom_margin,
        )
        y -= 10  # tarpas prieš Kainas

    # Kainos
    if show_prices and kainos:
        if y < bottom_margin + 60:
            c.showPage()
            y = height - 30 * mm

        c.setFont(font_bold, 13)
        c.setFillColor(colors.HexColor("#111827"))
        c.drawString(margin_left, y, "Kainos")
        y -= 8
        c.setStrokeColor(colors.HexColor("#e5e7eb"))
        c.line(margin_left, y, width - margin_right, y)
        y -= 10

        c.setFont(font_regular, 9)
        headers = [
            "Kaina",
            "Matas",
            "Tipas",
            "Nuo",
            "Iki",
            "Fiks. kiekis",
            "Galioja nuo",
            "Galioja iki",
        ]
        col_x = [20, 40, 60, 82, 100, 125, 150, 178]  # mm

        for hx, h in zip(col_x, headers):
            c.drawString(hx * mm, y, h)
        y -= 4
        c.line(margin_left, y, width - margin_right, y)
        y -= 8

        for k in kainos:
            if y < bottom_margin + 20:
                c.showPage()
                c.setFont(font_regular, 9)
                y = height - 30 * mm

            tipas = "Fiksuota" if k.yra_fiksuota else "Intervalinė"
            c.drawString(col_x[0] * mm, y, f"€ {k.kaina}")
            c.drawString(col_x[1] * mm, y, k.matas)
            c.drawString(col_x[2] * mm, y, tipas)
            c.drawString(col_x[3] * mm, y, str(k.kiekis_nuo or "—"))
            c.drawString(col_x[4] * mm, y, str(k.kiekis_iki or "—"))
            c.drawString(col_x[5] * mm, y, str(k.fiksuotas_kiekis or "—"))
            c.drawString(
                col_x[6] * mm,
                y,
                k.galioja_nuo.strftime("%Y-%m-%d") if k.galioja_nuo else "—",
            )
            c.drawString(
                col_x[7] * mm,
                y,
                k.galioja_iki.strftime("%Y-%m-%d") if k.galioja_iki else "—",
            )
            y -= 10

        y -= 6

    # Brėžinių miniatiūros
    if show_drawings and brez:
        if y < bottom_margin + 60:
            c.showPage()
            y = height - 30 * mm

        c.setFont(font_bold, 13)
        c.setFillColor(colors.HexColor("#111827"))
        c.drawString(margin_left, y, "Brėžinių miniatiūros")
        y -= 10

        thumb_w = 50 * mm
        thumb_h = 35 * mm
        x = margin_left

        for b in brez:
            if y < bottom_margin + thumb_h + 20:
                c.showPage()
                y = height - 30 * mm
                x = margin_left

            img_path = None
            try:
                rel_preview = b._preview_relpath()
                candidate = os.path.join(settings.MEDIA_ROOT, rel_preview)
                if os.path.exists(candidate):
                    img_path = candidate
                else:
                    img_path = b.failas.path
            except Exception:
                img_path = None

            if img_path and os.path.exists(img_path):
                try:
                    c.drawImage(
                        ImageReader(img_path),
                        x,
                        y - thumb_h,
                        width=thumb_w,
                        height=thumb_h,
                        preserveAspectRatio=True,
                        mask="auto",
                    )
                except Exception:
                    c.rect(x, y - thumb_h, thumb_w, thumb_h)
            else:
                c.rect(x, y - thumb_h, thumb_w, thumb_h)

            title = b.pavadinimas or b.filename
            c.setFont(font_regular, 8)
            c.drawString(x, y - thumb_h - 8, title[:40])

            x += thumb_w + 10 * mm
            if x + thumb_w > width - margin_right:
                x = margin_left
                y -= thumb_h + 24

        y -= 6

    # Papildomos pastabos iš formos (jei kitokios nei pozicijos pastabos)
    if notes and notes.strip() != poz_pastabos:
        if y < bottom_margin + 60:
            c.showPage()
            y = height - 30 * mm

        c.setFont(font_bold, 13)
        c.setFillColor(colors.HexColor("#111827"))
        c.drawString(margin_left, y, "Pastabos / sąlygos")
        y -= 8
        c.setStrokeColor(colors.HexColor("#e5e7eb"))
        c.line(margin_left, y, width - margin_right, y)
        y -= 10

        c.setFillColor(colors.HexColor("#111827"))
        y = _draw_wrapped_text(
            c=c,
            text=notes,
            x=margin_left,
            y=y,
            max_width=width - margin_left - margin_right,
            font_name=font_regular,
            font_size=10,
            page_width=width,
            page_height=height,
            bottom_margin=bottom_margin,
        )

    # data / laikas apačioje
    c.setFont(font_regular, 8)
    c.setFillColor(colors.HexColor("#6b7280"))
    c.drawRightString(
        width - margin_right,
        15 * mm,
        datetime.now().strftime("%Y-%m-%d %H:%M"),
    )

    c.showPage()
    c.save()

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="pasiulymas_{pozicija.poz_kodas}.pdf"'
    return response
