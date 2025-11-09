# pozicijos/models.py
from django.db import models


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

    # dabartinė kaina (parodoma sąraše / peržiūroje)
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
        # kiek brėžinių yra
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
    """
    Vienas pozicijos brėžinys / failas.
    """
    pozicija = models.ForeignKey(
        Pozicija,
        on_delete=models.CASCADE,
        related_name="breziniai",
    )
    pavadinimas = models.CharField("Pavadinimas", max_length=255, blank=True)
    failas = models.FileField(
        "Brėžinys",
        upload_to="pozicijos/breziniai/%Y/%m/",
    )
    uploaded = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded"]

    def __str__(self):
        return self.pavadinimas or self.failas.name

    @property
    def is_image(self):
        name = (self.failas.name or "").lower()
        return name.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"))
