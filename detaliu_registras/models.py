from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.auth import get_user_model

User = get_user_model()


# ====================
# SENI MODELLIAI (palikti kaip buvo)
# ====================

class Klientas(models.Model):
    vardas = models.CharField(max_length=255)
    el_pastas = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.vardas


class Projektas(models.Model):
    klientas = models.ForeignKey(Klientas, on_delete=models.CASCADE, related_name="projektai")
    pavadinimas = models.CharField(max_length=255)
    aprasymas = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.pavadinimas


class Detale(models.Model):
    projektas = models.ForeignKey(Projektas, on_delete=models.CASCADE, related_name="detales")
    pavadinimas = models.CharField(max_length=255)
    brezinio_nr = models.CharField(max_length=255, blank=True, null=True)
    kiekis = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.pavadinimas} ({self.brezinio_nr})"


class Uzklausa(models.Model):
    klientas = models.ForeignKey(Klientas, on_delete=models.CASCADE, related_name="uzklausos")
    projektas = models.ForeignKey(Projektas, on_delete=models.CASCADE, related_name="uzklausos")
    detale = models.ForeignKey(Detale, on_delete=models.CASCADE, related_name="uzklausos")
    data = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Užklausa {self.id} ({self.klientas})"


class Kaina(models.Model):
    uzklausa = models.ForeignKey(
        Uzklausa,
        on_delete=models.CASCADE,
        related_name="kainos",
        null=True, blank=True
    )
    suma = models.DecimalField(max_digits=12, decimal_places=2)
    valiuta = models.CharField(max_length=10, default="EUR")
    busena = models.CharField(
        max_length=10,
        choices=[("aktuali", "Aktuali"), ("sena", "Sena")],
        default="aktuali"
    )

    def __str__(self):
        return f"{self.suma} {self.valiuta} ({self.busena})"


# ====================
# NAUJI MODELLIAI (pagal screenshot'us, 9 blokai)
# ====================

class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        abstract = True


# 1) PROJEKTO DUOMENYS
class UzklausosProjektoDuomenys(TimeStamped):
    uzklausa = models.OneToOneField(
        "Uzklausa", on_delete=models.CASCADE, related_name="projekto_duomenys"
    )

    uzklausos_nr = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    uzklausos_data = models.DateField(blank=True, null=True)
    pasiulymo_data = models.DateField(blank=True, null=True)
    projekto_pradzia_metai = models.PositiveIntegerField(blank=True, null=True)
    projekto_pabaiga_metai = models.PositiveIntegerField(blank=True, null=True)

    kaina_vnt = models.DecimalField(
        max_digits=12, decimal_places=4, blank=True, null=True,
        validators=[MinValueValidator(0)]
    )
    kaina_galioja_iki = models.DateField(blank=True, null=True)

    apmokejimo_salygos = models.CharField(max_length=128, blank=True, null=True)
    transportavimo_salygos = models.CharField(max_length=64, blank=True, null=True)

    atsakingas = models.ForeignKey(
        User, on_delete=models.SET_NULL, blank=True, null=True, related_name="uzklausos_atsakingas"
    )

    def __str__(self):
        return f"Projekto duomenys #{self.uzklausos_nr or self.pk}"


# 2) DETALĖS IDENTIFIKACIJA
class DetalesIdentifikacija(TimeStamped):
    detale = models.OneToOneField(
        "Detale", on_delete=models.CASCADE, related_name="identifikacija"
    )
    pavadinimas = models.CharField(max_length=128, blank=True, null=True)
    brezinio_numeris = models.CharField(max_length=128, blank=True, null=True, db_index=True)
    paruosimas = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.pavadinimas or self.brezinio_numeris or f"Detale #{self.detale_id}"


