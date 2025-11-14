# pozicijos/proposal_views.py
from pathlib import Path
from typing import Optional, Iterable
from decimal import Decimal
from datetime import date, datetime

from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.utils import timezone

from .models import Pozicija
try:
    from .schemas.columns import COLUMNS  # dict'ų sąrašas
except Exception:
    COLUMNS = []

# ReportLab
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader


def _find_first_existing(paths: Iterable[Path]) -> Optional[Path]:
    for p in paths:
        if p and p.exists():
            return p
    return None

def _find_logo_path() -> Optional[Path]:
    base = Path(settings.BASE_DIR)
    return _find_first_existing([
        base / "media" / "logo.png",
        base / "static" / "img" / "logo.png",
    ])

def _find_font_path() -> Optional[Path]:
    base = Path(settings.BASE_DIR)
    return _find_first_existing([
        base / "media" / "fonts" / "NotoSans-Regular.ttf",
        base / "static" / "fonts" / "NotoSans-Regular.ttf",
        base / "media" / "fonts" / "DejaVuSans.ttf",
        base / "static" / "fonts" / "DejaVuSans.ttf",
    ])

def _draw_wrapped_text(c: canvas.Canvas, text: str, x: float, y: float,
                       max_chars: int, line_h: float, bottom_margin: float,
                       font: str, size: int) -> float:
    c.setFont(font, size)
    text = text or ""
    for paragraph in (text.splitlines() or [""]):
        t = paragraph.rstrip("\n")
        if t == "":
            y -= line_h
            if y < bottom_margin:
                c.showPage(); y = A4[1] - 18 * mm; c.setFont(font, size)
            continue
        while t:
            line = t[:max_chars]
            t = t[max_chars:]
            c.drawString(x, y, line)
            y -= line_h
            if y < bottom_margin:
                c.showPage(); y = A4[1] - 18 * mm; c.setFont(font, size)
    return y

def _fmt(val) -> str:
    if val is None or val == "":
        return ""
    if isinstance(val, Decimal):
        return f"{val.normalize()}"
    if isinstance(val, (date, datetime)):
        return val.strftime("%Y-%m-%d")
    return str(val)


FALLBACK_FIELDS = [
    ("Klientas", "klientas"),
    ("Projektas", "projektas"),
    ("Kodas", "poz_kodas"),
    ("Pavadinimas", "poz_pavad"),
    ("Metalas", "metalas"),
    ("Plotas", "plotas"),
    ("Svoris", "svoris"),
    ("Kabinimo būdas", "kabinimo_budas"),
    ("Kabinimas rėme", "kabinimas_reme"),
    ("Detalių kiekis rėme", "detaliu_kiekis_reme"),
    ("Faktinis kiekis rėme", "faktinis_kiekis_reme"),
    ("Paruošimas", "paruosimas"),
    ("Padengimas", "padengimas"),
    ("Standartas", "padengimo_standartas"),
    ("Spalva", "spalva"),
    ("Maskavimas", "maskavimas"),
    ("Atlikimo terminas", "atlikimo_terminas"),
    ("Pakavimas", "pakavimas"),
    ("Instrukcija", "instrukcija"),
    ("Pakavimo d. norma", "pakavimo_dienos_norma"),
    ("Pak. po KTL", "pak_po_ktl"),
    ("Pak. po milt", "pak_po_milt"),
    ("Kaina", "kaina_eur"),
    ("Pastabos", "pastabos"),
]


def proposal_prepare(request, pk: int):
    pozicija = get_object_or_404(Pozicija, pk=pk)

    show_prices = request.GET.get("show_prices") == "1"
    show_drawings = request.GET.get("show_drawings") == "1"
    notes = (request.GET.get("notes") or "").strip()

    kainos = list(pozicija.kainos.all() if show_prices else [])
    brez = list(pozicija.breziniai.all() if show_drawings else [])

    context = {
        "pozicija": pozicija,
        "columns": COLUMNS,
        "kainos": kainos,
        "brez": brez,
        "show_prices": show_prices,
        "show_drawings": show_drawings,
        "notes": notes,
        "now": timezone.now(),
        "logo_url": None,
    }
    return render(request, "pozicijos/proposal_prepare.html", context)


