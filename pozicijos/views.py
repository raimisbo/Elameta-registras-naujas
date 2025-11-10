# pozicijos/views.py
import os
from io import BytesIO

from django.conf import settings
from django.core.exceptions import FieldError
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image, PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


from .models import Pozicija
from .forms import (
    PozicijaForm,
    PozicijosKainaFormSet,
    PozicijosBrezinysForm,
)
from .schemas.columns import COLUMNS  # tavo columns.py



def _get_visible_cols(request):
    cols_param = request.GET.get("cols")
    if cols_param:
        return [c for c in cols_param.split(",") if c]
    # jei nieko neatsiuntė – imam tuos, kurie pažymėti kaip default
    return [c["key"] for c in COLUMNS if c.get("default")]


def apply_filters(qs, request):
    model_fields = {f.name for f in Pozicija._meta.get_fields()}

    # globali paieška
    g = (request.GET.get("q") or "").strip()
    if g:
        q_obj = Q()
        for col in COLUMNS:
            if not col.get("searchable"):
                continue
            key = col["key"]
            if key not in model_fields:
                continue
            q_obj |= Q(**{f"{key}__icontains": g})
        if q_obj:
            try:
                qs = qs.filter(q_obj)
            except FieldError:
                pass

    # stulpelių filtrai
    for key, value in request.GET.items():
        if not key.startswith("f[") or not key.endswith("]"):
            continue
        col_key = key[2:-1]
        val = value.strip()
        if not val:
            continue

        col = next((c for c in COLUMNS if c["key"] == col_key), None)
        if not col:
            continue
        if col_key not in model_fields:
            continue

        ftype = col.get("filter") or col.get("type") or "text"

        try:
            if ftype in ("text", "choice"):
                qs = qs.filter(**{f"{col_key}__icontains": val})
            elif ftype in ("date",):
                qs = qs.filter(**{col_key: val})
            elif ftype in ("number", "range"):
                if val.startswith(">="):
                    qs = qs.filter(**{f"{col_key}__gte": val[2:].strip()})
                elif val.startswith("<="):
                    qs = qs.filter(**{f"{col_key}__lte": val[2:].strip()})
                elif ".." in val:
                    lo, hi = val.split("..", 1)
                    if lo:
                        qs = qs.filter(**{f"{col_key}__gte": lo})
                    if hi:
                        qs = qs.filter(**{f"{col_key}__lte": hi})
                else:
                    qs = qs.filter(**{col_key: val})
            else:
                qs = qs.filter(**{f"{col_key}__icontains": val})
        except FieldError:
            continue

    return qs


def pozicijos_list(request):
    visible_cols = _get_visible_cols(request)

    qs = Pozicija.objects.all().order_by("-created", "-id")
    qs = apply_filters(qs, request)
    page_size = int(request.GET.get("page_size", 25) or 25)
    items = qs[:page_size]

    return render(
        request,
        "pozicijos/list.html",
        {
            "columns_schema": COLUMNS,
            "visible_cols": visible_cols,
            "items": items,
            "q": request.GET.get("q", ""),
            "f": {},
            "page_size": page_size,
        },
    )


def pozicijos_tbody(request):
    visible_cols = _get_visible_cols(request)
    qs = Pozicija.objects.all().order_by("-created", "-id")
    qs = apply_filters(qs, request)
    page_size = int(request.GET.get("page_size", 25) or 25)
    items = qs[:page_size]

    f_vals = {}
    for key, value in request.GET.items():
      if key.startswith("f[") and key.endswith("]"):
        f_vals[key[2:-1]] = value

    return render(
        request,
        "pozicijos/_tbody.html",
        {
            "items": items,
            "columns_schema": COLUMNS,
            "visible_cols": visible_cols,
            "f": f_vals,
        },
    )


def pozicijos_stats(request):
    qs = Pozicija.objects.all()
    qs = apply_filters(qs, request)

    agg = qs.values("klientas").annotate(cnt=Count("id")).order_by("-cnt")

    labels, values, total = [], [], 0
    for row in agg:
        lbl = row["klientas"] or "—"
        labels.append(lbl)
        values.append(row["cnt"])
        total += row["cnt"]

    return JsonResponse({"labels": labels, "values": values, "total": total})


