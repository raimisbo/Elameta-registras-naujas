# pozicijos/models.py
from __future__ import annotations

import os
from decimal import Decimal

from django.db import models
from simple_history.models import HistoricalRecords


class Pozicija(models.Model):
    MASKAVIMO_TIPAS_CHOICES = [
        ("nera", "Nėra"),
        ("yra", "Yra"),
    ]
    PAKAVIMO_TIPAS_CHOICES = [
        ("palaidas", "Palaidas"),
        ("standartinis", "Standartinis"),
        ("geras", "Geras"),
        ("individualus", "Individualus"),
    ]

    PAPILDOMOS_PASLAUGOS_CHOICES = [
        ("ne", "Nėra"),
        ("taip", "Yra"),
    ]

    # Pagrindiniai
    klientas = models.CharField("Klientas", max_length=255, blank=True, default="")
    projektas = models.CharField("Projektas", max_length=255, blank=True, default="")

    poz_kodas = models.CharField("Pozicijos kodas", max_length=100, blank=True, default="")
    poz_pavad = models.CharField("Pozicijos pavadinimas", max_length=255, blank=True, default="")

    # Medžiaga / detalė
    metalas = models.CharField("Metalas", max_length=120, blank=True, default="")
    plotas = models.CharField("Plotas", max_length=120, blank=True, default="")
    svoris = models.CharField("Svoris", max_length=120, blank=True, default="")

    # Matmenys (mm) - NAUJA
    x_mm = models.DecimalField("X (mm)", max_digits=10, decimal_places=2, null=True, blank=True)
    y_mm = models.DecimalField("Y (mm)", max_digits=10, decimal_places=2, null=True, blank=True)
    z_mm = models.DecimalField("Z (mm)", max_digits=10, decimal_places=2, null=True, blank=True)

    # Kabinimas
    kabinimo_budas = models.CharField("Kabinimo būdas", max_length=120, blank=True, default="")
    kabinimas_reme = models.CharField("Kabinimas rėme", max_length=120, blank=True, default="")
    detaliu_kiekis_reme = models.CharField("Detalių kiekis rėme", max_length=120, blank=True, default="")
    faktinis_kiekis_reme = models.CharField("Faktinis kiekis rėme", max_length=120, blank=True, default="")

    # Paruošimas / padengimas
    paruosimas = models.CharField("Paruošimas", max_length=200, blank=True, default="")
    padengimas = models.CharField("Padengimas", max_length=200, blank=True, default="")
    padengimo_standartas = models.CharField("Padengimo standartas", max_length=200, blank=True, default="")
    spalva = models.CharField("Spalva", max_length=120, blank=True, default="")

    # Paslaugos logika: KTL / Miltai / Paruošimas
    paslauga_ktl = models.BooleanField("KTL", default=False)
    paslauga_miltai = models.BooleanField("Miltai", default=False)
    paslauga_paruosimas = models.BooleanField("Paruošimas", default=False)

    miltu_kodas = models.CharField("Miltelių kodas", max_length=100, blank=True, default="")
    miltu_spalva = models.CharField("Miltelių spalva", max_length=120, blank=True, default="")
    miltu_tiekejas = models.CharField("Miltelių tiekėjas", max_length=120, blank=True, default="")
    miltu_blizgumas = models.CharField("Blizgumas", max_length=50, blank=True, default="")
    miltu_kaina = models.DecimalField("Miltelių kaina", max_digits=10, decimal_places=2, null=True, blank=True)

    paslaugu_pastabos = models.TextField("Paslaugų pastabos", blank=True, default="")

    # Maskavimas
    maskavimo_tipas = models.CharField(
        "Maskavimas",
        max_length=10,
        choices=MASKAVIMO_TIPAS_CHOICES,
        default="nera",
        blank=False,
    )
    maskavimas = models.TextField("Maskavimo aprašymas", max_length=200, blank=True, default="")

    # --- Terminai ---
    atlikimo_terminas = models.IntegerField("Atlikimo terminas (d.d.)", null=True, blank=True)
    atlikimo_terminas_data = models.DateField("Atlikimo terminas (data)", null=True, blank=True)

    # Kokybė / testai
    testai_kokybe = models.CharField("Testai / kokybė", max_length=255, blank=True, default="")

    # Pakavimas
    pakavimo_tipas = models.CharField(
        "Pakavimo tipas",
        max_length=20,
        choices=PAKAVIMO_TIPAS_CHOICES,
        blank=True,
        default="",
    )
    pakavimas = models.CharField("Pakavimas", max_length=255, blank=True, default="")
    instrukcija = models.TextField("Instrukcija", blank=True, default="")

    # --- Papildomos paslaugos ---
    papildomos_paslaugos = models.CharField(
        "Papildomos paslaugos",
        max_length=4,
        choices=PAPILDOMOS_PASLAUGOS_CHOICES,
        default="ne",
        blank=False,
    )
    papildomos_paslaugos_aprasymas = models.TextField(
        "Papildomų paslaugų aprašymas",
        blank=True,
        default="",
    )

    # Kaina (sinchronizuojama iš kainų eilučių)
    kaina_eur = models.DecimalField("Kaina (EUR)", max_digits=12, decimal_places=2, null=True, blank=True)

    pastabos = models.TextField("Pastabos", blank=True, default="")

    created = models.DateTimeField("Sukurta", auto_now_add=True)
    updated = models.DateTimeField("Atnaujinta", auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.poz_kodas or self.id} — {self.poz_pavad}".strip()

    # ---- Matmenys XYZ (suvestinė) ----
    @staticmethod
    def _fmt_dim(val: Decimal | None) -> str:
        """
        Gražinam reikšmę kaip tekstą:
        - None -> "—"
        - 12.00 -> "12"
        - 12.50 -> "12.5"
        """
        if val is None:
            return "—"
        s = format(val, "f")
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s or "0"

    @property
    def matmenys_xyz(self) -> str:
        """
        Suvestinis formatas: X×Y×Z mm
        - Jei visi trys tušti -> "—"
        - Jei dalis trūksta -> trūkstamos rodomos kaip "—" (pvz. 120×80×— mm)
        """
        if self.x_mm is None and self.y_mm is None and self.z_mm is None:
            return "—"
        x = self._fmt_dim(self.x_mm)
        y = self._fmt_dim(self.y_mm)
        z = self._fmt_dim(self.z_mm)
        return f"{x}×{y}×{z} mm"

    # ---- Kainos API (naudojama views) ----
    def aktualios_kainos(self):
        qs = self.kainos_eilutes.all()
        field_names = {f.name for f in qs.model._meta.get_fields()}
        order_fields = []
        if "prioritetas" in field_names:
            order_fields.append("prioritetas")
        if "created" in field_names:
            order_fields.append("-created")
        if order_fields:
            qs = qs.order_by(*order_fields)
        return qs

    def get_kaina_for_qty(self, qty):
        try:
            q = int(qty) if qty is not None else None
        except (TypeError, ValueError):
            q = None

        lines = list(self.aktualios_kainos())

        if q is not None:
            for l in lines:
                if getattr(l, "yra_fiksuota", False) and getattr(l, "fiksuotas_kiekis", None) == q:
                    return getattr(l, "kaina", None)

        if q is not None:
            for l in lines:
                kn = getattr(l, "kiekis_nuo", None)
                kk = getattr(l, "kiekis_iki", None)
                if kn is None and kk is None:
                    continue
                if kn is None:
                    ok = q <= kk
                elif kk is None:
                    ok = q >= kn
                else:
                    ok = (kn <= q <= kk)
                if ok:
                    return getattr(l, "kaina", None)

        for l in lines:
            k = getattr(l, "kaina", None)
            if k is not None:
                return k
        return None


