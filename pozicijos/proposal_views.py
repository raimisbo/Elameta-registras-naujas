# pozicijos/proposal_views.py
from __future__ import annotations

import io
import os
from datetime import datetime
from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle

from .models import Pozicija, KainosEilute


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

        "preview_hint": "Sugeneruojamas PDF.",
        "no_data": "Nėra duomenų.",
        "no_prices": "Nėra aktyvių kainų eilučių šiai pozicijai.",
        "no_drawings": "Nėra brėžinių.",

        "col_price": "Kaina",
        "col_unit": "Matas",
        "col_qty_from": "Kiekis nuo",
        "col_qty_to": "Kiekis iki",
        "col_valid_from": "Galioja nuo",
        "col_valid_to": "Galioja iki",
    },
    "en": {
        "offer_title": "OFFER",
        "date_label": "Date",

        "section_main": "Main information",
        "section_prices": "Prices (active lines)",
        "section_drawings": "Drawing thumbnails",
        "section_notes": "Notes / terms",

        "preview_hint": "PDF will be generated.",
        "no_data": "No data.",
        "no_prices": "There are no active price lines for this position.",
        "no_drawings": "No drawings.",

        "col_price": "Price",
        "col_unit": "Unit",
        "col_qty_from": "Qty from",
        "col_qty_to": "Qty to",
        "col_valid_from": "Valid from",
        "col_valid_to": "Valid to",
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

        "paslauga_ktl": "Papildoma paslauga: KTL",
        "paslauga_miltai": "Papildoma paslauga: Miltai",
        "paslauga_paruosimas": "Papildoma paslauga: Paruošimas",

        "miltu_kodas": "Miltų kodas",
        "miltu_serija": "Miltų serija",

        "pakavimas": "Pakavimas",
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

        "paruosimas": "Preparation",
        "padengimas": "Coating",
        "padengimo_standartas": "Coating standard",
        "spalva": "Color",

        "paslauga_ktl": "Extra service: KTL",
        "paslauga_miltai": "Extra service: Powder",
        "paslauga_paruosimas": "Extra service: Preparation",

        "miltu_kodas": "Powder code",
        "miltu_serija": "Powder series",

        "pakavimas": "Packaging",
        "pastabos": "Notes",
    },
}


def proposal_prepare(request, pk: int):
    """
    Suderinamumo endpointas: nukreipiam tiesiai į PDF.
    """
    lang = _get_lang(request)
    notes = (request.GET.get("notes", "") or "").strip()

    params: list[tuple[str, str]] = []
    if lang:
        params.append(("lang", lang))
    if notes:
        params.append(("notes", notes))

    url = reverse("pozicijos:pdf", args=[pk])
    if params:
        url += "?" + urlencode(params)
    return redirect(url)


def _register_fonts() -> tuple[str, str]:
    """
    Registruojam fontus su LT diakritika.
    Bandom iš MEDIA_ROOT/fonts, jei nėra – paliekam Helvetica.
    """
    fonts_dir = os.path.join(settings.MEDIA_ROOT, "fonts")

    regular_files = [
        os.path.join(fonts_dir, "HelveticaLT.ttf"),
        os.path.join(fonts_dir, "Arial.ttf"),
        os.path.join(fonts_dir, "DejaVuSans.ttf"),
    ]
    bold_files = [
        os.path.join(fonts_dir, "HelveticaLT-Bold.ttf"),
        os.path.join(fonts_dir, "Arial-Bold.ttf"),
        os.path.join(fonts_dir, "DejaVuSans-Bold.ttf"),
    ]

    reg_alias = "LT-Regular"
    bold_alias = "LT-Bold"

    reg_ok = next((p for p in regular_files if os.path.exists(p)), None)
    bold_ok = next((p for p in bold_files if os.path.exists(p)), None)

    if reg_ok:
        try:
            pdfmetrics.registerFont(TTFont(reg_alias, reg_ok))
        except Exception:
            reg_alias = "Helvetica"
    else:
        reg_alias = "Helvetica"

    if bold_ok:
        try:
            pdfmetrics.registerFont(TTFont(bold_alias, bold_ok))
        except Exception:
            bold_alias = "Helvetica-Bold" if reg_alias == "Helvetica" else reg_alias
    else:
        bold_alias = "Helvetica-Bold" if reg_alias == "Helvetica" else reg_alias

    return reg_alias, bold_alias


