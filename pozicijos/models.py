# pozicijos/models.py
from django.db import models


class Pozicija(models.Model):
    # Pagrindiniai
    klientas = models.CharField("Klientas", max_length=255, blank=True, null=True, db_index=True)
    projektas = models.CharField("Projektas", max_length=255, blank=True, null=True, db_index=True)
    poz_kodas = models.CharField("Kodas", max_length=120, db_index=True)
    poz_pavad = models.CharField("Pavadinimas", max_length=255, db_index=True)

    # Specifikacija
    metalas = models.CharField("Metalas", max_length=120, blank=True, null=True)
    plotas = models.CharField("Plotas", max_length=120, blank=True, null=True)
    svoris = models.CharField("Svoris", max_length=120, blank=True, null=True)

    # Kabinimas
    kabinimo_budas = models.CharField("Kabinimo būdas", max_length=160, blank=True, null=True)
    kabinimas_reme = models.CharField("Kabinimas rėme x-y-z", max_length=160, blank=True, null=True)
    detaliu_kiekis_reme = models.IntegerField("Detalių kiekis rėme", blank=True, null=True)
    faktinis_kiekis_reme = models.IntegerField("Faktinis kiekis rėme", blank=True, null=True)

    # Dažymas / padengimas
    paruosimas = models.CharField("Paruošimas", max_length=200, blank=True, null=True)
    padengimas = models.CharField("Padengimas", max_length=200, blank=True, null=True)
    padengimo_standartas = models.CharField("Padengimo standartas", max_length=200, blank=True, null=True)
    spalva = models.CharField("Spalva", max_length=120, blank=True, null=True)
    maskavimas = models.CharField("Maskavimas", max_length=200, blank=True, null=True)
    atlikimo_terminas = models.DateField("Atlikimo terminas", blank=True, null=True)
    testai_kokybe = models.CharField("Testai/Kokybė", max_length=255, blank=True, null=True)

    # Pakavimas
    pakavimas = models.CharField("Pakavimas", max_length=200, blank=True, null=True)
    instrukcija = models.CharField("Instrukcija", max_length=255, blank=True, null=True)
    pakavimo_dienos_norma = models.IntegerField("Pakavimo dienos norma", blank=True, null=True)
    pak_po_ktl = models.IntegerField("Pak. po KTL", blank=True, null=True)
    pak_po_milt = models.IntegerField("Pak. po milt", blank=True, null=True)

    # Kaina
    kaina_eur = models.DecimalField("Kaina (EUR)", max_digits=12, decimal_places=2, blank=True, null=True)

    # Pastabos
    pastabos = models.TextField("Pastabos", blank=True, null=True)

    # Techniniai – leidžiam tuščius, kad migracija neklausinėtų
    created = models.DateTimeField("Sukurta", auto_now_add=True, null=True, blank=True)
    updated = models.DateTimeField("Atnaujinta", auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["poz_kodas"]),
            models.Index(fields=["poz_pavad"]),
            models.Index(fields=["klientas"]),
            models.Index(fields=["projektas"]),
            models.Index(fields=["metalas"]),
            models.Index(fields=["spalva"]),
            models.Index(fields=["kaina_eur"]),
        ]

    def __str__(self):
        return f"{self.poz_kodas} — {self.poz_pavad}"
