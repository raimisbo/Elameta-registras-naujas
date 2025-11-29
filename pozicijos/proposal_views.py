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
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from .models import Pozicija


# =====================================================================
#  LT šriftai
# =====================================================================

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


# =====================================================================
#  Pagalbiniai duomenų ruošėjai
# =====================================================================

def _build_field_rows(pozicija: Pozicija) -> list[tuple[str, str]]:
    """
    Grąžina (label, value) sąrašą visiems ne tuštiems Pozicija laukams.
    Naudojama ir HTML peržiūrai, ir PDF „Pagrindinė informacija“ lentelėje.
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


# =====================================================================
#  UI puslapis pasiūlymo paruošimui
# =====================================================================

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


# =====================================================================
#  PDF / HTML peržiūra
# =====================================================================

def proposal_pdf(request, pk: int):
    """
    Jei ?preview=1 – grąžina HTML (peržiūra su CSS, kaip puslapis).
    Kitu atveju – sugeneruoja PDF per ReportLab, su LT šriftais ir logotipu.

    Struktūra:
      - header (logo + rekvizitai + „PASIŪLYMAS“ + data)
      - Pagrindinė informacija (tokia pati, kaip HTML field_rows)
      - Kainos (jei pažymėta)
      - Brėžinių miniatiūros (jei pažymėta)
      - Pastabos / sąlygos iš formos (jei jos skiriasi nuo pozicijos pastabų)
    """
    pozicija = get_object_or_404(Pozicija, pk=pk)

    show_prices = bool(request.GET.get("show_prices"))
    show_drawings = bool(request.GET.get("show_drawings"))
    notes = request.GET.get("notes", "").strip()
    preview = bool(request.GET.get("preview"))

    # qs – HTML peržiūros "Atgal" mygtukui
    params: dict[str, str] = {}
    if show_prices:
        params["show_prices"] = "1"
    if show_drawings:
        params["show_drawings"] = "1"
    if notes:
        params["notes"] = notes
    qs = urlencode(params)

    field_rows = _build_field_rows(pozicija)
    kainos = _get_kainos_for_pdf(pozicija)
    brez = list(pozicija.breziniai.all())
    poz_pastabos = (pozicija.pastabos or "").strip()

    # --------- HTML peržiūra (tas pats šablonas, kaip iki šiol) ----------
    if preview:
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

    # =====================================================================
    #  Tikras PDF
    # =====================================================================
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    font_regular, font_bold = _register_fonts()

    margin_left = 18 * mm
    margin_right = 18 * mm
    bottom_margin = 20 * mm

    # --- vidiniai helperiai -------------------------------------------------

    def new_page_with_y(new_y: float | None = None) -> float:
        c.showPage()
        return height - (new_y or 30 * mm)

    def section_title(y: float, title: str) -> float:
        """
        Sekcijos antraštė kaip HTML <h2> – be numeracijos,
        PO ja paliekam šiek tiek daugiau oro (tuščią eilutę).
        """
        if y < bottom_margin + 30:
            y = new_page_with_y()
        c.setFont(font_bold, 12)
        c.setFillColor(colors.HexColor("#111827"))
        c.drawString(margin_left, y, title)
        y -= 5
        c.setStrokeColor(colors.HexColor("#e5e7eb"))
        c.setLineWidth(0.6)
        c.line(margin_left, y, width - margin_right, y)
        # + papildomas tarpas po linija (tuščia eilutė)
        return y - 16

    # --- viršutinė juosta + logo + rekvizitai ------------------------------

    top_bar_h = 18 * mm
    c.setFillColor(colors.HexColor("#f3f4f6"))
    c.rect(0, height - top_bar_h, width, top_bar_h, stroke=0, fill=1)

    c.setFillColor(colors.HexColor("#111827"))
    logo_path = os.path.join(settings.MEDIA_ROOT, "logo.png")
    if os.path.exists(logo_path):
        try:
            img = ImageReader(logo_path)
            logo_w = 28 * mm
            logo_h = 11 * mm
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

    company_name = getattr(settings, "OFFER_COMPANY_NAME", "") or "UAB Elameta"
    line1 = getattr(settings, "OFFER_COMPANY_LINE1", "Adresas, LT-00000, Miestas")
    line2 = getattr(
        settings,
        "OFFER_COMPANY_LINE2",
        "Tel. +370 000 00000, el. paštas info@elameta.lt",
    )
    right_x = width - margin_right

    c.setFont(font_bold, 10)
    c.drawRightString(right_x, height - 6 * mm, company_name)

    c.setFont(font_regular, 8)
    y_company = height - 10 * mm
    if line1:
        c.drawRightString(right_x, y_company, line1)
        y_company -= 3.5 * mm
    if line2:
        c.drawRightString(right_x, y_company, line2)

    # --- pavadinimas + data -------------------------------------------------

    top_bottom_y = height - top_bar_h
    d = 11 * mm  # tarpas nuo pilkos juostos
    title_y = top_bottom_y - d

    c.setFont(font_bold, 18)
    c.setFillColor(colors.HexColor("#111827"))
    c.drawCentredString(width / 2, title_y, "PASIŪLYMAS")

    c.setFont(font_regular, 9)
    date_y = title_y - 4 * mm
    c.drawRightString(
        width - margin_right,
        date_y,
        datetime.now().strftime("Data: %Y-%m-%d"),
    )

    # turinio pradžia
    y = title_y - d

    # plona linija po headeriu
    c.setStrokeColor(colors.HexColor("#e5e7eb"))
    c.setLineWidth(0.6)
    c.line(margin_left, y, width - margin_right, y)
    y -= 18

    # =====================================================================
    #  Pagrindinė informacija (kaip HTML field_rows)
    # =====================================================================

    y = section_title(y, "Pagrindinė informacija")

    table_x = margin_left
    table_w = width - margin_left - margin_right
    label_w = 60 * mm

    def label_row(y_pos: float, label: str, value: str | None) -> float:
        """
        Vienos eilutės label / value pora, kaip HTML lentelėje.
        Eilutės aukštį padidinam ~1.5 karto, kad tarpų būtų daugiau.
        """
        row_h = 18  # buvo 13
        if y_pos < bottom_margin + row_h + 5:
            y_pos = new_page_with_y()
            # pakartojam sekcijos pavadinimą puslapio viršuje
            y_pos = section_title(y_pos, "Pagrindinė informacija")

        val = value if (value not in (None, "")) else "—"

        # fonai
        c.setStrokeColor(colors.HexColor("#e5e7eb"))
        c.setLineWidth(0.4)
        c.setFillColor(colors.HexColor("#f9fafb"))
        c.rect(table_x, y_pos - row_h + 3, label_w, row_h, stroke=0, fill=1)
        c.setFillColor(colors.HexColor("#ffffff"))
        c.rect(
            table_x + label_w,
            y_pos - row_h + 3,
            table_w - label_w,
            row_h,
            stroke=0,
            fill=1,
        )

        # tekstai
        c.setFont(font_regular, 9)
        c.setFillColor(colors.HexColor("#4b5563"))
        c.drawString(table_x + 2, y_pos, label)
        c.setFillColor(colors.HexColor("#111827"))
        c.drawString(table_x + label_w + 3, y_pos, str(val))

        # apatinė linija
        c.setStrokeColor(colors.HexColor("#e5e7eb"))
        c.line(table_x, y_pos - 1, table_x + table_w, y_pos - 1)

        return y_pos - row_h

    if field_rows:
        for label, val in field_rows:
            y = label_row(y, label, val)
        y -= 8
    else:
        c.setFont(font_regular, 9)
        c.setFillColor(colors.HexColor("#6b7280"))
        c.drawString(margin_left, y, "Nėra duomenų.")
        y -= 12

    # =====================================================================
    #  Kainos
    # =====================================================================

    if show_prices:
        y = section_title(y, "Kainos (aktualios eilutės)")

        if kainos:
            if y < bottom_margin + 70:
                y = new_page_with_y()
                y = section_title(y, "Kainos (aktualios eilutės)")

            col_x = [
                margin_left,
                margin_left + 25 * mm,
                margin_left + 45 * mm,
                margin_left + 68 * mm,
                margin_left + 88 * mm,
                margin_left + 110 * mm,
                margin_left + 133 * mm,
                margin_left + 155 * mm,
            ]

            headers = [
                "Kaina €",
                "Matas",
                "Tipas",
                "Kiekis nuo",
                "Kiekis iki",
                "Fiks. kiekis",
                "Galioja nuo",
                "Galioja iki",
            ]

            header_h = 13
            c.setFillColor(colors.HexColor("#f9fafb"))
            c.rect(
                margin_left,
                y - header_h + 3,
                width - margin_left - margin_right,
                header_h,
                stroke=0,
                fill=1,
            )

            c.setFont(font_regular, 9)
            c.setFillColor(colors.HexColor("#374151"))
            for x_val, h_txt in zip(col_x, headers):
                c.drawString(x_val, y, h_txt)

            y -= 4
            c.setStrokeColor(colors.HexColor("#e5e7eb"))
            c.setLineWidth(0.5)
            c.line(margin_left, y, width - margin_right, y)
            y -= 8

            c.setFont(font_regular, 9)
            zebra = False
            row_h_prices = 16  # buvo 12 – daugiau tarpo tarp eilučių

            for k in kainos:
                if y < bottom_margin + row_h_prices + 8:
                    y = new_page_with_y()
                    y = section_title(y, "Kainos (aktualios eilutės)")

                    header_h = 13
                    c.setFillColor(colors.HexColor("#f9fafb"))
                    c.rect(
                        margin_left,
                        y - header_h + 3,
                        width - margin_left - margin_right,
                        header_h,
                        stroke=0,
                        fill=1,
                    )
                    c.setFont(font_regular, 9)
                    c.setFillColor(colors.HexColor("#374151"))
                    for x_val, h_txt in zip(col_x, headers):
                        c.drawString(x_val, y, h_txt)
                    y -= 4
                    c.setStrokeColor(colors.HexColor("#e5e7eb"))
                    c.setLineWidth(0.5)
                    c.line(margin_left, y, width - margin_right, y)
                    y -= 8
                    c.setFont(font_regular, 9)
                    zebra = False

                # zebra fonas
                if zebra:
                    c.setFillColor(colors.HexColor("#f9fafb"))
                    c.rect(
                        margin_left,
                        y - row_h_prices + 3,
                        width - margin_left - margin_right,
                        row_h_prices,
                        stroke=0,
                        fill=1,
                    )
                zebra = not zebra

                c.setFillColor(colors.HexColor("#111827"))
                tipas = "Fiksuota" if k.yra_fiksuota else "Intervalinė"

                c.drawString(col_x[0], y, f"{k.kaina}")
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

                y -= row_h_prices

            y -= 12
        else:
            c.setFont(font_regular, 9)
            c.setFillColor(colors.HexColor("#6b7280"))
            c.drawString(margin_left, y, "Aktyvių kainų eilučių šiai pozicijai nėra.")
            y -= 12

    # =====================================================================
    #  Brėžinių miniatiūros
    # =====================================================================

    if show_drawings and brez:
        y = section_title(y, "Brėžinių miniatiūros")

        thumb_w = 48 * mm
        thumb_h = 34 * mm
        x = margin_left

        for b in brez:
            if y < bottom_margin + thumb_h + 30:
                y = new_page_with_y()
                y = section_title(y, "Brėžinių miniatiūros")
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
                    c.setStrokeColor(colors.HexColor("#e5e7eb"))
                    c.rect(x, y - thumb_h, thumb_w, thumb_h)
            else:
                c.setStrokeColor(colors.HexColor("#e5e7eb"))
                c.rect(x, y - thumb_h, thumb_w, thumb_h)

            title = b.pavadinimas or b.filename
            c.setFont(font_regular, 8)
            c.setFillColor(colors.HexColor("#111827"))
            c.drawString(x, y - thumb_h - 8, title[:42])

            x += thumb_w + 10 * mm
            if x + thumb_w > width - margin_right:
                x = margin_left
                y -= thumb_h + 24

        y -= 12

    # =====================================================================
    #  Pastabos / sąlygos iš formos
    # =====================================================================

    if notes and notes.strip() != poz_pastabos:
        y = section_title(y, "Pastabos / sąlygos")
        if y < bottom_margin + 60:
            y = new_page_with_y()
            y = section_title(y, "Pastabos / sąlygos")

        c.setFillColor(colors.HexColor("#111827"))
        y = _draw_wrapped_text(
            c=c,
            text=notes,
            x=margin_left,
            y=y,
            max_width=width - margin_left - margin_right,
            font_name=font_regular,
            font_size=9.5,
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
    response["Content-Disposition"] = (
        f'inline; filename="pasiulymas_{pozicija.poz_kodas}.pdf"'
    )
    return response
