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
        "section_prices": "Kainos (pasirinktos eilutės)",
        "section_drawings": "Brėžinių miniatiūros",
        "section_notes": "Pastabos / sąlygos",
        "no_data": "Nėra duomenų.",
        "no_prices": "Pasirinktų (ar aktyvių) kainų eilučių šiai pozicijai nėra.",
        "no_drawings": "Brėžinių nėra.",
        "col_price": "Kaina €",
        "col_unit": "Matas",
        "col_qty_from": "Kiekis nuo",
        "col_qty_to": "Kiekis iki",
        "col_valid_from": "Galioja nuo",
        "col_valid_to": "Galioja iki",
        "preview_hint": "HTML peržiūra – galutinis PDF gali šiek tiek skirtis.",
    },
    "en": {
        "offer_title": "OFFER",
        "date_label": "Date",
        "section_main": "Main information",
        "section_prices": "Prices (selected lines)",
        "section_drawings": "Drawing thumbnails",
        "section_notes": "Notes / terms",
        "no_data": "No data.",
        "no_prices": "There are no selected (or active) price lines for this position.",
        "no_drawings": "No drawings.",
        "col_price": "Price €",
        "col_unit": "Unit",
        "col_qty_from": "Qty from",
        "col_qty_to": "Qty to",
        "col_valid_from": "Valid from",
        "col_valid_to": "Valid until",
        "preview_hint": "HTML preview – final PDF may differ slightly.",
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
        "paslauga_ktl": "KTL",
        "paslauga_miltai": "Miltai",
        "paslauga_paruosimas": "Paruošimas (paslauga)",
        "miltu_kodas": "Miltelių kodas",
        "miltu_spalva": "Miltelių spalva",
        "miltu_tiekejas": "Miltelių tiekėjas",
        "miltu_blizgumas": "Blizgumas",
        "miltu_kaina": "Miltelių kaina",
        "paslaugu_pastabos": "Paslaugų pastabos",
        "maskavimo_tipas": "Maskavimas",
        "maskavimas": "Maskavimo aprašymas",
        "atlikimo_terminas": "Atlikimo terminas (darbo dienos)",
        "testai_kokybe": "Testai / kokybė",
        "pakavimo_tipas": "Pakavimo tipas",
        "pakavimas": "Pakavimas",
        "instrukcija": "Instrukcija",
        "papildomos_paslaugos": "Papildomos paslaugos",
        "papildomos_paslaugos_aprasymas": "Papildomų paslaugų aprašymas",
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
        "paslauga_ktl": "KTL",
        "paslauga_miltai": "Powder",
        "paslauga_paruosimas": "Pre-treatment (service)",
        "miltu_kodas": "Powder code",
        "miltu_spalva": "Powder colour",
        "miltu_tiekejas": "Powder supplier",
        "miltu_blizgumas": "Gloss",
        "miltu_kaina": "Powder price",
        "paslaugu_pastabos": "Service notes",
        "maskavimo_tipas": "Masking",
        "maskavimas": "Masking description",
        "atlikimo_terminas": "Lead time (working days)",
        "testai_kokybe": "Tests / quality",
        "pakavimo_tipas": "Packaging type",
        "pakavimas": "Packaging",
        "instrukcija": "Instruction",
        "papildomos_paslaugos": "Additional services",
        "papildomos_paslaugos_aprasymas": "Additional services description",
        "kaina_eur": "Price €",
        "pastabos": "Notes",
    },
}


def _register_fonts() -> tuple[str, str]:
    """Pabandome paimti šriftus iš MEDIA_ROOT/fonts, kitaip – Helvetica."""
    regular = "Helvetica"
    bold = "Helvetica-Bold"

    fonts_dir = os.path.join(settings.MEDIA_ROOT, "fonts")
    if not os.path.isdir(fonts_dir):
        return regular, bold

    font_files = [f for f in os.listdir(fonts_dir) if f.lower().endswith((".ttf", ".otf"))]
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


def _get_selected_kaina_ids(request) -> list[int]:
    """
    Skaitom pasirinktų kainų ID iš querystring:
      ?kaina_id=12&kaina_id=15
    """
    raw = request.GET.getlist("kaina_id")
    ids: list[int] = []
    for r in raw:
        try:
            ids.append(int(r))
        except Exception:
            continue
    # unikalumas, bet išlaikom eiliškumą
    seen = set()
    out: list[int] = []
    for i in ids:
        if i not in seen:
            out.append(i)
            seen.add(i)
    return out


