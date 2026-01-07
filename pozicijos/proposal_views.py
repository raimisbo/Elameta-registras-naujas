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
    Suderinamumo endpointas: nukreipiam į PDF (HTML preview nebelieka).
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

    candidates_regular = [
        os.path.join(fonts_dir, "HelveticaLT.ttf"),
        os.path.join(fonts_dir, "Arial.ttf"),
        os.path.join(fonts_dir, "DejaVuSans.ttf"),
    ]
    candidates_bold = [
        os.path.join(fonts_dir, "HelveticaLT-Bold.ttf"),
        os.path.join(fonts_dir, "Arial-Bold.ttf"),
        os.path.join(fonts_dir, "DejaVuSans-Bold.ttf"),
    ]

    def register_font(alias: str, path: str) -> str | None:
        try:
            pdfmetrics.registerFont(TTFont(alias, path))
            return alias
        except Exception:
            return None

    regular = "Helvetica"
    bold = "Helvetica-Bold"

    reg_path = next((p for p in candidates_regular if os.path.exists(p)), None)
    bold_path = next((p for p in candidates_bold if os.path.exists(p)), None)

    if reg_path:
        regular = register_font("LT-Regular", reg_path) or regular
    if bold_path:
        bold = register_font("LT-Bold", bold_path) or bold
    else:
        bold = bold if bold != "Helvetica-Bold" else (regular if regular != "Helvetica" else bold)

    return regular, bold


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
    qs = pozicija.kainos_eilutes.filter(busena="aktuali")
    return qs.order_by(
        "matas",
        "kiekis_nuo",
        "kiekis_iki",
        "galioja_nuo",
        "galioja_iki",
        "-created",
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
    font_size: int,
    page_height: float,
    bottom_margin: float,
    leading: float = 12,
) -> float:
    c.setFont(font_name, font_size)
    text = _normalize_multiline(text).strip()
    if not text:
        return y

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


