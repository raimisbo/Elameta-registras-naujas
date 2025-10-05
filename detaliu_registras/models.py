"""
MINIMALUS PAKEITIMAS: Pridėta tik django-simple-history.

KĄ PRIDĖJAU:
- history = HistoricalRecords() Detale modeliui
- Tai trackins VISUS laukus (kabinimas, pakuotė, dokumentai)

KĄ NEPAKEITIAU:
- Jokių struktūros pakeitimų
- Visos lentelės tokios pačios
- Visi laukai tokie patys
- Jokių migracijų duomenims

KAIP VEIKIA:
- Kiekvienas Detale.save() sukuria snapshot'ą istorijoje
- Galite matyti kas, kada ir ką pakeitė
- Admin'e automatiškai atsirado "History" mygtukas
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.contrib.auth import get_user_model
from django.db.models import Q
from simple_history.models import HistoricalRecords  # NAUJAS IMPORT

User = get_user_model()


# --- Bazinė laiko žymų klasė: BŪTINAI abstract ---
class Timestamped(models.Model):
    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        abstract = True


# --- Pagrindiniai katalogai ---
class Klientas(Timestamped):
    vardas = models.CharField(max_length=255)

    def __str__(self):
        return self.vardas


class Projektas(Timestamped):
    klientas = models.ForeignKey(Klientas, on_delete=models.CASCADE, related_name="projektai")
    pavadinimas = models.CharField(max_length=255)
    aprasymas = models.TextField(blank=True, null=True)

    # Laukai, kuriuos naudoja services.UzklausaService._get_or_create_projektas(...)
    uzklausos_data = models.DateField(blank=True, null=True)
    pasiulymo_data = models.DateField(blank=True, null=True)

    # Pasirenkami papildomi (services gali paduoti per projektas_data)
    projekto_pradzia = models.DateField(blank=True, null=True)
    projekto_pabaiga = models.DateField(blank=True, null=True)
    kaina_galioja_iki = models.DateField(blank=True, null=True)
    apmokejimo_salygos = models.TextField(blank=True, null=True)
    transportavimo_salygos = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.pavadinimas


class Detale(Timestamped):
    projektas = models.ForeignKey(Projektas, on_delete=models.CASCADE, related_name="detales",
                                  blank=True, null=True)

    pavadinimas = models.CharField(max_length=255)
    brezinio_nr = models.CharField(max_length=255, blank=True, null=True)

    # nuorodos (naudoja services._normalize_path)
    nuoroda_brezinio = models.CharField(max_length=500, blank=True, null=True)
    nuoroda_pasiulymo = models.CharField(max_length=500, blank=True, null=True)

    # kiekiai
    kiekis_metinis = models.IntegerField(blank=True, null=True)
    kiekis_menesis = models.IntegerField(blank=True, null=True)
    kiekis_partijai = models.IntegerField(blank=True, null=True)
    kiekis_per_val = models.IntegerField(blank=True, null=True)

    # matmenys
    ilgis_mm = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    plotis_mm = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    aukstis_mm = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    skersmuo_mm = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    storis_mm = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    # kabinimas
    kabinimo_budas = models.CharField(max_length=255, blank=True, null=True)
    kabliuku_kiekis = models.IntegerField(blank=True, null=True)
    kabinimo_anga_mm = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    kabinti_per = models.CharField(max_length=255, blank=True, null=True)

    # pakuotė
    pakuotes_tipas = models.CharField(max_length=255, blank=True, null=True)
    vienetai_dezeje = models.IntegerField(blank=True, null=True)
    vienetai_paleje = models.IntegerField(blank=True, null=True)
    pakuotes_pastabos = models.CharField(max_length=255, blank=True, null=True)

    # testai
    testai_druskos_rukas_val = models.IntegerField(blank=True, null=True)
    testas_adhezija = models.CharField(max_length=255, blank=True, null=True)
    testas_storis_mikronai = models.IntegerField(blank=True, null=True)
    testai_kita = models.CharField(max_length=255, blank=True, null=True)

    # dokumentai/pastabos
    ppap_dokumentai = models.CharField(max_length=255, blank=True, null=True)
    priedai_info = models.CharField(max_length=255, blank=True, null=True)

    # ========================================
    # VIENINTELIS NAUJAS LAUKAS - ISTORIJA
    # ========================================
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.pavadinimas} ({self.brezinio_nr or '—'})"


class DetaleSpecifikacija(Timestamped):
    detale = models.OneToOneField(Detale, on_delete=models.CASCADE, related_name="specifikacija")
    metalas = models.CharField(max_length=255, blank=True, null=True)
    plotas_m2 = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)
    svoris_kg = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)
    medziagos_kodas = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Specifikacija: {self.detale}"


class PavirsiuDangos(Timestamped):
    detale = models.OneToOneField(Detale, on_delete=models.CASCADE, related_name="pavirsiu_dangos")
    ktl_ec_name = models.CharField(max_length=255, blank=True, null=True)
    miltelinis_name = models.CharField(max_length=255, blank=True, null=True)
    spalva_ral = models.CharField(max_length=64, blank=True, null=True)
    blizgumas = models.CharField(max_length=128, blank=True, null=True)

    def __str__(self):
        return f"Dangos: {self.detale}"


# --- Užklausa ---
class Uzklausa(Timestamped):
    klientas = models.ForeignKey(Klientas, on_delete=models.SET_NULL, null=True, blank=True, related_name="uzklausos")
    projektas = models.ForeignKey(Projektas, on_delete=models.SET_NULL, null=True, blank=True, related_name="uzklausos")
    detale = models.ForeignKey(Detale, on_delete=models.SET_NULL, null=True, blank=True, related_name="uzklausos")
    pastabos = models.TextField(blank=True, null=True)

    # jei naudoji – paliekam, nors Timestamped turi created
    data = models.DateField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return self.klientas.vardas if self.klientas_id else f"Užklausa #{self.pk}"


# --- Kainos ---
class KainaQuerySet(models.QuerySet):
    def aktualios(self):
        # naujoji schema (yra_aktuali)
        return self.filter(yra_aktuali=True)

    def istorija(self):
        return self.order_by("-galioja_nuo", "-id")


class Kaina(Timestamped):
    """
    Viena „aktuali" kaina vienu metu per (Uzklausa [+ Detale]).
    Pagrindinė schema: yra_aktuali + galioja_nuo/galioja_iki.
    Jei nori kiekių intervalų – naudok kiekis_nuo/iki arba fiksuotas_kiekis.
    """

    MATAS_CHOICES = [
        ("vnt", "Vnt"),
        ("m2", "m²"),
        ("kg", "kg"),
        ("val", "val."),
    ]

    # ryšiai
    uzklausa = models.ForeignKey(Uzklausa, on_delete=models.CASCADE, related_name="kainos")
    detale = models.ForeignKey(Detale, on_delete=models.CASCADE, related_name="kainos",
                               null=True, blank=True)

    # suma / valiuta
    suma = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    valiuta = models.CharField(max_length=10, default="EUR")

    # kiekių logika (pasirinktinai)
    yra_fiksuota = models.BooleanField(default=False)
    kiekis_nuo = models.PositiveIntegerField(null=True, blank=True)
    kiekis_iki = models.PositiveIntegerField(null=True, blank=True)
    fiksuotas_kiekis = models.PositiveIntegerField(null=True, blank=True)
    kainos_matas = models.CharField(max_length=8, choices=MATAS_CHOICES, null=True, blank=True)

    # istorija / aktualumas
    galioja_nuo = models.DateField(default=timezone.now)
    galioja_iki = models.DateField(null=True, blank=True)
    yra_aktuali = models.BooleanField(default=True)

    # audit
    keitimo_priezastis = models.TextField(blank=True)
    pakeite = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="kainu_keitimai")

    objects = KainaQuerySet.as_manager()

    class Meta:
        ordering = ["-galioja_nuo", "-id"]
        indexes = [
            models.Index(fields=["uzklausa", "yra_aktuali"]),
            models.Index(fields=["uzklausa", "galioja_nuo"]),
        ]
        constraints = [
            # Viena „aktuali" kaina per Uzklausa(+Detale) vienu metu
            models.UniqueConstraint(
                fields=["uzklausa", "detale"],
                condition=Q(yra_aktuali=True),
                name="unikali_aktuali_kaina_per_uzklausa_detale",
            ),
        ]

    def __str__(self):
        target = f"Užklausa #{self.uzklausa_id}" + (f" / Detalė #{self.detale_id}" if self.detale_id else "")
        base = f"{self.suma} {self.valiuta}"
        if self.yra_fiksuota and self.fiksuotas_kiekis:
            return f"{target}: {base} ({self.fiksuotas_kiekis} {self.kainos_matas or ''}) [AKTUALI]" if self.yra_aktuali else f"{target}: {base} ({self.fiksuotas_kiekis} {self.kainos_matas or ''})"
        if self.kiekis_nuo or self.kiekis_iki:
            r1 = self.kiekis_nuo or 0
            r2 = self.kiekis_iki or "∞"
            return f"{target}: {base} [{r1}–{r2}] [AKTUALI]" if self.yra_aktuali else f"{target}: {base} [{r1}–{r2}]"
        return f"{target}: {base} ({'AKTUALI' if self.yra_aktuali else 'sena'})"


# --- Kainodaros lentelės (jei naudojamos admin Inline) ---
class Kainodara(Timestamped):
    """Bendresnė kainodaros „antraštė". Jei nenaudoji – gali palikti dėl admin priklausomybių."""
    uzklausa = models.ForeignKey(Uzklausa, on_delete=models.CASCADE, related_name="kainodaros")
    pavadinimas = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Kainodara #{self.pk} ({self.pavadinimas or 'be pavadinimo'})"


class KainosPartijai(Timestamped):
    """Eilutės priklausančios konkrečiai Kainodarai (vienas FK)."""
    kainodara = models.ForeignKey(Kainodara, on_delete=models.CASCADE, related_name="partijos")

    kiekis_nuo = models.PositiveIntegerField(null=True, blank=True)
    kiekis_iki = models.PositiveIntegerField(null=True, blank=True)
    suma = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    valiuta = models.CharField(max_length=10, default="EUR")

    def __str__(self):
        r1 = self.kiekis_nuo or 0
        r2 = self.kiekis_iki or "∞"
        return f"{self.kainodara} [{r1}–{r2}] = {self.suma or '—'} {self.valiuta}"