def _get_kainos_for_pdf(pozicija: Pozicija, selected_ids: list[int] | None = None):
    """
    Naudojam tik 'aktuali' KainosEilute eilutes.
    Jei selected_ids pateikta – imam tik jas (tik tos pozicijos ribose).
    """
    qs = pozicija.kainos_eilutes.filter(busena="aktuali")

    if selected_ids:
        qs = qs.filter(pk__in=selected_ids)

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
    font_size: float,
    page_height: float,
    bottom_margin: float,
    leading: float | None = None,
) -> float:
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
    """UI puslapis – pasirinkimai + kainų eilučių checkbox'ai."""
    pozicija = get_object_or_404(Pozicija, pk=pk)
    lang = _get_lang(request)

    show_prices = bool(request.GET.get("show_prices"))
    show_drawings = bool(request.GET.get("show_drawings"))
    notes = request.GET.get("notes", "")

    # Kainų pasirinkimas
    selected_ids = _get_selected_kaina_ids(request)
    available_kainos = list(_get_kainos_for_pdf(pozicija, selected_ids=None))  # visos aktualios

    # Jei vartotojas įjungė "rodyti kainas", bet nieko nepasirinko -> default: visos aktualios
    if show_prices and not selected_ids:
        selected_ids = [k.id for k in available_kainos]

    params: list[tuple[str, str]] = []
    if show_prices:
        params.append(("show_prices", "1"))
    if show_drawings:
        params.append(("show_drawings", "1"))
    if notes:
        params.append(("notes", notes))
    if lang:
        params.append(("lang", lang))
    # į qs įdedam pasirinktus kainų ID (kad preview puslapyje PDF mygtukas turėtų tą patį rinkinį)
    for kid in selected_ids:
        params.append(("kaina_id", str(kid)))

    qs = urlencode(params)

    context = {
        "pozicija": pozicija,
        "show_prices": show_prices,
        "show_drawings": show_drawings,
        "notes": notes,
        "qs": qs,
        "lang": lang,
        "available_kainos": available_kainos,
        "selected_kaina_ids": set(selected_ids),
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

    selected_ids = _get_selected_kaina_ids(request)

    # jei show_prices=1 ir nieko nenurodyta -> default: visos aktualios
    if show_prices and not selected_ids:
        selected_ids = [k.id for k in _get_kainos_for_pdf(pozicija, selected_ids=None)]

    params: list[tuple[str, str]] = []
    if show_prices:
        params.append(("show_prices", "1"))
    if show_drawings:
        params.append(("show_drawings", "1"))
    if notes:
        params.append(("notes", notes))
    if lang:
        params.append(("lang", lang))
    for kid in selected_ids:
        params.append(("kaina_id", str(kid)))
    qs = urlencode(params)

    field_rows = _build_field_rows(pozicija, lang)
    kainos = list(_get_kainos_for_pdf(pozicija, selected_ids if show_prices else []))
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

    # Title
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

    # ===== Prices =====
    if show_prices:
        draw_section_title(labels["section_prices"])

        if kainos:
            table_width = width - margin_left - margin_right

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
                    "—" if not k.galioja_nuo else k.galioja_nuo.strftime("%Y-%m-%d"),
                    "—" if not k.galioja_iki else k.galioja_iki.strftime("%Y-%m-%d"),
                ]
                rows.append(row)

            col_widths = [
                26 * mm,
                18 * mm,
                18 * mm,
                18 * mm,
                28 * mm,
                28 * mm,
            ]

            tbl = Table(rows, colWidths=col_widths)
            tbl.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, 0), font_bold),
                        ("FONTNAME", (0, 1), (-1, -1), font_regular),
                        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f9fafb")),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 3),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                        ("TOPPADDING", (0, 0), (-1, -1), 2),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
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
        draw_section_title(labels["section_drawings"])

        drawings = brez[:3]
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
    combined_notes: list[str] = []
    if poz_pastabos:
        combined_notes.append(poz_pastabos)
    if notes:
        combined_notes.append(notes)

    if combined_notes:
        draw_section_title(labels["section_notes"])
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
