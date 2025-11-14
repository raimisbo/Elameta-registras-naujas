# pozicijos/models.py
from django.db import models
from django.conf import settings
from django.core.files.base import ContentFile

import os
import io
import mimetypes
import shutil
import subprocess
from pathlib import Path

# Vaizdų apdorojimas
from PIL import Image

# Pasirenkama: PDF -> PNG (jei įdiegtas pymupdf)
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None


class Pozicija(models.Model):
    # pagrindiniai
    klientas = models.CharField("Klientas", max_length=255, null=True, blank=True)
    projektas = models.CharField("Projektas", max_length=255, null=True, blank=True)
    poz_kodas = models.CharField("Kodas", max_length=100)
    poz_pavad = models.CharField("Pavadinimas", max_length=255)

    # iš tavo sena columns.py
    metalas = models.CharField("Metalas", max_length=120, null=True, blank=True)
    plotas = models.DecimalField("Plotas", max_digits=10, decimal_places=2, null=True, blank=True)
    svoris = models.DecimalField("Svoris", max_digits=10, decimal_places=3, null=True, blank=True)

    kabinimo_budas = models.CharField("Kabinimo būdas", max_length=120, null=True, blank=True)
    kabinimas_reme = models.CharField("Kabinimas rėme", max_length=120, null=True, blank=True)
    detaliu_kiekis_reme = models.IntegerField("Detalių kiekis rėme", null=True, blank=True)
    faktinis_kiekis_reme = models.IntegerField("Faktinis kiekis rėme", null=True, blank=True)

    paruosimas = models.CharField("Paruošimas", max_length=200, null=True, blank=True)
    padengimas = models.CharField("Padengimas", max_length=200, null=True, blank=True)
    padengimo_standartas = models.CharField("Padengimo standartas", max_length=200, null=True, blank=True)
    spalva = models.CharField("Spalva", max_length=120, null=True, blank=True)

    maskavimas = models.CharField("Maskavimas", max_length=200, null=True, blank=True)
    atlikimo_terminas = models.DateField("Atlikimo terminas", null=True, blank=True)

    testai_kokybe = models.CharField("Testai / kokybė", max_length=255, null=True, blank=True)
    pakavimas = models.CharField("Pakavimas", max_length=255, null=True, blank=True)
    instrukcija = models.TextField("Instrukcija", null=True, blank=True)
    pakavimo_dienos_norma = models.CharField("Pakavimo dienos norma", max_length=120, null=True, blank=True)
    pak_po_ktl = models.CharField("Pakavimas po KTL", max_length=255, null=True, blank=True)
    pak_po_milt = models.CharField("Pakavimas po miltelinio", max_length=255, null=True, blank=True)

    kaina_eur = models.DecimalField("Dabartinė kaina (EUR)", max_digits=12, decimal_places=2, null=True, blank=True)

    pastabos = models.TextField("Pastabos", null=True, blank=True)

    created = models.DateTimeField("Sukurta", auto_now_add=True, null=True, blank=True)
    updated = models.DateTimeField("Atnaujinta", auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ["-created", "-id"]
        verbose_name = "Pozicija"
        verbose_name_plural = "Pozicijos"

    def __str__(self):
        return f"{self.poz_kodas} – {self.poz_pavad or ''}"

    @property
    def brez_count(self):
        return self.breziniai.count()

    @property
    def dok_count(self):
        return ""


class PozicijosKaina(models.Model):
    MATAS_CHOICES = [
        ("vnt.", "vnt."),
        ("kg", "kg"),
        ("m2", "m2"),
    ]
    BUSENA_CHOICES = [
        ("aktuali", "Aktuali"),
        ("sena", "Sena"),
        ("pasiulymas", "Pasiūlymas"),
    ]

    pozicija = models.ForeignKey(
        Pozicija,
        on_delete=models.CASCADE,
        related_name="kainos",
        verbose_name="Pozicija",
    )
    suma = models.DecimalField("Suma", max_digits=12, decimal_places=2)
    busena = models.CharField("Būsena", max_length=20, choices=BUSENA_CHOICES, default="aktuali")
    yra_fiksuota = models.BooleanField("Yra fiksuota", default=False)
    kiekis_nuo = models.IntegerField("Kiekis nuo", null=True, blank=True)
    kiekis_iki = models.IntegerField("Kiekis iki", null=True, blank=True)
    fiksuotas_kiekis = models.IntegerField("Fiksuotas kiekis", null=True, blank=True, default=None)
    kainos_matas = models.CharField("Matas", max_length=10, choices=MATAS_CHOICES, default="vnt.")
    created = models.DateTimeField("Įrašyta", auto_now_add=True, null=True, blank=True)

    class Meta:
        ordering = ["-created"]
        verbose_name = "Pozicijos kaina"
        verbose_name_plural = "Pozicijų kainos"

    def __str__(self):
        return f"{self.pozicija} – {self.suma} {self.kainos_matas}"


class PozicijosBrezinys(models.Model):
    pozicija = models.ForeignKey(
        Pozicija,
        on_delete=models.CASCADE,
        related_name="breziniai",
    )
    pavadinimas = models.CharField("Pavadinimas", max_length=255, blank=True)
    failas = models.FileField("Brėžinys", upload_to="pozicijos/breziniai/%Y/%m/")
    # NAUJA: miniatiūra ir PDF info
    preview = models.ImageField("Peržiūra (PNG)", upload_to="pozicijos/breziniai/%Y/%m/previews/", blank=True, null=True)
    mime = models.CharField(max_length=80, blank=True)
    pages = models.PositiveIntegerField(default=1)

    uploaded = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded"]

    def __str__(self):
        return self.pavadinimas or self.failas.name

    @property
    def filename(self):
        return os.path.basename(self.failas.name or "")

    @property
    def is_image(self):
        name = (self.failas.name or "").lower()
        return name.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"))

    def save(self, *args, **kwargs):
        # nustatom MIME (jei trūksta)
        if not self.mime and self.failas:
            self.mime = mimetypes.guess_type(self.failas.name)[0] or ""
        super().save(*args, **kwargs)
        # sugeneruojame preview, jei dar nėra
        if self.failas and not self.preview:
            self._ensure_preview()

    def _ensure_preview(self, max_size=(600, 600)):
        """
        Sugeneruoja PNG peržiūrą:
          - jei failas vaizdas -> sumažintas PNG
          - jei PDF -> pirmo puslapio PNG (PyMuPDF, o jei jo nėra – bandome per poppler 'pdftoppm', jei įdiegtas)
        Jei nepavyksta, peržiūros neliečia (šablonas rodys fallback).
        """
        if not self.failas:
            return

        try:
            storage = self.failas.storage
            src_path = storage.path(self.failas.name)
        except Exception:
            return

        # 1) Vaizdas -> PNG thumbnail
        if (self.mime or "").startswith("image/") or self.is_image:
            try:
                with Image.open(src_path) as im:
                    im.thumbnail(max_size)
                    buf = io.BytesIO()
                    im.save(buf, format="PNG")
                    buf.seek(0)
                    name = f"{Path(self.filename).stem}_prev.png"
                    self.preview.save(name, ContentFile(buf.read()), save=True)
            except Exception:
                # nepavyko – ignoruojam
                pass
            return

        # 2) PDF -> PNG
        if (self.mime or "").endswith("pdf") or str(self.failas.name).lower().endswith(".pdf"):
            # 2a) PyMuPDF (jei yra)
            if fitz:
                try:
                    doc = fitz.open(src_path)
                    self.pages = max(1, doc.page_count or 1)
                    page = doc.load_page(0)
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # ~2x
                    out = pix.tobytes(output="png")
                    name = f"{Path(self.filename).stem}_prev.png"
                    self.preview.save(name, ContentFile(out), save=True)
                    doc.close()
                    return
                except Exception:
                    pass

            # 2b) Poppler 'pdftoppm' (jei yra sistemoje, pvz. per Homebrew)
            if shutil.which("pdftoppm"):
                try:
                    outdir = Path(settings.MEDIA_ROOT) / "tmp_previews"
                    outdir.mkdir(parents=True, exist_ok=True)
                    stem = Path(self.filename).stem
                    tmp_png = outdir / f"{stem}-1.png"
                    # pirmas puslapis į PNG
                    subprocess.run(
                        ["pdftoppm", "-png", "-f", "1", "-singlefile", src_path, str(outdir / stem)],
                        check=True
                    )
                    with open(tmp_png, "rb") as fh:
                        name = f"{stem}_prev.png"
                        self.preview.save(name, ContentFile(fh.read()), save=True)
                    # išvalom laikiną failą
                    try:
                        tmp_png.unlink(missing_ok=True)  # Python 3.8+ turi missing_ok
                    except TypeError:
                        if tmp_png.exists():
                            tmp_png.unlink()
                    return
                except Exception:
                    pass
            # jei nei fitz, nei poppler – paliekam be preview

    def delete(self, using=None, keep_parents=False):
        """
        Ištrinam ir DB įrašą, ir patį failą bei preview iš media/.
        """
        storage = self.failas.storage
        name = self.failas.name
        preview_name = self.preview.name if self.preview else None

        super().delete(using=using, keep_parents=keep_parents)

        if name and storage.exists(name):
            storage.delete(name)
        if preview_name and storage.exists(preview_name):
            storage.delete(preview_name)
