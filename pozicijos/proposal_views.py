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

        # Specialus formatas dabartinei kainai: be (EUR), su € prieš sumą
        if field.name == "kaina_eur":
            label = "Dabartinė kaina"
            rows.append((label, f"€ {value}"))
            continue

        label = str(field.verbose_name or field.name)
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


def _build_params_qs(show_prices: bool, show_drawings: bool, notes: str) -> str:
    """
    Pagal dabartinę formos būseną paruošia QS dalį be „preview“ parametro.
    Naudojama ir paruošimo formoje, ir peržiūros šablone (Atgal mygtukui).
    """
    params: dict[str, str] = {}
    if show_prices:
        params["show_prices"] = "1"
    if show_drawings:
        params["show_drawings"] = "1"
    notes_clean = (notes or "").strip()
    if notes_clean:
        params["notes"] = notes_clean
    return urlencode(params)


def _wrap_text_for_pdf(text: str, font_name: str, font_size: float, max_width: float) -> list[str]:
    """
    Paprastas žodžių laužymas pagal max_width.
    Grąžina sąrašą eilučių, kurios tilps į nurodytą plotį.
    """
    words = text.split()
    if not words:
        return [""]

    lines: list[str] = []
    current = words[0]

    for w in words[1:]:
        candidate = current + " " + w
        w_width = pdfmetrics.stringWidth(candidate, font_name, font_size)
        if w_width <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines


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

    qs = _build_params_qs(show_prices, show_drawings, notes)

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
    qs = _build_params_qs(show_prices, show_drawings, notes)

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
            "qs": qs,
        }
        return render(request, "pozicijos/proposal_pdf.html", ctx)

    # ===== Tikras PDF =====
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 20 * mm

    font_regular, font_bold = _register_fonts()
    c.setLineWidth(0.4)

    # ---- VIRŠUTINĖ PILKA JUOSTA + LOGO + REKVIZITAI ------------------------
    top_bar_h = 24 * mm
    top_offset = 10 * mm  # papildomas nusileidimas žemyn
    top_bar_y = height - top_bar_h - top_offset

    # pilka juosta per visą lapo plotį
    c.setFillColor(colors.HexColor("#F3F4F6"))
    c.rect(0, top_bar_y, width, top_bar_h, fill=1, stroke=0)

    logo_path = os.path.join(settings.MEDIA_ROOT, "logo.png")
    logo_h = 14 * mm
    logo_w = 35 * mm
    logo_y = top_bar_y + (top_bar_h - logo_h) / 2
    logo_x = margin

    if os.path.exists(logo_path):
        try:
            img = ImageReader(logo_path)
            c.drawImage(
                img,
                logo_x,
                logo_y,
                width=logo_w,
                height=logo_h,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception:
            pass

    # Rekvizitai dešinėje, ant pilkos juostos
    company_name = getattr(settings, "OFFER_COMPANY_NAME", "Įmonės pavadinimas")
    company_line1 = getattr(settings, "OFFER_COMPANY_LINE1", "Adresas, miestas")
    company_line2 = getattr(settings, "OFFER_COMPANY_LINE2", "Tel. / el. paštas")

    text_right_x = width - margin
    text_top_y = top_bar_y + top_bar_h - 6 * mm

    c.setFont(font_bold, 10)
    c.setFillColor(colors.HexColor("#111827"))
    c.drawRightString(text_right_x, text_top_y, company_name)

    c.setFont(font_regular, 8.5)
    c.setFillColor(colors.HexColor("#374151"))
    c.drawRightString(text_right_x, text_top_y - 4 * mm, company_line1)
    c.drawRightString(text_right_x, text_top_y - 8 * mm, company_line2)

    # ---- PAVADINIMAS IR KLIENTO BLOKAS -------------------------------------
    c.setFont(font_bold, 20)
    c.setFillColor(colors.HexColor("#111827"))
    # šiek tiek atitrauktas nuo pilkos juostos
    title_y = top_bar_y - 16 * mm
    c.drawCentredString(width / 2, title_y, "PASIŪLYMAS")

    c.setFont(font_regular, 10)
    c.setFillColor(colors.HexColor("#111827"))
    info_y = title_y - 16 * mm
    latest_info_y = info_y

    today_str = datetime.now().strftime("%Y-%m-%d")
    c.drawRightString(width - margin, info_y, f"Data: {today_str}")
    latest_info_y = info_y
    info_y -= 6 * mm

    if pozicija.klientas:
        c.drawString(margin, info_y, f"Klientas: {pozicija.klientas}")
        latest_info_y = info_y
        info_y -= 5 * mm
    if pozicija.projektas:
        c.drawString(margin, info_y, f"Projektas: {pozicija.projektas}")
        latest_info_y = info_y
        info_y -= 5 * mm

    c.drawString(margin, info_y, f"Pozicijos kodas: {pozicija.poz_kodas}")
    latest_info_y = info_y
    info_y -= 5 * mm
    if pozicija.poz_pavad:
        c.drawString(margin, info_y, f"Detalė: {pozicija.poz_pavad}")
        latest_info_y = info_y
        info_y -= 5 * mm

    # pilka linija PO viso šito bloko
    c.setStrokeColor(colors.HexColor("#E5E7EB"))
    line_y = latest_info_y - 4 * mm
    c.line(margin, line_y, width - margin, line_y)

    # turinio startas – aiškiai žemiau linijos
    y = line_y - 12 * mm

    # ---- PAGRINDINĖ INFORMACIJA – DVI KOLONOS ------------------------------
    c.setFillColor(colors.HexColor("#111827"))
    c.setFont(font_bold, 13)
    c.drawString(margin, y, "Pagrindinė informacija")
    y -= 6
    c.setStrokeColor(colors.HexColor("#D1D5DB"))
    c.line(margin, y, width - margin, y)
    y -= 14  # tarpas po brūkšniu

    c.setFont(font_regular, 9.5)
    label_font_size = 9.5
    value_font_size = 9.5

    col1_label_x = margin
    col1_val_x = margin + 30 * mm
    col2_label_x = margin + 90 * mm
    col2_val_x = margin + 120 * mm

    row_height = 7 * mm

    c.setFillColor(colors.HexColor("#111827"))
    row_y = y

    for idx, (label, val) in enumerate(field_rows):
        if idx % 2 == 0 and idx != 0:
            row_y -= row_height

        if row_y < 40 * mm:
            c.showPage()
            width, height = A4
            margin = 20 * mm
            c.setLineWidth(0.4)

            c.setFont(font_bold, 12)
            c.setFillColor(colors.HexColor("#111827"))
            c.drawString(margin, height - 30 * mm, "Pagrindinė informacija (tęsinys)")
            c.setStrokeColor(colors.HexColor("#D1D5DB"))
            c.line(margin, height - 32 * mm, width - margin, height - 32 * mm)

            row_y = height - 44 * mm
            c.setFont(font_regular, value_font_size)
            c.setFillColor(colors.HexColor("#111827"))

        if idx % 2 == 0:
            lx = col1_label_x
            vx = col1_val_x
        else:
            lx = col2_label_x
            vx = col2_val_x

        c.setFont(font_bold, label_font_size)
        c.setFillColor(colors.HexColor("#374151"))
        c.drawString(lx, row_y, f"{label}:")

        c.setFont(font_regular, value_font_size)
        c.setFillColor(colors.HexColor("#111827"))
        text_val = str(val)
        if len(text_val) > 60:
            text_val = text_val[:57] + "…"
        c.drawString(vx, row_y, text_val)

    if len(field_rows) % 2 == 1:
        row_y -= row_height

    y = row_y - 14 * mm

    # ---- POZICIJOS PASTABOS (pilnas laukas iš pozicija.pastabos) -----------
    poz_past = (pozicija.pastabos or "").strip()
    if poz_past:
        if y < 60 * mm:
            c.showPage()
            width, height = A4
            margin = 20 * mm
            c.setLineWidth(0.4)
            y = height - 30 * mm

        c.setFillColor(colors.HexColor("#111827"))
        c.setFont(font_bold, 13)
        c.drawString(margin, y, "Pozicijos pastabos")
        y -= 6
        c.setStrokeColor(colors.HexColor("#D1D5DB"))
        c.line(margin, y, width - margin, y)
        y -= 10

        font_size_poz = 9.5
        c.setFont(font_regular, font_size_poz)
        c.setFillColor(colors.HexColor("#111827"))

        max_width = width - 2 * margin
        wrapped_lines: list[str] = []
        for raw in poz_past.splitlines() or [poz_past]:
            if not raw.strip():
                wrapped_lines.append("")
                continue
            wrapped_lines.extend(
                _wrap_text_for_pdf(raw, font_regular, font_size_poz, max_width)
            )

        for line in wrapped_lines:
            if y < 30 * mm:
                c.showPage()
                width, height = A4
                margin = 20 * mm
                c.setLineWidth(0.4)
                c.setFont(font_regular, font_size_poz)
                y = height - 30 * mm
            c.drawString(margin, y, line)
            y -= 11

        y -= 8

    # ---- KAINOS -------------------------------------------------------------
    if show_prices and kainos:
        if y < 60 * mm:
            c.showPage()
            width, height = A4
            margin = 20 * mm
            c.setLineWidth(0.4)
            y = height - 30 * mm

        c.setFillColor(colors.HexColor("#111827"))
        c.setFont(font_bold, 13)
        c.drawString(margin, y, "Kainos")
        y -= 6
        c.setStrokeColor(colors.HexColor("#D1D5DB"))
        c.line(margin, y, margin + 30 * mm, y)
        y -= 10

        c.setFont(font_regular, 9)

        headers = ["Kaina", "Matas", "Tipas", "Nuo", "Iki", "Fiks. kiekis", "Galioja nuo", "Galioja iki"]
        col_x = [
            margin,
            margin + 25 * mm,
            margin + 40 * mm,
            margin + 63 * mm,
            margin + 80 * mm,
            margin + 98 * mm,
            margin + 125 * mm,
            margin + 150 * mm,
        ]

        c.setFillColor(colors.HexColor("#4B5563"))
        for hx, h in zip(col_x, headers):
            c.drawString(hx, y, h)
        y -= 4
        c.setStrokeColor(colors.HexColor("#E5E7EB"))
        c.line(margin, y, width - margin, y)
        y -= 8

        c.setFont(font_regular, 9)
        c.setFillColor(colors.HexColor("#111827"))

        for k in kainos:
            if y < 40 * mm:
                c.showPage()
                width, height = A4
                margin = 20 * mm
                c.setLineWidth(0.4)
                c.setFont(font_bold, 12)
                c.setFillColor(colors.HexColor("#111827"))
                c.drawString(margin, height - 30 * mm, "Kainos (tęsinys)")
                c.setStrokeColor(colors.HexColor("#D1D5DB"))
                c.line(margin, height - 32 * mm, width - margin, height - 32 * mm)
                y = height - 46 * mm
                c.setFont(font_regular, 9)
                c.setFillColor(colors.HexColor("#111827"))

            tipas = "Fiksuota" if k.yra_fiksuota else "Intervalinė"
            price_str = f"€ {k.kaina}"
            c.drawString(col_x[0], y, price_str)
            c.drawString(col_x[1], y, k.matas)
            c.drawString(col_x[2], y, tipas)
            c.drawString(col_x[3], y, str(k.kiekis_nuo or "—"))
            c.drawString(col_x[4], y, str(k.kiekis_iki or "—"))
            c.drawString(col_x[5], y, str(k.fiksuotas_kiekis or "—"))
            c.drawString(
                col_x[6],
                y,
                k.galioja_nuo.strftime("%Y-%m-%d") if k.galioja_nuo else "—",
            )
            c.drawString(
                col_x[7],
                y,
                k.galioja_iki.strftime("%Y-%m-%d") if k.galioja_iki else "—",
            )
            y -= 9

        y -= 10

    # ---- BRĖŽINIŲ MINIATIŪROS ----------------------------------------------
    if show_drawings and brez:
        y -= 6 * mm

        if y < 70 * mm:
            c.showPage()
            width, height = A4
            margin = 20 * mm
            c.setLineWidth(0.4)
            y = height - 30 * mm

        c.setFillColor(colors.HexColor("#111827"))
        c.setFont(font_bold, 13)
        c.drawString(margin, y, "Brėžinių miniatiūros")
        y -= 6
        c.setStrokeColor(colors.HexColor("#D1D5DB"))
        c.line(margin, y, margin + 45 * mm, y)
        y -= 12

        thumb_w = 50 * mm
        thumb_h = 35 * mm
        card_gap_x = 10 * mm
        card_gap_y = 18 * mm

        x = margin
        row_top_y = y

        for b in brez:
            if x + thumb_w > width - margin:
                x = margin
                row_top_y -= thumb_h + card_gap_y

            if row_top_y - thumb_h < 40 * mm:
                c.showPage()
                width, height = A4
                margin = 20 * mm
                c.setLineWidth(0.4)
                c.setFont(font_bold, 12)
                c.setFillColor(colors.HexColor("#111827"))
                c.drawString(margin, height - 30 * mm, "Brėžinių miniatiūros (tęsinys)")
                c.setStrokeColor(colors.HexColor("#D1D5DB"))
                c.line(margin, height - 32 * mm, width - margin, height - 32 * mm)
                row_top_y = height - 48 * mm
                x = margin

            card_h = thumb_h + 10 * mm
            c.setFillColor(colors.whitesmoke)
            c.roundRect(x, row_top_y - card_h, thumb_w, card_h, 3 * mm, fill=1, stroke=0)

            img_path = None
            try:
                img_path = b.failas.path
            except Exception:
                img_path = None

            img_y = row_top_y - 8 * mm
            if img_path and os.path.exists(img_path):
                try:
                    c.drawImage(
                        ImageReader(img_path),
                        x + 3 * mm,
                        img_y - thumb_h,
                        width=thumb_w - 6 * mm,
                        height=thumb_h,
                        preserveAspectRatio=True,
                        mask="auto",
                    )
                except Exception:
                    c.setStrokeColor(colors.HexColor("#D1D5DB"))
                    c.rect(x + 3 * mm, img_y - thumb_h, thumb_w - 6 * mm, thumb_h)
            else:
                c.setStrokeColor(colors.HexColor("#D1D5DB"))
                c.rect(x + 3 * mm, img_y - thumb_h, thumb_w - 6 * mm, thumb_h)

            # be pavadinimo teksto po paveiksliuku
            x += thumb_w + card_gap_x

        y = row_top_y - thumb_h - card_gap_y

    # ---- PASTABOS IŠ FORMOS (notes) ----------------------------------------
    if notes:
        if y < 60 * mm:
            c.showPage()
            width, height = A4
            margin = 20 * mm
            c.setLineWidth(0.4)
            y = height - 30 * mm

        c.setFillColor(colors.HexColor("#111827"))
        c.setFont(font_bold, 13)
        c.drawString(margin, y, "Pastabos / sąlygos")
        y -= 6
        c.setStrokeColor(colors.HexColor("#D1D5DB"))
        c.line(margin, y, margin + 45 * mm, y)
        y -= 10

        font_size_notes = 9.5
        c.setFont(font_regular, font_size_notes)
        c.setFillColor(colors.HexColor("#111827"))

        max_width = width - 2 * margin
        wrapped_lines: list[str] = []

        for raw in notes.splitlines() or [notes]:
            if not raw.strip():
                wrapped_lines.append("")
                continue
            wrapped_lines.extend(
                _wrap_text_for_pdf(raw, font_regular, font_size_notes, max_width)
            )

        for line in wrapped_lines:
            if y < 30 * mm:
                c.showPage()
                width, height = A4
                margin = 20 * mm
                c.setLineWidth(0.4)
                c.setFont(font_regular, font_size_notes)
                y = height - 30 * mm
            c.drawString(margin, y, line)
            y -= 11

    # ---- PORA INFORMACIJOS APAČIOJE ----------------------------------------
    c.setFont(font_regular, 8)
    c.setFillColor(colors.HexColor("#6B7280"))
    c.drawRightString(
        width - margin,
        15 * mm,
        datetime.now().strftime("%Y-%m-%d %H:%M"),
    )

    c.save()

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="pasiulymas_{pozicija.poz_kodas}.pdf"'
    return response
