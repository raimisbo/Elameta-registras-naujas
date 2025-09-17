# detaliu_registras/admin.py
from django.contrib import admin
from .models import (
    Klientas, Projektas, Detale, Uzklausa, Kaina,
    UzklausosProjektoDuomenys, DetalesIdentifikacija, PavirsiaiDangos,
    DetalesSpecifikacija, KiekiaiTerminai, KabinimasRemai, Pakavimas,
    Kainodara, KainosPartijai, Pastaba
)


# ===== Klientas =====
@admin.register(Klientas)
class KlientasAdmin(admin.ModelAdmin):
    list_display = ("id", "vardas", "el_pastas")
    search_fields = ("vardas", "el_pastas")


# ===== Projektas =====
@admin.register(Projektas)
class ProjektasAdmin(admin.ModelAdmin):
    list_display = ("id", "pavadinimas", "klientas")
    list_select_related = ("klientas",)
    search_fields = ("pavadinimas", "klientas__vardas")
    list_filter = ("klientas",)


# ===== Detalės palydovai kaip Inline =====
class DetalesIdentifikacijaInline(admin.StackedInline):
    model = DetalesIdentifikacija
    extra = 0


class DetalesSpecifikacijaInline(admin.StackedInline):
    model = DetalesSpecifikacija
    extra = 0


class PavirsiaiDangosInline(admin.StackedInline):
    model = PavirsiaiDangos
    extra = 0


# ===== Detalė =====
@admin.register(Detale)
class DetaleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "projektas",
        "pavadinimas",
        "brezinio_nr",
        "adm_metalas",
        "adm_svoris",
        "adm_plotas",
    )
    list_select_related = ("projektas",)
    search_fields = ("pavadinimas", "brezinio_nr", "projektas__pavadinimas")
    list_filter = ("projektas",)
    inlines = (DetalesIdentifikacijaInline, DetalesSpecifikacijaInline, PavirsiaiDangosInline)

    # Metodai rodyti laukus iš OneToOne palydovų saugiai
    def _spec(self, obj):
        return getattr(obj, "specifikacija", None)

    @admin.display(description="Metalas")
    def adm_metalas(self, obj):
        spec = self._spec(obj)
        return getattr(spec, "metalas", None) if spec else None

    @admin.display(description="Svoris (kg)")
    def adm_svoris(self, obj):
        spec = self._spec(obj)
        return getattr(spec, "svoris_kg", None) if spec else None

    @admin.display(description="Plotas (m²)")
    def adm_plotas(self, obj):
        spec = self._spec(obj)
        return getattr(spec, "plotas_m2", None) if spec else None


# ===== Užklausos palydovai kaip Inline =====
class UzklausosProjektoDuomenysInline(admin.StackedInline):
    model = UzklausosProjektoDuomenys
    extra = 0


class KiekiaiTerminaiInline(admin.StackedInline):
    model = KiekiaiTerminai
    extra = 0


class KabinimasRemaiInline(admin.StackedInline):
    model = KabinimasRemai
    extra = 0


class PakavimasInline(admin.StackedInline):
    model = Pakavimas
    extra = 0


class PastabaInline(admin.StackedInline):
    model = Pastaba
    extra = 0


# (Kainodara su kainomis partijai — atskirai registruosim žemiau,
#  nes Django neleidžia "nested" inline per Uzklausa -> Kainodara -> KainosPartijai)


