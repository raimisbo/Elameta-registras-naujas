import os
import hashlib

from django.db import models
from django.db.models import Q, Index, UniqueConstraint
from django.core.exceptions import ValidationError
from django.utils import timezone
from simple_history.models import HistoricalRecords

# ======================= Pagrindas: Pozicija =======================


class Pozicija(models.Model):
    # pagrindiniai
    klientas = models.CharField("Klientas", max_length=255, null=True, blank=True)
    projektas = models.CharField("Projektas", max_length=255, null=True, blank=True)
    poz_kodas = models.CharField("Kodas", max_length=100)
    poz_pavad = models.CharField("Pavadinimas", max_length=255)

    # specifikacija
    metalas = models.CharField("Metalas", max_length=120, null=True, blank=True)
    plotas = models.DecimalField("Plotas", max_digits=10, decimal_places=2, null=True, blank=True)
    svoris = models.DecimalField("Svoris", max_digits=10, decimal_places=3, null=True, blank=True)

    # kabinimas
    kabinimo_budas = models.CharField("Kabinimo būdas", max_length=120, null=True, blank=True)
    kabinimas_reme = models.CharField("Kabinimas rėme", max_length=120, null=True, blank=True)
    detaliu_kiekis_reme = models.IntegerField("Detalių kiekis rėme", null=True, blank=True)
    faktinis_kiekis_reme = models.IntegerField("Faktinis kiekis rėme", null=True, blank=True)

    # paviršius / dažymas
    paruosimas = models.CharField("Paruošimas", max_length=200, null=True, blank=True)
    padengimas = models.CharField("Padengimas", max_length=200, null=True, blank=True)
    padengimo_standartas = models.CharField("Padengimo standartas", max_length=200, null=True, blank=True)
    spalva = models.CharField("Spalva", max_length=120, null=True, blank=True)

    # Paslaugos (KTL / Miltai / Paruošimas (Chemetall))
    turi_ktl = models.BooleanField(
        "KTL",
        default=False,
        help_text="Pažymėkite, jei pozicijai taikomas KTL procesas (pvz. BASF CG 570).",
    )
    turi_miltus = models.BooleanField(
        "Miltelinis dažymas",
        default=False,
        help_text="Pažymėkite, jei pozicijai taikomas miltelinis dažymas.",
    )
    turi_paruosima = models.BooleanField(
        "Paruošimas (Chemetall)",
        default=False,
        help_text="Tik paruošimas Chemetall be KTL.",
    )

    miltai_kodas = models.CharField(
        "Miltelių kodas",
        max_length=100,
        blank=True,
    )
    miltai_tiekejas = models.CharField(
        "Miltelių tiekėjas",
        max_length=100,
        blank=True,
    )
    miltai_blizgumas = models.CharField(
        "Blizgumas",
        max_length=50,
        blank=True,
    )
    miltai_kaina = models.DecimalField(
        "Miltelių kaina",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # kiti
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

    # ===== Helperiai kainoms

    def aktualios_kainos(self, matas: str | None = None, as_of=None):
        as_of = (as_of or timezone.now().date())
        qs = self.kainu_eilutes.filter(
            busena="aktuali"
        ).filter(
            Q(galioja_nuo__isnull=True) | Q(galioja_nuo__lte=as_of)
        ).filter(
            Q(galioja_iki__isnull=True) | Q(galioja_iki__gte=as_of)
        )
        if matas:
            qs = qs.filter(matas=matas)
        return qs.order_by("yra_fiksuota", "kiekis_nuo", "fiksuotas_kiekis", "prioritetas", "-created")

    def get_kaina_for_qty(self, qty: int, matas: str = "vnt.", as_of=None):
        as_of = (as_of or timezone.now().date())
        qs = self.kainu_eilutes.filter(
            matas=matas, busena="aktuali"
        ).filter(
            Q(galioja_nuo__isnull=True) | Q(galioja_nuo__lte=as_of)
        ).filter(
            Q(galioja_iki__isnull=True) | Q(galioja_iki__gte=as_of)
        )

        fx = qs.filter(yra_fiksuota=True, fiksuotas_kiekis=qty).order_by("prioritetas", "-created").first()
        if fx:
            return fx

        iv = qs.filter(yra_fiksuota=False) \
               .filter(Q(kiekis_nuo__isnull=True) | Q(kiekis_nuo__lte=qty)) \
               .filter(Q(kiekis_iki__isnull=True) | Q(kiekis_iki__gte=qty)) \
               .order_by("prioritetas", "-created").first()
        return iv


# ======================= Sena suderinamumui =======================


class PozicijosKaina(models.Model):
    MATAS_CHOICES = [
        ("vnt.", "vnt."), ("kg", "kg"), ("m2", "m2"),
    ]
    BUSENA_CHOICES = [
        ("aktuali", "Aktuali"), ("sena", "Sena"), ("pasiulymas", "Pasiūlymas"),
    ]

    pozicija = models.ForeignKey(Pozicija, on_delete=models.CASCADE, related_name="kainos", verbose_name="Pozicija")
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


# ======================= Brėžiniai (su preview helperiais) =======================


class PozicijosBrezinys(models.Model):
    pozicija = models.ForeignKey(Pozicija, on_delete=models.CASCADE, related_name="breziniai")
    pavadinimas = models.CharField("Pavadinimas", max_length=255, blank=True)
    failas = models.FileField("Brėžinys", upload_to="pozicijos/breziniai/%Y/%m/")
    uploaded = models.DateTimeField(auto_now_add=True)

    # 🔹 NAUJAS LAUKAS – sugeneruota PNG miniatiūra
    preview = models.ImageField(
        "Miniatiūra",
        upload_to="pozicijos/breziniai/previews/",
        null=True,
        blank=True,
        help_text="Automatiškai sugeneruota PNG miniatiūra.",
    )

    class Meta:
        ordering = ["-uploaded"]

    def __str__(self):
        return self.pavadinimas or getattr(self.failas, "name", "")

    # ---- Helperiai UI ir preview keliui ----
    @property
    def filename(self) -> str:
        name = getattr(self.failas, "name", "") or ""
        return os.path.basename(name)

    @property
    def ext(self) -> str:
        name = (getattr(self.failas, "name", "") or "").lower()
        _, ext = os.path.splitext(name)
        return (ext or "").lstrip(".")

    def _preview_relpath(self) -> str:
        """Naujas kelias su hash (stabilus pavadinimas)."""
        name = getattr(self.failas, "name", "") or ""
        base, _ = os.path.splitext(os.path.basename(name))
        digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:10]
        return f"pozicijos/breziniai/previews/{base}-{digest}.png"

    def _legacy_preview_relpath(self) -> str:
        """Senas kelias be hash — suderinamumui su anksčiau sugeneruotais PNG."""
        name = getattr(self.failas, "name", "") or ""
        base, _ = os.path.splitext(os.path.basename(name))
        return f"pozicijos/breziniai/previews/{base}.png"

    @property
    def thumb_url(self) -> str | None:
        """
        - jei yra ImageField preview → jo URL
        - jei yra senas PNG disk'e → jo URL
        - jei STP/STEP → statinė 3D ikona iš static
        - kitaip None
        """
        # 1) ImageField preview
        if self.preview:
            try:
                return self.preview.url
            except Exception:
                pass

        # 2) suderinamumas – senieji PNG failai saugykloje
        storage = self.failas.storage
        rel_new = self._preview_relpath()
        rel_old = self._legacy_preview_relpath()
        try:
            if storage.exists(rel_new):
                return storage.url(rel_new)
            if storage.exists(rel_old):
                return storage.url(rel_old)
        except Exception:
            pass

        # 3) fallback – statinė ikona STP/STEP failams
        from django.templatetags.static import static
        ext = (self.ext or "").lower()
        if ext in {"stp", "step"}:
            return static("pozicijos/img/icon-3d.png")

        return None

    def preview_abspath(self) -> str | None:
        """
        Absoliutus kelias iki sugeneruoto PNG preview:
        - pirma bandom ImageField preview.path
        - tada naują hash pavadinimą
        - tada legacy pavadinimą
        """
        # 1) ImageField
        if self.preview:
            try:
                return self.preview.path
            except Exception:
                pass

        # 2) senasis mechanizmas
        storage = self.failas.storage
        rel_new = self._preview_relpath()
        rel_old = self._legacy_preview_relpath()
        for rel in (rel_new, rel_old):
            try:
                if storage.exists(rel):
                    try:
                        return storage.path(rel)
                    except Exception:
                        return None
            except Exception:
                continue
        return None

    def best_image_path_for_pdf(self) -> str | None:
        """
        Parenka geriausią kelią PDF'ui:
        - jei yra PNG preview – grąžina jį
        - kitaip, jei originalas yra PNG/JPG/JPEG – grąžina originalo path
        - kitaip None (PDF/TIFF/CAD nerodom)
        """
        preview = self.preview_abspath()
        if preview:
            return preview

        try:
            orig_path = self.failas.path
        except Exception:
            orig_path = None

        if not orig_path:
            return None

        ext = (self.ext or "").lower()
        if ext in {"png", "jpg", "jpeg"}:
            return orig_path
        return None

    # ---- Valymas trynimo metu ----
    def delete(self, using=None, keep_parents=False):
        """
        Trinant įrašą:
         - pašalina originalų failą
         - pašalina ImageField preview (jei yra)
         - pašalina naują ir seną preview failą (jei buvo sugeneruoti be ImageField)
        """
        storage = self.failas.storage
        orig = getattr(self.failas, "name", None)
        rel_new = self._preview_relpath()
        rel_old = self._legacy_preview_relpath()
        preview_name = self.preview.name if self.preview else None

        super().delete(using=using, keep_parents=keep_parents)

        for path in (orig, rel_new, rel_old, preview_name):
            try:
                if path and storage.exists(path):
                    storage.delete(path)
            except Exception:
                pass