def proposal_pdf(request, pk: int):
    """
    Visada generuojam PDF per ReportLab (HTML preview nebelieka).
    Visada rodom: kainas + brėžinių miniatiūras.
    Kalba pasirenkama per ?lang=lt|en.
    """
    pozicija = get_object_or_404(Pozicija, pk=pk)

    lang = _get_lang(request)
    labels = LANG_LABELS.get(lang, LANG_LABELS["lt"])

    # visada rodom viską
    show_prices = True
    show_drawings = True

    notes = (request.GET.get("notes", "") or "").strip()

    field_rows = _build_field_rows(pozicija, lang)
    kainos = list(_get_kainos_for_pdf(pozicija))
    brez = list(pozicija.breziniai.all())
    poz_pastabos = (pozicija.pastabos or "").strip()

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

    # ===== Top bar =====
    top_bar_h = 18 * mm
    c.setFillColor(colors.HexColor("#f3f4f6"))
    c.rect(0, height - top_bar_h, width, top_bar_h, stroke=0, fill=1)

    # Logo (optional)
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

    # Company block (right)
    company_name = getattr(settings, "OFFER_COMPANY_NAME", "") or "UAB Elameta"
    line1 = getattr(settings, "OFFER_COMPANY_LINE1", "Adresas, LT-00000, Miestas")
    line2 = getattr(settings, "OFFER_COMPANY_LINE2", "Tel. +370 000 00000, el. paštas info@elameta.lt")
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

    # ===== Header (title + preview right) =====
    header_top = height - top_bar_h - 6 * mm
    header_h = 46 * mm
    header_bottom = header_top - header_h

    # Right preview box (first drawing)
    preview_w = 62 * mm
    preview_h = header_h
    preview_x = width - margin_right - preview_w
    preview_y = header_bottom

    # Pick hero drawing
    hero = brez[0] if brez else None
    hero_img_path = None
    if hero is not None:
        try:
            if getattr(hero, "preview", None) and getattr(hero.preview, "path", None):
                p = hero.preview.path
                if p and os.path.exists(p):
                    hero_img_path = p
        except Exception:
            hero_img_path = None

    # Draw preview frame
    c.setStrokeColor(colors.HexColor("#e5e7eb"))
    c.setFillColor(colors.HexColor("#f9fafb"))
    c.rect(preview_x, preview_y, preview_w, preview_h, stroke=1, fill=1)

    if hero_img_path:
        try:
            c.drawImage(
                ImageReader(hero_img_path),
                preview_x + 2,
                preview_y + 2,
                width=preview_w - 4,
                height=preview_h - 4,
                preserveAspectRatio=True,
                anchor="c",
                mask="auto",
            )
        except Exception:
            hero_img_path = None

    if not hero_img_path:
        ext = (getattr(hero, "ext", "") or "").lower() if hero is not None else ""
        mark = "3D" if ext in {"stp", "step"} else "N/A"
        c.setFont(font_bold, 14)
        c.setFillColor(colors.HexColor("#6b7280"))
        c.drawCentredString(preview_x + preview_w / 2, preview_y + preview_h / 2, mark)

    # Left header text area
    x_left = margin_left

    c.setFillColor(colors.HexColor("#111827"))
    c.setFont(font_bold, 16)
    c.drawString(x_left, header_top - 6 * mm, labels["offer_title"])

    c.setFont(font_regular, 9)
    c.setFillColor(colors.HexColor("#111827"))
    c.drawString(
        x_left,
        header_top - 12.5 * mm,
        f"Pozicija: {pozicija.poz_kodas or pozicija.pk}",
    )
    c.setFillColor(colors.HexColor("#6b7280"))
    c.drawString(
        x_left,
        header_top - 17 * mm,
        datetime.now().strftime(f"{labels['date_label']}: %Y-%m-%d"),
    )

    # Client / project line (if any)
    sub_parts = []
    if pozicija.klientas:
        sub_parts.append(str(pozicija.klientas))
    if pozicija.projektas:
        sub_parts.append(str(pozicija.projektas))
    sub_line = " • ".join(sub_parts)
    if sub_line:
        c.setFillColor(colors.HexColor("#6b7280"))
        c.setFont(font_regular, 9)
        c.drawString(x_left, header_top - 22 * mm, sub_line)

    # Divider under header
    y = header_bottom - 8
    c.setStrokeColor(colors.HexColor("#e5e7eb"))
    c.setLineWidth(0.6)
    c.line(margin_left, y, width - margin_right, y)
    y -= 18

    def draw_section_title(title: str) -> None:
        nonlocal y
        if y < bottom_margin + 20 * mm:
            y = new_page_y()

        c.setFont(font_bold, 12)
        c.setFillColor(colors.HexColor("#111827"))
        c.drawString(margin_left, y, title)
        y -= 5
        c.setStrokeColor(colors.HexColor("#e5e7eb"))
        c.setLineWidth(0.6)
        c.line(margin_left, y, width - margin_right, y)
        y -= 8

    # ===== Main info =====
    draw_section_title(labels["section_main"])

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

        tw, th = tbl.wrap(table_width, 0)
        if y - th < bottom_margin:
            y = new_page_y()
        tbl.drawOn(c, margin_left, y - th)
        y = y - th - 14
    else:
        c.setFont(font_regular, 9)
        c.setFillColor(colors.HexColor("#6b7280"))
        c.drawString(margin_left, y, labels["no_data"])
        y -= 12

    # ===== Prices =====
    if show_prices:
        draw_section_title(labels["section_prices"])

        if kainos:
            table_width = width - margin_left - margin_right
            col_widths = [
                40 * mm,
                25 * mm,
                22 * mm,
                22 * mm,
                28 * mm,
                28 * mm,
            ]

            header = [
                labels["col_price"],
                labels["col_unit"],
                labels["col_qty_from"],
                labels["col_qty_to"],
                labels["col_valid_from"],
                labels["col_valid_to"],
            ]
            rows = [header]

            for k in kainos:
                row = [
                    "" if k.kaina is None else str(k.kaina),
                    str(k.matas or ""),
                    "—" if k.kiekis_nuo is None else str(k.kiekis_nuo),
                    "—" if k.kiekis_iki is None else str(k.kiekis_iki),
                    k.galioja_nuo.strftime("%Y-%m-%d") if k.galioja_nuo else "—",
                    k.galioja_iki.strftime("%Y-%m-%d") if k.galioja_iki else "—",
                ]
                rows.append(row)

            tbl = Table(rows, colWidths=col_widths, repeatRows=1)
            tbl.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, -1), font_regular),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("FONTNAME", (0, 0), (-1, 0), font_bold),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f9fafb")),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )

            tw, th = tbl.wrap(table_width, 0)
            if y - th < bottom_margin:
                y = new_page_y()
            tbl.drawOn(c, margin_left, y - th)
            y = y - th - 14
        else:
            c.setFont(font_regular, 9)
            c.setFillColor(colors.HexColor("#6b7280"))
            c.drawString(margin_left, y, labels["no_prices"])
            y -= 12

    # ===== Drawings =====
    if show_drawings:
        # Pirmą brėžinį rodome header'io dešinėje (per b.preview); čia rodome tik likusius (iki 2 vnt.)
        hero_in_header = bool(brez)
        drawings = brez[1:3] if hero_in_header else brez[:3]

        if hero_in_header and not drawings:
            # nėra papildomų brėžinių – atskiro bloko nerodom
            pass
        else:
            draw_section_title(labels["section_drawings"])

            if not drawings:
                c.setFont(font_regular, 9)
                c.setFillColor(colors.HexColor("#6b7280"))
                c.drawString(margin_left, y, labels["no_drawings"])
                y -= 12
            else:
                available = width - margin_left - margin_right
                gap = 6 * mm
                thumb_w = (available - gap * 2) / 3
                thumb_h = thumb_w * 0.75
                label_h = 5 * mm

                needed_h = thumb_h + label_h + 6
                if y - needed_h < bottom_margin:
                    y = new_page_y()

                top_y = y
                for i, b in enumerate(drawings):
                    x = margin_left + i * (thumb_w + gap)

                    c.setStrokeColor(colors.HexColor("#e5e7eb"))
                    c.setLineWidth(0.6)
                    c.rect(x, top_y - thumb_h, thumb_w, thumb_h, stroke=1, fill=0)

                    img_path = None
                    try:
                        if getattr(b, "preview", None) and getattr(b.preview, "path", None):
                            p = b.preview.path
                            if p and os.path.exists(p):
                                img_path = p
                    except Exception:
                        img_path = None

                    if img_path:
                        try:
                            c.drawImage(
                                ImageReader(img_path),
                                x + 1,
                                top_y - thumb_h + 1,
                                width=thumb_w - 2,
                                height=thumb_h - 2,
                                preserveAspectRatio=True,
                                anchor="c",
                                mask="auto",
                            )
                        except Exception:
                            c.setFont(font_bold, 10)
                            c.setFillColor(colors.HexColor("#6b7280"))
                            c.drawCentredString(x + thumb_w / 2, top_y - thumb_h / 2, "N/A")
                    else:
                        ext = (getattr(b, "ext", "") or "").lower()
                        label = "3D" if ext in {"stp", "step"} else "N/A"
                        c.setFont(font_bold, 12)
                        c.setFillColor(colors.HexColor("#6b7280"))
                        c.drawCentredString(x + thumb_w / 2, top_y - thumb_h / 2, label)

                    c.setFont(font_regular, 7.5)
                    c.setFillColor(colors.HexColor("#111827"))
                    name = (getattr(b, "pavadinimas", "") or "").strip() or getattr(b, "filename", "")
                    if len(name) > 36:
                        name = name[:33] + "..."
                    c.drawCentredString(x + thumb_w / 2, top_y - thumb_h - 4, name)

                y = top_y - needed_h - 6

    # ===== Notes =====
    combined_notes = []
    if poz_pastabos:
        combined_notes.append(poz_pastabos)
    if notes:
        combined_notes.append(notes)

    if combined_notes:
        draw_section_title(labels["section_notes"])
        c.setFont(font_regular, 9)
        c.setFillColor(colors.HexColor("#111827"))
        y = _draw_wrapped_text(
            c=c,
            text="\n\n".join(combined_notes),
            x=margin_left,
            y=y,
            max_width=width - margin_left - margin_right,
            font_name=font_regular,
            font_size=9,
            page_height=height,
            bottom_margin=bottom_margin,
        )
        y -= 6

    # ===== Footer =====
    c.setFont(font_regular, 8)
    c.setFillColor(colors.HexColor("#6b7280"))
    c.drawRightString(width - margin_right, 15 * mm, datetime.now().strftime("%Y-%m-%d %H:%M"))

    c.save()

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf, content_type="application/pdf")
    filename = f"pasiulymas_{pozicija.poz_kodas or pozicija.pk}.pdf"
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response