# 3) PAVIRŠIAI / DANGOS
class PavirsiaiDangos(TimeStamped):
    detale = models.OneToOneField(
        "Detale", on_delete=models.CASCADE, related_name="pavirsiu_dangos"
    )

    ktl_ec_name = models.CharField("Padengimas KTL / e-coating", max_length=128, blank=True, null=True)
    miltelinis_name = models.CharField("Padengimas milteliniu būdu", max_length=128, blank=True, null=True)

    storis_ktl_mkm = models.DecimalField(
        "Padengimas, storis μm KTL", max_digits=8, decimal_places=2, blank=True, null=True,
        validators=[MinValueValidator(0)]
    )
    storis_ktl_plus_miltai_mkm = models.DecimalField(
        "Padengimo storis: KTL + miltai, μm", max_digits=8, decimal_places=2, blank=True, null=True,
        validators=[MinValueValidator(0)]
    )

    padengimo_standartas = models.CharField(max_length=128, blank=True, null=True)
    testai = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Paviršiai detalei #{self.detale_id}"


# 4) MATMENYS & MEDŽIAGA
class DetalesSpecifikacija(TimeStamped):
    detale = models.OneToOneField(
        "Detale", on_delete=models.CASCADE, related_name="specifikacija"
    )

    aukstis_x_cm = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True,
                                       validators=[MinValueValidator(0)])
    plotis_y_cm = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True,
                                      validators=[MinValueValidator(0)])
    ilgis_z_cm = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True,
                                     validators=[MinValueValidator(0)])
    metalo_storis_mm = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True,
                                           validators=[MinValueValidator(0)])

    svoris_kg = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True,
                                    validators=[MinValueValidator(0)])
    plotas_m2 = models.DecimalField(max_digits=12, decimal_places=6, blank=True, null=True,
                                    validators=[MinValueValidator(0)])

    metalas = models.CharField(max_length=256, blank=True, null=True)

    def __str__(self):
        return f"Specifikacija detalei #{self.detale_id}"


# 5) KIEKIAI & TERMINAI
class KiekiaiTerminai(TimeStamped):
    uzklausa = models.OneToOneField(
        "Uzklausa", on_delete=models.CASCADE, related_name="kiekiai_terminai"
    )
    metinis_kiekis_vnt = models.PositiveIntegerField(blank=True, null=True)
    partijos_dydis_vnt = models.PositiveIntegerField(blank=True, null=True)
    minimalus_kiekis_vnt = models.PositiveIntegerField(blank=True, null=True)
    terminai_darbo_dienomis = models.PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        return f"Kiekiai/terminai #{self.uzklausa_id}"


# 6) KABINIMAS / RĖMAI
class KabinimasRemai(TimeStamped):
    KABINIMO_BUDAS_CHOICES = [
        ("girliandos", "Girliandos"),
        ("kablys", "Kablys"),
        ("kita", "Kita"),
    ]

    uzklausa = models.OneToOneField(
        "Uzklausa", on_delete=models.CASCADE, related_name="kabinimas_remai"
    )
    kabinimo_budas = models.CharField(max_length=64, choices=KABINIMO_BUDAS_CHOICES,
                                      blank=True, null=True)

    kiekis_reme_planuotas = models.PositiveIntegerField(blank=True, null=True)
    kiekis_reme_faktinis = models.PositiveIntegerField(blank=True, null=True)

    kabliukai = models.CharField(max_length=128, blank=True, null=True)
    spyruoke = models.CharField(max_length=128, blank=True, null=True)

    kontaktines_vietos_ktl = models.TextField(blank=True, null=True)
    kontaktines_vietos_miltelinis = models.TextField(blank=True, null=True)

    nepilnas_remas = models.BooleanField(blank=True, null=True)

    sukabinimo_dienos_norma_vnt = models.PositiveIntegerField(blank=True, null=True)
    pakavimo_dienos_norma_vnt = models.PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        return f"Kabinimas/rėmai #{self.uzklausa_id}"


