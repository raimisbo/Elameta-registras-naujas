# pozicijos/proposal_views.py
import os
from io import BytesIO

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .models import Pozicija


def proposal_prepare(request, pk):
    """
    Tarpinis puslapis: parodome checkbox'us ir tekstus prieš PDF.
    """
    pozicija = get_object_or_404(Pozicija, pk=pk)

    context = {
        "pozicija": pozicija,
        # default'ai – ką rodyti pirmą kartą
        "show_prices": True,
        "show_drawings": True,
        "custom_terms": "• Kaina galioja 14 kalendorinių dienų nuo pasiūlymo datos.\n• Gamybos terminas – pagal suderintus techninius reikalavimus.",
        "custom_price_note": "",
    }
    return render(request, "pozicijos/proposal_prepare.html", context)


def proposal_pdf(request, pk):
    """
    Generuoja PDF pagal tai, ką pažymėjome formoje.
    GET atveju – rodo 'viską'.
    POST atveju – rodo tik tai, kas pažymėta.
    """
    pozicija = get_object_or_404(Pozicija, pk=pk)
    breziniai = pozicija.breziniai.all()
    kainos = pozicija.kainos.all()

    if request.method == "POST":
        show_prices = request.POST.get("show_prices") == "on"
        show_drawings = request.POST.get("show_drawings") == "on"
        custom_terms = request.POST.get("custom_terms", "").strip()
        custom_price_note = request.POST.get("custom_price_note", "").strip()
    else:
        # jei kažkas atėjo per GET į /pdf/ – rodom viską
        show_prices = True
        show_drawings = True
        custom_terms = ""
        custom_price_note = ""

    # ====== PDF START ======
    # fontas LT
    font_name = "Helvetica"
    font_path = os.path.join(settings.MEDIA_ROOT, "fonts", "DejaVuSans.ttf")
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont("DejaVuSans", font_path))
        font_name = "DejaVuSans"

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleLT", parent=styles["Heading1"], fontName=font_name))
    styles.add(ParagraphStyle(name="NormalLT", parent=styles["Normal"], fontName=font_name, fontSize=10, leading=12))
    styles.add(ParagraphStyle(name="SmallLT", parent=styles["Normal"], fontName=font_name, fontSize=9, leading=11))
    styles.add(ParagraphStyle(name="SectionLT", parent=styles["Heading2"], fontName=font_name, fontSize=11, leading=13, spaceBefore=8, spaceAfter=3))
    styles.add(ParagraphStyle(name="MutedLT", parent=styles["Normal"], fontName=font_name, fontSize=8, textColor=colors.grey))

    story = []

    # HEADER
    logo_path = os.path.join(settings.MEDIA_ROOT, "logo.png")
    if os.path.exists(logo_path):
        header_left = Image(logo_path, width=35 * mm, height=15 * mm)
    else:
        header_left = Paragraph(" ", styles["NormalLT"])

    header_right = Paragraph(
        "<b>UAB „Tavo įmonė“</b><br/>Įm. k. 123456789<br/>PVM LT123456789<br/>info@imone.lt<br/>+370 000 00000",
        styles["SmallLT"],
    )

    header_tbl = Table([[header_left, header_right]], colWidths=[70 * mm, 90 * mm])
    header_tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.3, colors.lightgrey),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(header_tbl)
    story.append(Spacer(1, 6))

    # TITLAS
    title_txt = f"Pasiūlymas: {pozicija.poz_kodas or ''} – {pozicija.poz_pavad or ''}"
    story.append(Paragraph(title_txt, styles["TitleLT"]))
    story.append(Spacer(1, 2))

    meta_html = (
        f"Klientas: {pozicija.klientas or '—'}<br/>"
        f"Projektas: {pozicija.projektas or '—'}<br/>"
        f"Data: {(pozicija.created.strftime('%Y-%m-%d') if pozicija.created else '—')}"
    )
    story.append(Paragraph(meta_html, styles["NormalLT"]))
    story.append(Spacer(1, 6))

    # 1. POZICIJA
    story.append(Paragraph("1. Pozicijos duomenys", styles["SectionLT"]))

    poz_data = [
        ["Kodas", pozicija.poz_kodas or "—"],
        ["Pavadinimas", pozicija.poz_pavad or "—"],
        ["Metalas", getattr(pozicija, "metalas", None) or "—"],
        ["Padengimas", getattr(pozicija, "padengimas", None) or "—"],
        ["Spalva", getattr(pozicija, "spalva", None) or "—"],
    ]
    if pozicija.pastabos:
        poz_data.append(["Pastabos", pozicija.pastabos])

    poz_tbl = Table(poz_data, colWidths=[38 * mm, 122 * mm])
    poz_tbl.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.25, colors.grey),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ]
        )
    )
    story.append(poz_tbl)
    story.append(Spacer(1, 6))

    # 2. KAINOS (tik jei pažymėta)
    if show_prices:
        story.append(Paragraph("2. Kainos", styles["SectionLT"]))
        if kainos:
            rows = [["Data", "Suma", "Matas", "Būsena", "Kiekis"]]
            for k in kainos:
                if k.kiekis_nuo or k.kiekis_iki:
                    kiekis = f"{k.kiekis_nuo or ''}–{k.kiekis_iki or ''}"
                else:
                    kiekis = "—"
                rows.append(
                    [
                        k.created.strftime("%Y-%m-%d") if k.created else "—",
                        str(k.suma),
                        k.kainos_matas or "",
                        k.busena or "",
                        kiekis,
                    ]
                )
            k_tbl = Table(rows, colWidths=[23 * mm, 23 * mm, 20 * mm, 32 * mm, 40 * mm])
            k_tbl.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, -1), font_name),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ]
                )
            )
            story.append(k_tbl)
        else:
            story.append(Paragraph("Kainų nėra.", styles["NormalLT"]))
        # jei buvo įrašyta teksto prie kainų
        if custom_price_note:
            story.append(Spacer(1, 3))
            story.append(Paragraph(custom_price_note, styles["SmallLT"]))
        story.append(Spacer(1, 6))

    # 3. SĄLYGOS – iš formos
    story.append(Paragraph("Sąlygos", styles["SectionLT"]))
    if custom_terms:
        # paverčiam \n į <br/>
        for line in custom_terms.splitlines():
            if line.strip():
                story.append(Paragraph(line, styles["SmallLT"]))
    else:
        story.append(Paragraph("Kaina galioja 14 kalendorinių dienų nuo pasiūlymo datos.", styles["SmallLT"]))
    story.append(Spacer(1, 8))

    # 4. PARAŠAI
    story.append(Paragraph("Patvirtinimas", styles["SectionLT"]))
    sign_tbl = Table(
        [
            ["Pasiūlymą parengė:", "Pasiūlymą patvirtino:"],
            ["_____________________", "_____________________"],
            ["Vardas, pavardė, data", "Vardas, pavardė, data"],
        ],
        colWidths=[80 * mm, 80 * mm],
    )
    sign_tbl.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.append(sign_tbl)

    # 5. BRĖŽINIAI/KITAS – jei pažymėta
    if show_drawings and breziniai:
        story.append(PageBreak())
        story.append(Paragraph("Priedas: brėžiniai ir dokumentai", styles["SectionLT"]))
        image_exts = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp")
        for b in breziniai:
            fname = b.failas.name if b.failas else ""
            ext = os.path.splitext(fname)[1].lower()
            story.append(Paragraph(b.pavadinimas or fname, styles["SmallLT"]))
            if ext in image_exts and b.failas and hasattr(b.failas, "path") and os.path.exists(b.failas.path):
                try:
                    img = Image(b.failas.path, width=150 * mm, height=90 * mm)
                    story.append(img)
                except Exception:
                    story.append(Paragraph(f"({fname} nepavyko atvaizduoti)", styles["MutedLT"]))
            else:
                story.append(Paragraph(f"Failas: {fname}", styles["MutedLT"]))
            story.append(Spacer(1, 6))

    # footer
    story.append(Spacer(1, 10))
    story.append(Paragraph("Pasiūlymas sugeneruotas automatiškai iš pozicijos duomenų.", styles["MutedLT"]))

    doc.build(story)

    pdf = buffer.getvalue()
    buffer.close()

    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="pasiulymas_{pozicija.poz_kodas}.pdf"'
    return resp