# ===== Užklausa =====
@admin.register(Uzklausa)
class UzklausaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "klientas",
        "projektas",
        "detale",
        "data",
        "adm_kaina_vnt",
        "adm_metinis_kiekis",
        "adm_partijos_dydis",
    )
    list_select_related = ("klientas", "projektas", "detale")
    search_fields = ("id", "detale__pavadinimas", "detale__brezinio_nr",
                     "projektas__pavadinimas", "klientas__vardas")
    list_filter = ("klientas", "projektas")
    inlines = (UzklausosProjektoDuomenysInline, KiekiaiTerminaiInline, KabinimasRemaiInline, PakavimasInline, PastabaInline)

    # Patogūs stulpeliai iš palydovų
    @admin.display(description="Kaina vnt.")
    def adm_kaina_vnt(self, obj):
        pd = getattr(obj, "projekto_duomenys", None)
        return getattr(pd, "kaina_vnt", None) if pd else None

    @admin.display(description="Metinis kiekis")
    def adm_metinis_kiekis(self, obj):
        kt = getattr(obj, "kiekiai_terminai", None)
        return getattr(kt, "metinis_kiekis_vnt", None) if kt else None

    @admin.display(description="Partijos dydis")
    def adm_partijos_dydis(self, obj):
        kt = getattr(obj, "kiekiai_terminai", None)
        return getattr(kt, "partijos_dydis_vnt", None) if kt else None


# ===== Kainodara + KainosPartijai (Inline) =====
class KainosPartijaiInline(admin.TabularInline):
    model = KainosPartijai
    extra = 1


@admin.register(Kainodara)
class KainodaraAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "uzklausa",
        "kabliuku_kaina_vnt",
        "pakavimo_medziagu_kaina_vnt",
        "milteliniu_dazu_kaina_kg",
        "darbo_kaina",
        "viso_savikaina",
        "fiksuota_kaina_vnt",
        "remo_kaina",
        "faktine_kaina",
        "valiuta",
    )
    list_select_related = ("uzklausa",)
    search_fields = ("uzklausa__id", "uzklausa__detale__pavadinimas", "uzklausa__detale__brezinio_nr")
    inlines = (KainosPartijaiInline,)


# ===== Kaina (senasis komercinis modelis) =====
@admin.register(Kaina)
class KainaAdmin(admin.ModelAdmin):
    list_display = ("id", "adm_detale", "suma", "valiuta", "busena")
    list_select_related = ("uzklausa", "uzklausa__detale")
    search_fields = ("uzklausa__id", "uzklausa__detale__pavadinimas", "uzklausa__detale__brezinio_nr")
    list_filter = ("busena", "valiuta")

    @admin.display(description="Detalė")
    def adm_detale(self, obj):
        if obj.uzklausa and obj.uzklausa.detale:
            d = obj.uzklausa.detale
            return f"{d.pavadinimas} ({d.brezinio_nr})" if d.brezinio_nr else d.pavadinimas
        return None


# ===== Kiti pagalbiniai (jei reikės atskirai tvarkyti) =====
@admin.register(UzklausosProjektoDuomenys)
class UzklausosProjektoDuomenysAdmin(admin.ModelAdmin):
    list_display = ("id", "uzklausa", "uzklausos_nr", "kaina_vnt", "kaina_galioja_iki", "atsakingas")
    list_select_related = ("uzklausa", "atsakingas")
    search_fields = ("uzklausos_nr", "uzklausa__id")


@admin.register(KiekiaiTerminai)
class KiekiaiTerminaiAdmin(admin.ModelAdmin):
    list_display = ("id", "uzklausa", "metinis_kiekis_vnt", "partijos_dydis_vnt", "minimalus_kiekis_vnt", "terminai_darbo_dienomis")
    list_select_related = ("uzklausa",)
    search_fields = ("uzklausa__id",)


@admin.register(KabinimasRemai)
class KabinimasRemaiAdmin(admin.ModelAdmin):
    list_display = ("id", "uzklausa", "kabinimo_budas", "kiekis_reme_planuotas", "kiekis_reme_faktinis", "nepilnas_remas")
    list_select_related = ("uzklausa",)
    list_filter = ("kabinimo_budas", "nepilnas_remas")


@admin.register(Pakavimas)
class PakavimasAdmin(admin.ModelAdmin):
    list_display = ("id", "uzklausa", "tara")
    list_select_related = ("uzklausa",)


@admin.register(Pastaba)
class PastabaAdmin(admin.ModelAdmin):
    list_display = ("id", "uzklausa", "kategorija", "created_at", "created_by")
    list_select_related = ("uzklausa", "created_by")
    list_filter = ("kategorija",)
    search_fields = ("tekstas",)
