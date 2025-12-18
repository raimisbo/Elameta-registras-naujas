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
from reportlab.platypus import Table, TableStyle

from .models import Pozicija


def _get_lang(request) -> str:
    """?lang=lt / ?lang=en; default – lt."""
    lang = (request.GET.get("lang") or "lt").lower()
    if lang.startswith("en"):
        return "en"
    return "lt"


LANG_LABELS = {
    "lt": {
        "offer_title": "PASIŪLYMAS",
        "date_label": "Data",

        "section_main": "Pagrindinė informacija",
        "section_prices": "Kainos (aktualios eilutės)",
        "section_drawings": "Brėžinių miniatiūros",
        "section_notes": "Pastabos / sąlygos",

        "no_data": "Nėra duomenų.",
        "no_prices": "Aktyvių kainų eilučių šiai pozicijai nėra.",
        "no_drawings": "Brėžinių nėra.",

        "col_price": "Kaina €",
        "col_unit": "Matas",
        "col_type": "Tipas",
        "col_qty_from": "Kiekis nuo",
        "col_qty_to": "Kiekis iki",
        "col_fixed_qty": "Fiks. kiekis",
        "col_valid_from": "Galioja nuo",
        "col_valid_to": "Galioja iki",

        "type_fixed": "Fiksuota",
        "type_interval": "Intervalinė",
    },
    "en": {
        "offer_title": "OFFER",
        "date_label": "Date",

        "section_main": "Main information",
        "section_prices": "Prices (current lines)",
        "section_drawings": "Drawing thumbnails",
        "section_notes": "Notes / terms",

        "no_data": "No data.",
        "no_prices": "There are no active price lines for this position.",
        "no_drawings": "No drawings.",

        "col_price": "Price €",
        "col_unit": "Unit",
        "col_type": "Type",
        "col_qty_from": "Qty from",
        "col_qty_to": "Qty to",
        "col_fixed_qty": "Fixed qty",
        "col_valid_from": "Valid from",
        "col_valid_to": "Valid until",

        "type_fixed": "Fixed",
        "type_interval": "Interval",
    },
}


FIELD_LABELS = {
    "lt": {
        "klientas": "Klientas",
        "projektas": "Projektas",
        "poz_kodas": "Brėžinio kodas",
        "poz_pavad": "Detalės pavadinimas",
        "metalas": "Metalo tipas",
        "plotas": "Plotas (m²)",
        "svoris": "Svoris (kg)",
        "kabinimo_budas": "Kabinimo būdas",
        "kabinimas_reme": "Kabinimas rėme",
        "detaliu_kiekis_reme": "Detalių kiekis rėme",
        "faktinis_kiekis_reme": "Faktinis kiekis rėme",
        "paruosimas": "Paruošimas",
        "padengimas": "Padengimas",
        "padengimo_standartas": "Padengimo standartas",
        "spalva": "Spalva",
        "maskavimas": "Maskavimas",
        "atlikimo_terminas": "Atlikimo terminas (darbo dienos)",
        "testai_kokybe": "Testai / kokybė",
        "pakavimas": "Pakavimas",
        "instrukcija": "Instrukcija",
        "pakavimo_dienos_norma": "Pakavimo dienos norma",
        "pak_po_ktl": "Pakavimas po KTL",
        "pak_po_milt": "Pakavimas po miltelinio",
        "kaina_eur": "Kaina €",
        "pastabos": "Pastabos",
    },
    "en": {
        "klientas": "Customer",
        "projektas": "Project",
        "poz_kodas": "Drawing code",
        "poz_pavad": "Part name",
        "metalas": "Metal type",
        "plotas": "Area (m²)",
        "svoris": "Weight (kg)",
        "kabinimo_budas": "Hanging method",
        "kabinimas_reme": "Hanging on frame",
        "detaliu_kiekis_reme": "Parts per frame",
        "faktinis_kiekis_reme": "Actual qty per frame",
        "paruosimas": "Pre-treatment",
        "padengimas": "Coating",
        "padengimo_standartas": "Coating standard",
        "spalva": "Colour",
        "maskavimas": "Masking",
        "atlikimo_terminas": "Lead time (working days)",
        "testai_kokybe": "Tests / quality",
        "pakavimas": "Packaging",
        "instrukcija": "Instruction",
        "pakavimo_dienos_norma": "Daily packing capacity",
        "pak_po_ktl": "Packing after KTL",
        "pak_po_milt": "Packing after powder",
        "kaina_eur": "Price €",
        "pastabos": "Notes",
    },
}


def _register_fonts() -> tuple[str, str]:
    """Pabandome paimti LT šriftus iš MEDIA_ROOT/fonts, kitaip – Helvetica."""
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


def _build_field_rows(pozicija: Pozicija, lang: str) -> list[tuple[str, str]]:
    """(label, value) sąrašas iš neužpildytų Pozicija laukų."""
    rows: list[tuple[str, str]] = []

    # svarbu: praleidžiam legacy datą, kad nesimaišytų su nauju darbo dienų lauku
    skip = {"id", "created", "updated", "atlikimo_terminas_data"}

    labels_map = FIELD_LABELS.get(lang, FIELD_LABELS["lt"])

    for field in pozicija._meta.fields:
        if field.name in skip:
            continue

        value = getattr(pozicija, field.name, None)
        if value in (None, ""):
            continue

        label = labels_map.get(field.name)
        if not label:
            vn = field.verbose_name or field.name
            label = str(vn).capitalize()

        # special-case: darbo dienų sufiksas
        if field.name == "atlikimo_terminas":
            try:
                n = int(value)
                if lang == "en":
                    value_str = f"{n} working days"
                else:
                    value_str = f"{n} darbo dienos"
            except Exception:
                value_str = str(value)
        else:
            value_str = str(value)

        rows.append((label, value_str))

    return rows