def _build_field_rows(pozicija: Pozicija, lang: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []

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

        # Boolean laukai: vietoj True/False rodom Yra/Nėra (LT) arba Yes/No (EN)
        if isinstance(value, bool):
            value_str = ("Yes" if value else "No") if lang == "en" else ("Yra" if value else "Nėra")
            rows.append((label, value_str))
            continue

        value_str: str
        get_disp = getattr(pozicija, f"get_{field.name}_display", None)
        if callable(get_disp) and getattr(field, "choices", None):
            try:
                value_str = str(get_disp())
            except Exception:
                value_str = str(value)
        else:
            if field.name == "atlikimo_terminas":
                try:
                    n = int(value)
                    value_str = f"{n} working days" if lang == "en" else f"{n} darbo dienos"
                except Exception:
                    value_str = str(value)
            else:
                value_str = str(value)

        rows.append((label, value_str))

    return rows


def _get_kainos_for_pdf(pozicija: Pozicija):
    """Naudojam tik 'aktuali' KainosEilute eilutes."""
    qs = KainosEilute.objects.filter(pozicija=pozicija, busena="aktuali")
    return qs.order_by(
        "matas",
        "kiekis_nuo",
        "kiekis_iki",
        "galioja_nuo",
        "galioja_iki",
        "-created",
    )


def _wrap_lines(text: str) -> list[str]:
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _draw_wrapped(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    max_w: float,
    font_name: str,
    font_size: int,
    leading: float,
    bottom: float,
    page_h: float,
) -> float:
    c.setFont(font_name, font_size)

    for para in _wrap_lines(text):
        words = para.split()
        if not words:
            y -= leading
            continue

        line = words[0]
        for w in words[1:]:
            test = f"{line} {w}"
            if stringWidth(test, font_name, font_size) <= max_w:
                line = test
            else:
                if y - leading < bottom:
                    c.showPage()
                    c.setFont(font_name, font_size)
                    y = page_h - 30 * mm
                c.drawString(x, y, line)
                y -= leading
                line = w

        if y - leading < bottom:
            c.showPage()
            c.setFont(font_name, font_size)
            y = page_h - 30 * mm
        c.drawString(x, y, line)
        y -= leading

    return y


def proposal_pdf(request, pk: int):
    """
    Visada generuojam PDF per ReportLab.
    """
    pozicija = get_object_or_404(Pozicija, pk=pk)

    lang = _get_lang(request)
    labels = LANG_LABELS.get(lang, LANG_LABELS["lt"])
    notes = (request.GET.get("notes", "") or "").strip()

    show_prices = True
    show_drawings = True

    field_rows = _build_field_rows(pozicija, lang)
    kainos = list(_get_kainos_for_pdf(pozicija))
    brez = list(pozicija.breziniai.all())

    font_regular, font_bold = _register_fonts()

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    page_w, page_h = A4

    left = 14 * mm
    right = 14 * mm
    top = 14 * mm
    bottom = 14 * mm

    # Header bar
    bar_h = 18 * mm
    c.setFillColor(colors.HexColor("#f3f4f6"))
    c.rect(0, page_h - bar_h, page_w, bar_h, stroke=0, fill=1)

    c.setFillColor(colors.HexColor("#111827"))
    c.setFont(font_bold, 13)
    title = f'{labels["offer_title"]} – {pozicija.poz_kodas or pozicija.pk}'
    c.drawString(left, page_h - 11 * mm, title)

    c.setFont(font_regular, 9)
    date_str = datetime.now().strftime("%Y-%m-%d")
    c.drawRightString(page_w - right, page_h - 11 * mm, f'{labels["date_label"]}: {date_str}')

    y = page_h - bar_h - 8 * mm

    # Sub line
    sub_parts = []
    if pozicija.klientas:
        sub_parts.append(str(pozicija.klientas))
    if pozicija.projektas:
        sub_parts.append(str(pozicija.projektas))
    sub_line = " • ".join(sub_parts)
    if sub_line:
        c.setFont(font_regular, 9)
        c.setFillColor(colors.HexColor("#6b7280"))
        c.drawString(left, y, sub_line)
        y -= 7 * mm

    # MAIN
    c.setFillColor(colors.HexColor("#111827"))
    c.setFont(font_bold, 10)
    c.drawString(left, y, labels["section_main"])
    y -= 5 * mm

    if field_rows:
        table_w = page_w - left - right
        label_w = 70 * mm
        value_w = table_w - label_w

        data = [[lbl, val] for (lbl, val) in field_rows]

        tbl = Table(data, colWidths=[label_w, value_w])
        tbl.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), font_regular),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f9fafb")),
                    ("FONTNAME", (0, 0), (0, -1), font_bold),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )

        w, h = tbl.wrapOn(c, table_w, y)
        if y - h < bottom:
            c.showPage()
            y = page_h - top
        tbl.drawOn(c, left, y - h)
        y -= h + 8 * mm
    else:
        c.setFont(font_regular, 9)
        c.setFillColor(colors.HexColor("#6b7280"))
        c.drawString(left, y, labels["no_data"])
        y -= 10 * mm

    # PRICES
    if show_prices:
        c.setFillColor(colors.HexColor("#111827"))
        c.setFont(font_bold, 10)
        c.drawString(left, y, labels["section_prices"])
        y -= 5 * mm

        if kainos:
            cols = [40 * mm, 25 * mm, 22 * mm, 22 * mm, 28 * mm, 28 * mm]
            data = [[
                labels["col_price"],
                labels["col_unit"],
                labels["col_qty_from"],
                labels["col_qty_to"],
                labels["col_valid_from"],
                labels["col_valid_to"],
            ]]

            for k in kainos:
                data.append([
                    (str(k.kaina) if k.kaina is not None else ""),
                    (k.matas or ""),
                    ("—" if k.kiekis_nuo is None else str(k.kiekis_nuo)),
                    ("—" if k.kiekis_iki is None else str(k.kiekis_iki)),
                    (k.galioja_nuo.strftime("%Y-%m-%d") if k.galioja_nuo else "—"),
                    (k.galioja_iki.strftime("%Y-%m-%d") if k.galioja_iki else "—"),
                ])

            tbl = Table(data, colWidths=cols)
            tbl.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, -1), font_regular),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("FONTNAME", (0, 0), (-1, 0), font_bold),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f9fafb")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )

            table_w = page_w - left - right
            w, h = tbl.wrapOn(c, table_w, y)
            if y - h < bottom:
                c.showPage()
                y = page_h - top
            tbl.drawOn(c, left, y - h)
            y -= h + 8 * mm
        else:
            c.setFont(font_regular, 9)
            c.setFillColor(colors.HexColor("#6b7280"))
            c.drawString(left, y, labels["no_prices"])
            y -= 10 * mm

    # DRAWINGS (miniatiūros iki 3)
    if show_drawings:
        c.setFillColor(colors.HexColor("#111827"))
        c.setFont(font_bold, 10)
        c.drawString(left, y, labels["section_drawings"])
        y -= 5 * mm

        thumbs = brez[:3]
        if not thumbs:
            c.setFont(font_regular, 9)
            c.setFillColor(colors.HexColor("#6b7280"))
            c.drawString(left, y, labels["no_drawings"])
            y -= 10 * mm
        else:
            thumb_w = (page_w - left - right - 2 * 6 * mm) / 3.0
            thumb_h = 32 * mm
            x = left

            for b in thumbs:
                c.setStrokeColor(colors.HexColor("#e5e7eb"))
                c.setFillColor(colors.HexColor("#f9fafb"))
                c.rect(x, y - thumb_h, thumb_w, thumb_h, stroke=1, fill=1)

                if getattr(b, "preview", None) and getattr(b.preview, "path", None) and os.path.exists(b.preview.path):
                    try:
                        img = ImageReader(b.preview.path)
                        c.drawImage(
                            img,
                            x + 2 * mm,
                            y - thumb_h + 2 * mm,
                            width=thumb_w - 4 * mm,
                            height=thumb_h - 4 * mm,
                            preserveAspectRatio=True,
                            anchor="c",
                            mask="auto",
                        )
                    except Exception:
                        pass
                else:
                    ext = (getattr(b, "ext", "") or "").lower()
                    mark = "3D" if ext in ("stp", "step") else "N/A"
                    c.setFont(font_bold, 12)
                    c.setFillColor(colors.HexColor("#6b7280"))
                    c.drawCentredString(x + thumb_w / 2, y - thumb_h / 2, mark)

                cap = (getattr(b, "pavadinimas", None) or getattr(b, "filename", None) or "").strip()
                if cap:
                    c.setFont(font_regular, 8)
                    c.setFillColor(colors.HexColor("#111827"))
                    c.drawString(x + 2 * mm, y - thumb_h - 4 * mm, cap[:60])

                x += thumb_w + 6 * mm

            y -= thumb_h + 12 * mm

    # NOTES
    combined_notes = ""
    if getattr(pozicija, "pastabos", None):
        combined_notes += (pozicija.pastabos or "").strip()
    if notes:
        if combined_notes:
            combined_notes += "\n\n"
        combined_notes += notes.strip()

    if combined_notes:
        c.setFillColor(colors.HexColor("#111827"))
        c.setFont(font_bold, 10)
        c.drawString(left, y, labels["section_notes"])
        y -= 5 * mm

        c.setFont(font_regular, 9)
        c.setFillColor(colors.HexColor("#111827"))
        y = _draw_wrapped(
            c=c,
            text=combined_notes,
            x=left,
            y=y,
            max_w=(page_w - left - right),
            font_name=font_regular,
            font_size=9,
            leading=12,
            bottom=bottom,
            page_h=page_h,
        )

    c.showPage()
    c.save()

    pdf = buf.getvalue()
    buf.close()

    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="pasiulymas_{pozicija.pk}.pdf"'
    return resp