# ======================= Naujas modelis: KainosEilute =======================


class KainosEilute(models.Model):
    MATAS_CHOICES = [("vnt.", "vnt."), ("kg", "kg"), ("m2", "m2")]
    BUSENA_CHOICES = [("aktuali", "Aktuali"), ("sena", "Sena"), ("pasiulymas", "Pasiūlymas")]

    pozicija = models.ForeignKey(Pozicija, on_delete=models.CASCADE, related_name="kainu_eilutes")
    kaina = models.DecimalField("Kaina", max_digits=12, decimal_places=2)
    matas = models.CharField("Matas", max_length=10, choices=MATAS_CHOICES, default="vnt.", db_index=True)

    # kiekio dimensija
    yra_fiksuota = models.BooleanField("Fiksuotas kiekis", default=False, db_index=True)
    fiksuotas_kiekis = models.IntegerField("Fiksuotas kiekis", null=True, blank=True)
    kiekis_nuo = models.IntegerField("Kiekis nuo", null=True, blank=True)
    kiekis_iki = models.IntegerField("Kiekis iki", null=True, blank=True)

    # laikas
    galioja_nuo = models.DateField("Galioja nuo", null=True, blank=True, db_index=True)
    galioja_iki = models.DateField("Galioja iki", null=True, blank=True, db_index=True)

    busena = models.CharField("Būsena", max_length=20, choices=BUSENA_CHOICES, default="aktuali", db_index=True)
    prioritetas = models.IntegerField("Prioritetas", default=100, help_text="Mažesnis laimi, kai yra keli galimi")

    pastaba = models.TextField("Pastaba", null=True, blank=True)

    created = models.DateTimeField(auto_now_add=True, db_index=True)
    updated = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        indexes = [
            Index(fields=["pozicija", "matas", "busena"]),
            Index(fields=["pozicija", "created"]),
            Index(fields=["pozicija", "galioja_nuo", "galioja_iki"]),
        ]
        constraints = [
            UniqueConstraint(
                condition=Q(busena="aktuali", yra_fiksuota=True),
                fields=["pozicija", "matas", "fiksuotas_kiekis"],
                name="uniq_aktuali_fiksuota",
            ),
        ]
        ordering = ["-created"]
        verbose_name = "Kainos eilutė"
        verbose_name_plural = "Kainų eilutės"

    def __str__(self):
        if self.yra_fiksuota:
            scope = f"fx {self.fiksuotas_kiekis} {self.matas}"
        else:
            iki = self.kiekis_iki if self.kiekis_iki is not None else "∞"
            scope = f"[{self.kiekis_nuo}-{iki}] {self.matas}"
        return f"{self.pozicija} – {self.kaina} ({scope})"

    def clean(self):
        if self.yra_fiksuota:
            if self.fiksuotas_kiekis is None:
                raise ValidationError("Fiksuotai kainai privalomas „fiksuotas_kiekis“.")
            if self.kiekis_nuo is not None or self.kiekis_iki is not None:
                raise ValidationError("Fiksuotai kainai „kiekis_nuo/iki“ turi būti tušti.")
        else:
            if self.kiekis_nuo is None and self.kiekis_iki is None:
                raise ValidationError("Intervalinei kainai užpildykite bent „kiekis_nuo“ arba „kiekis_iki“.")
            if self.kiekis_nuo is not None and self.kiekis_iki is not None:
                if self.kiekis_iki < self.kiekis_nuo:
                    raise ValidationError("„kiekis_iki“ negali būti mažesnis už „kiekis_nuo“.")