def _get_kainos_for_pdf(pozicija: Pozicija):
    """Naudojam tik 'aktuali' KainosEilute eilutes."""
    return pozicija.kainu_eilutes.filter(busena="aktuali").order_by(
        "matas",
        "yra_fiksuota",
        "kiekis_nuo",
        "fiksuotas_kiekis",
        "galioja_nuo",
    )


def _normalize_multiline(text: str) -> str:
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
    """Paprastas word-wrap tekstui; grąžina naują y."""
    if leading is None:
        leading = font_size * 1.3

    c.setFont(font_name, font_size)
    text = _normalize_multiline(text)
    paragraphs = text.split("\n")

    for para in paragraphs:
        words = para.split()
        if not words:
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


def proposal_prepare(request, pk: int):
    """UI puslapis – varnelių + pastabų pasirinkimas."""
    pozicija = get_object_or_404(Pozicija, pk=pk)
    lang = _get_lang(request)

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
    if lang:
        params["lang"] = lang
    qs = urlencode(params)

    context = {
        "pozicija": pozicija,
        "show_prices": show_prices,
        "show_drawings": show_drawings,
        "notes": notes,
        "qs": qs,
        "lang": lang,
    }
    return render(request, "pozicijos/proposal_prepare.html", context)


def proposal_pdf(request, pk: int):
    """
    Jei ?preview=1 – HTML peržiūra (su CSS).
    Kitu atveju – PDF per ReportLab.
    """
    pozicija = get_object_or_404(Pozicija, pk=pk)

    lang = _get_lang(request)
    labels = LANG_LABELS.get(lang, LANG_LABELS["lt"])

    show_prices = bool(request.GET.get("show_prices"))
    show_drawings = bool(request.GET.get("show_drawings"))
    notes = request.GET.get("notes", "").strip()
    preview = bool(request.GET.get("preview"))

    params: dict[str, str] = {}
    if show_prices:
        params["show_prices"] = "1"
    if show_drawings:
        params["show_drawings"] = "1"
    if notes:
        params["notes"] = notes
    if lang:
        params["lang"] = lang
    qs = urlencode(params)

    field_rows = _build_field_rows(pozicija, lang)
    kainos = list(_get_kainos_for_pdf(pozicija))
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
            "qs": qs,
            "lang": lang,
            "labels": labels,
        }
        return render(request, "pozicijos/proposal_pdf.html", ctx)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    font_regular, font_bold = _register_fonts()

    margin_left = 18 * mm
    margin_right = 18 * mm
    bottom_margin = 20 * mm

    def new_page_y() -> float:
        c.showPage()
        return height - 30 * mm

    top_bar_h = 18 * mm
    c.setFillColor(colors.HexColor("#f3f4f6"))
    c.rect(0, height - top_bar_h, width, top_bar_h, stroke=0, fill=1)

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
    c.setFillColor(colors.HexColor("#111827"))
    c.drawRightString(right_x, height - 6 * mm, company_name)

    c.setFont(font_regular, 8)
    y_company = height - 10 * mm
    if line1:
        c.drawRightString(right_x, y_company, line1)
        y_company -= 3.5 * mm
    if line2:
        c.drawRightString(right_x, y_company, line2)

    top_bottom_y = height - top_bar_h
    d = 11 * mm
    title_y = top_bottom_y - d

    c.setFont(font_bold, 18)
    c.setFillColor(colors.HexColor("#111827"))
    c.drawCentredString(width / 2, title_y, labels["offer_title"])

    c.setFont(font_regular, 9)
    c.drawRightString(
        width - margin_right,
        title_y - 4 * mm,
        datetime.now().strftime(f"{labels['date_label']}: %Y-%m-%d"),
    )

    y = title_y - d

    c.setStrokeColor(colors.HexColor("#e5e7eb"))
    c.setLineWidth(0.6)
    c.line(margin_left, y, width - margin_right, y)
    y -= 18

    c.setFont(font_bold, 12)
    c.setFillColor(colors.HexColor("#111827"))
    c.drawString(margin_left, y, labels["section_main"])
    y -= 5
    c.setStrokeColor(colors.HexColor("#e5e7eb"))
    c.setLineWidth(0.6)
    c.line(margin_left, y, width - margin_right, y)
    y -= 8

    if field_rows:
        table_width = width - margin_left - margin_right
        label_col_width = 70 * mm
        value_col_width = table_width - label_col_width

        data = [[lbl, val] for lbl, val in field_rows]

        tbl = Table(data, colWidths=[label_col_width, value_col_width])
        tbl.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), font_regular),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#4b5563")),
                    ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#111827")),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f9fafb")),
                    ("BACKGROUND", (1, 0), (1, -1), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
                    ("BOX", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )

        tw, th = tbl.wrap(table_width, 0)
        if y - th < bottom_margin:
            y = new_page_y()
        tbl.drawOn(c, margin_left, y - th)
        y = y - th - 16
    else:
        c.setFont(font_regular, 9)
        c.setFillColor(colors.HexColor("#6b7280"))
        c.drawString(margin_left, y, labels["no_data"])
        y -= 12

    # ... (likusi PDF generavimo dalis pas tave lieka nepakitusi) ...

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
    filename = f"pasiulymas_{pozicija.poz_kodas or pozicija.pk}.pdf"
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response