def pozicija_detail(request, pk):
    pozicija = get_object_or_404(Pozicija, pk=pk)
    kainos = pozicija.kainos.all()
    breziniai = pozicija.breziniai.all()
    brezinys_form = PozicijosBrezinysForm()
    return render(
        request,
        "pozicijos/detail.html",
        {
            "pozicija": pozicija,
            "kainos": kainos,
            "breziniai": breziniai,
            "brezinys_form": brezinys_form,
        },
    )


def pozicija_create(request):
    if request.method == "POST":
        form = PozicijaForm(request.POST)
        if form.is_valid():
            obj = form.save()
            return redirect("pozicijos:detail", pk=obj.pk)
    else:
        form = PozicijaForm()
    return render(request, "pozicijos/form.html", {"form": form})


def pozicija_edit(request, pk):
    obj = get_object_or_404(Pozicija, pk=pk)
    if request.method == "POST":
        form = PozicijaForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            return redirect("pozicijos:detail", pk=obj.pk)
    else:
        form = PozicijaForm(instance=obj)
    return render(request, "pozicijos/form.html", {"form": form, "pozicija": obj})


def pozicijos_kainos_redaguoti(request, pk):
    pozicija = get_object_or_404(Pozicija, pk=pk)

    if request.method == "POST":
        formset = PozicijosKainaFormSet(request.POST, instance=pozicija)
        if formset.is_valid():
            formset.save()
            last = pozicija.kainos.filter(busena="aktuali").order_by("-created").first()
            if last:
                pozicija.kaina_eur = last.suma
                pozicija.save(update_fields=["kaina_eur"])
            return redirect("pozicijos:detail", pk=pozicija.pk)
    else:
        formset = PozicijosKainaFormSet(instance=pozicija)

    return render(
        request,
        "pozicijos/kainos_redaguoti.html",
        {
            "pozicija": pozicija,
            "formset": formset,
        },
    )


def pozicija_brezinys_upload(request, pk):
    pozicija = get_object_or_404(Pozicija, pk=pk)
    if request.method != "POST":
        return HttpResponseForbidden("POST only")

    form = PozicijosBrezinysForm(request.POST, request.FILES)
    if form.is_valid():
        brezinys = form.save(commit=False)
        brezinys.pozicija = pozicija
        brezinys.save()
    return redirect("pozicijos:detail", pk=pozicija.pk)


def pozicija_brezinys_delete(request, pk, brezinys_id):
    pozicija = get_object_or_404(Pozicija, pk=pk)
    brezinys = pozicija.breziniai.filter(pk=brezinys_id).first()
    if not brezinys:
        return redirect("pozicijos:detail", pk=pozicija.pk)
    if request.method == "POST":
        brezinys.delete()
    return redirect("pozicijos:detail", pk=pozicija.pk)


def pozicija_pdf(request, pk):
    pozicija = get_object_or_404(Pozicija, pk=pk)
    breziniai = pozicija.breziniai.all()
    kainos = pozicija.kainos.all()

    # 1) šriftas LT
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

    # ===== HEADER =====
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

    # ===== TITLAS =====
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

    # ===== POZICIJA =====
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

    # ===== KAINOS =====
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
    story.append(Spacer(1, 6))

    # ===== SĄLYGOS =====
    story.append(Paragraph("3. Sąlygos", styles["SectionLT"]))
    story.append(Paragraph("• Kaina galioja 14 kalendorinių dienų nuo pasiūlymo datos, jei nenurodyta kitaip.", styles["SmallLT"]))
    story.append(Paragraph("• Gamybos terminas ir pakavimas – pagal suderintus techninius reikalavimus.", styles["SmallLT"]))
    story.append(Paragraph("• Brėžiniai ir kiti dokumentai – žr. priedą.", styles["SmallLT"]))
    story.append(Spacer(1, 8))

    # ===== PARAŠAI =====
    story.append(Paragraph("4. Patvirtinimas", styles["SectionLT"]))
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
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(sign_tbl)

    # ===== BRĖŽINIAI KITAM PUSLAPY =====
    if breziniai:
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
                # pvz. PDF – tik tekstu
                story.append(Paragraph(f"Failas: {fname}", styles["MutedLT"]))
            story.append(Spacer(1, 6))

    # ===== FOOTER =====
    story.append(Spacer(1, 10))
    story.append(Paragraph("Pasiūlymas sugeneruotas automatiškai iš pozicijos duomenų.", styles["MutedLT"]))

    doc.build(story)

    pdf = buffer.getvalue()
    buffer.close()

    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="pasiulymas_{pozicija.poz_kodas}.pdf"'
    return resp