# 7) PAKAVIMAS
class Pakavimas(TimeStamped):
    uzklausa = models.OneToOneField(
        "Uzklausa", on_delete=models.CASCADE, related_name="pakavimas"
    )

    tara = models.CharField(max_length=128, blank=True, null=True)
    pakavimo_instrukcija = models.TextField(blank=True, null=True)

    pakavimas_po_ktl = models.TextField(blank=True, null=True)
    pakavimas_po_miltelinio = models.TextField(blank=True, null=True)

    papildomos_paslaugos = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Pakavimas #{self.uzklausa_id}"


# 8) KAINODARA + KAINOS PARTIJAI
class Kainodara(TimeStamped):
    uzklausa = models.OneToOneField(
        "Uzklausa", on_delete=models.CASCADE, related_name="kainodara"
    )

    kabliuku_kaina_vnt = models.DecimalField(
        max_digits=12, decimal_places=4, blank=True, null=True, validators=[MinValueValidator(0)]
    )
    pakavimo_medziagu_kaina_vnt = models.DecimalField(
        max_digits=12, decimal_places=4, blank=True, null=True, validators=[MinValueValidator(0)]
    )
    milteliniu_dazu_kaina_kg = models.DecimalField(
        max_digits=12, decimal_places=4, blank=True, null=True, validators=[MinValueValidator(0)]
    )
    darbo_kaina = models.DecimalField(
        max_digits=12, decimal_places=4, blank=True, null=True, validators=[MinValueValidator(0)]
    )
    viso_savikaina = models.DecimalField(
        max_digits=12, decimal_places=4, blank=True, null=True, validators=[MinValueValidator(0)]
    )
    fiksuota_kaina_vnt = models.DecimalField(
        max_digits=12, decimal_places=4, blank=True, null=True, validators=[MinValueValidator(0)]
    )
    remo_kaina = models.DecimalField(
        max_digits=12, decimal_places=4, blank=True, null=True, validators=[MinValueValidator(0)]
    )
    faktine_kaina = models.DecimalField(
        max_digits=12, decimal_places=4, blank=True, null=True, validators=[MinValueValidator(0)]
    )

    sukabinimas_pagal_fakta = models.PositiveIntegerField(blank=True, null=True)
    valiuta = models.CharField(max_length=8, blank=True, null=True, default="EUR")

    def __str__(self):
        return f"Kainodara #{self.uzklausa_id}"


class KainosPartijai(TimeStamped):
    kainodara = models.ForeignKey(
        Kainodara, on_delete=models.CASCADE, related_name="kainos_partijoms"
    )
    partijos_kiekis_vnt = models.PositiveIntegerField(db_index=True)
    kaina_bendra = models.DecimalField(
        max_digits=14, decimal_places=4, validators=[MinValueValidator(0)]
    )

    class Meta:
        unique_together = [("kainodara", "partijos_kiekis_vnt")]
        indexes = [models.Index(fields=["partijos_kiekis_vnt"])]

    def __str__(self):
        return f"{self.partijos_kiekis_vnt} vnt – {self.kaina_bendra} {self.kainodara.valiuta or ''}"


# 9) PASTABOS
class Pastaba(TimeStamped):
    KATEGORIJOS = [
        ("projektas", "Projektas"),
        ("identifikacija", "Identifikacija"),
        ("paviršiai", "Paviršiai"),
        ("matmenys", "Matmenys/medžiaga"),
        ("kiekiai", "Kiekiai/terminai"),
        ("kabinimas", "Kabinimas/rėmai"),
        ("pakavimas", "Pakavimas"),
        ("kainodara", "Kainodara"),
        ("kita", "Kita"),
    ]

    uzklausa = models.ForeignKey("Uzklausa", on_delete=models.CASCADE, related_name="pastabos")
    kategorija = models.CharField(max_length=32, choices=KATEGORIJOS, blank=True, null=True, db_index=True)
    tekstas = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="pastabos_autoriai")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.kategorija or 'kita'}: {self.tekstas[:40]}"