class PozicijosBrezinys(models.Model):
    pozicija = models.ForeignKey(Pozicija, on_delete=models.CASCADE, related_name="breziniai")
    pavadinimas = models.CharField("Pavadinimas", max_length=255, blank=True)
    failas = models.FileField("Brėžinys", upload_to="pozicijos/breziniai/%Y/%m/")
    uploaded = models.DateTimeField(auto_now_add=True)

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

    @property
    def filename(self) -> str:
        name = getattr(self.failas, "name", "") or ""
        return os.path.basename(name)

    @property
    def ext(self) -> str:
        name = getattr(self.failas, "name", "") or ""
        return os.path.splitext(name)[1].lower().lstrip(".")

    @property
    def is_step(self) -> bool:
        return self.ext in ("stp", "step")

    @property
    def thumb_url(self) -> str:
        if self.preview:
            try:
                return self.preview.url
            except Exception:
                return ""
        return ""


class KainosEilute(models.Model):
    pozicija = models.ForeignKey(Pozicija, on_delete=models.CASCADE, related_name="kainos_eilutes")

    kaina = models.DecimalField("Kaina", max_digits=12, decimal_places=2, null=True, blank=True)
    matas = models.CharField("Matas", max_length=50, blank=True, default="")

    yra_fiksuota = models.BooleanField("Fiksuota", default=False)
    fiksuotas_kiekis = models.IntegerField("Fiksuotas kiekis", null=True, blank=True)

    kiekis_nuo = models.IntegerField("Kiekis nuo", null=True, blank=True)
    kiekis_iki = models.IntegerField("Kiekis iki", null=True, blank=True)

    galioja_nuo = models.DateField("Galioja nuo", null=True, blank=True)
    galioja_iki = models.DateField("Galioja iki", null=True, blank=True)

    busena = models.CharField("Būsena", max_length=50, blank=True, default="")
    prioritetas = models.IntegerField("Prioritetas", default=0)
    pastaba = models.CharField("Pastaba", max_length=255, blank=True, default="")

    created = models.DateTimeField("Sukurta", auto_now_add=True)
    updated = models.DateTimeField("Atnaujinta", auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.pozicija_id} | {self.kaina} {self.matas}".strip()