def proposal_pdf(request, pk: int):
    pozicija = get_object_or_404(Pozicija, pk=pk)

    show_prices = request.GET.get("show_prices") == "1"
    show_drawings = request.GET.get("show_drawings") == "1"
    notes = (request.GET.get("notes") or "").strip()

    kainos = list(pozicija.kainos.all() if show_prices else [])
    brez = list(pozicija.breziniai.all() if show_drawings else [])

    if request.GET.get("preview") == "1":
        context = {
            "pozicija": pozicija,
            "columns": COLUMNS,
            "kainos": kainos,
            "brez": brez,
            "show_prices": show_prices,
            "show_drawings": show_drawings,
            "notes": notes,
            "now": timezone.now(),
            "logo_url": None,
        }
        return render(request, "pozicijos/proposal_pdf.html", context)

    resp = HttpResponse(content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="pasiulymas-{pozicija.pk}.pdf"'

    c = canvas.Canvas(resp, pagesize=A4)
    width, height = A4

    LM, RM, TM, BM = 18 * mm, 18 * mm, 18 * mm, 18 * mm
    x = LM
    y = height - TM

    base_font = "Helvetica"
    font_path = _find_font_path()
    if font_path:
        try:
            pdfmetrics.registerFont(TTFont("LTText", str(font_path)))
            base_font = "LTText"
        except Exception:
            base_font = "Helvetica"

    logo_path = _find_logo_path()
    if logo_path:
        try:
            img = ImageReader(str(logo_path))
            logo_w = 38 * mm
            c.drawImage(img, x, y - logo_w * 0.35, width=logo_w, height=logo_w * 0.35,
                        preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    c.setFont(base_font, 16)
    c.drawRightString(width - RM, y, "Pasiūlymas")
    y -= 8 * mm
    c.setFont(base_font, 11)
    c.drawRightString(width - RM, y, f"Pozicija: {getattr(pozicija, 'poz_kodas', pozicija.pk)}")
    y -= 5 * mm
    c.drawRightString(width - RM, y, f"{getattr(pozicija, 'poz_pavad', '')}")
    y -= 7 * mm

    c.setStrokeColorRGB(0.88, 0.91, 0.94)
    c.line(LM, y, width - RM, y)
    y -= 6 * mm

    c.setFont(base_font, 12)
    c.drawString(x, y, "Pagrindinė informacija")
    y -= 6 * mm
    c.setFont(base_font, 10)
    row_h = 6 * mm

    def draw_row(label: str, value, y0: float) -> float:
        val = _fmt(value)
        if not val:
            return y0
        if y0 < BM + 25 * mm:
            c.showPage(); y1 = height - TM; c.setFont(base_font, 10)
        else:
            y1 = y0
        c.drawString(x, y1, f"{label}: {val}"[:170])
        return y1 - row_h

    if COLUMNS:
        for col in COLUMNS:
            if (col or {}).get("type") == "virtual":
                continue
            key = (col or {}).get("key")
            if not key:
                continue
            label = (col or {}).get("label", key)
            value = getattr(pozicija, key, "")
            y = draw_row(label, value, y)
    else:
        for label, key in FALLBACK_FIELDS:
            y = draw_row(label, getattr(pozicija, key, ""), y)

    if show_prices:
        if y < BM + 35 * mm:
            c.showPage(); y = height - TM; c.setFont(base_font, 10)

        c.setFont(base_font, 12)
        c.drawString(x, y, "Kainos")
        y -= 6 * mm
        c.setFont(base_font, 10)

        headers = ["Suma", "Matas", "Būsena", "Kiekis nuo", "Kiekis iki", "Fiks. kiekis", "Įrašyta"]
        col_w = (width - LM - RM) / len(headers)
        for i, hname in enumerate(headers):
            c.drawString(x + i * col_w, y, hname)
        y -= 5 * mm
        c.line(LM, y, width - RM, y)
        y -= 3 * mm

        for k in kainos:
            if y < BM + 20 * mm:
                c.showPage(); y = height - TM; c.setFont(base_font, 10)
            vals = [
                _fmt(getattr(k, "suma", "")),
                _fmt(getattr(k, "kainos_matas", "")),
                getattr(k, "get_busena_display", lambda: "")(),
                _fmt(getattr(k, "kiekis_nuo", "") or "—"),
                _fmt(getattr(k, "kiekis_iki", "") or "—"),
                _fmt(getattr(k, "fiksuotas_kiekis", "") or "—"),
                _fmt(getattr(k, "created", None)),
            ]
            for i, v in enumerate(vals):
                c.drawString(x + i * col_w, y, str(v))
            y -= 5 * mm
        y -= 4 * mm

    if show_drawings:
        if y < BM + 45 * mm:
            c.showPage(); y = height - TM; c.setFont(base_font, 10)

        c.setFont(base_font, 12)
        c.drawString(x, y, "Brėžinių miniatiūros")
        y -= 6 * mm
        c.setFont(base_font, 10)

        thumb_h = 28 * mm
        thumb_w = 42 * mm
        gap = 6 * mm
        col_count = int((width - LM - RM + gap) // (thumb_w + gap)) or 1

        col_i = 0
        line_bottom = y

        for b in brez:
            if y < BM + thumb_h + 15 * mm:
                c.showPage()
                y = height - TM
                c.setFont(base_font, 10)
                c.setFont(base_font, 12); c.drawString(x, y, "Brėžinių miniatiūros")
                y -= 6 * mm
                c.setFont(base_font, 10)
                col_i = 0
                line_bottom = y

            bx = x + col_i * (thumb_w + gap)
            by = y - thumb_h

            img_path = None
            if getattr(b, "preview", None) and getattr(b.preview, "path", None):
                img_path = b.preview.path
            else:
                name = str(getattr(b, "failas", ""))
                if name.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")) and getattr(b, "failas", None):
                    img_path = b.failas.path

            if img_path:
                try:
                    c.drawImage(ImageReader(img_path), bx, by, width=thumb_w, height=thumb_h,
                                preserveAspectRatio=True, anchor='sw', mask='auto')
                except Exception:
                    pass

            label = (getattr(b, "pavadinimas", None) or Path(b.failas.name).name)[:46]
            c.drawString(bx, by - 4 * mm, label)

            col_i += 1
            if col_i >= col_count:
                col_i = 0
                y = by - 10 * mm
                line_bottom = y

        if col_i != 0:
            y = line_bottom

    if notes:
        if y < BM + 25 * mm:
            c.showPage(); y = height - TM; c.setFont(base_font, 10)
        c.setFont(base_font, 12)
        c.drawString(x, y, "Pastabos / sąlygos")
        y -= 6 * mm
        y = _draw_wrapped_text(
            c=c,
            text=notes,
            x=x,
            y=y,
            max_chars=110,
            line_h=5 * mm,
            bottom_margin=BM + 15 * mm,
            font=base_font,
            size=10,
        )

    c.showPage()
    c.save()
    return resp
