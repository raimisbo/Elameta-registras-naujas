# detaliu_registras/admin.py
from django.contrib import admin
from .models import (
    Klientas,
    Projektas,
    Detale,
    DetaleSpecifikacija,
    PavirsiuDangos,
    Uzklausa,
    Kaina,
    Kainodara,
    KainosPartijai,
)

# --- Bendri utility ---
class ReadonlyTimestampsMixin:
    readonly_fields = ("created", "updated")


# --- Pagrindiniai katalogai ---
@admin.register(Klientas)
class KlientasAdmin(ReadonlyTimestampsMixin, admin.ModelAdmin):
    list_display = ("id", "vardas", "created", "updated")
    search_fields = ("vardas",)


@admin.register(Projektas)
class ProjektasAdmin(ReadonlyTimestampsMixin, admin.ModelAdmin):
    list_display = ("id", "pavadinimas", "klientas", "uzklausos_data", "pasiulymo_data", "created", "updated")
    list_filter = ("uzklausos_data", "pasiulymo_data", "klientas")
    search_fields = ("pavadinimas", "klientas__vardas")


# Inline’ai detalei (nebūtina, bet patogu)
class DetaleSpecifikacijaInline(admin.StackedInline):
    model = DetaleSpecifikacija
    extra = 0


class PavirsiuDangosInline(admin.StackedInline):
    model = PavirsiuDangos
    extra = 0


@admin.register(Detale)
class DetaleAdmin(ReadonlyTimestampsMixin, admin.ModelAdmin):
    list_display = ("id", "pavadinimas", "brezinio_nr", "projektas", "created", "updated")
    list_filter = ("projektas",)
    search_fields = ("pavadinimas", "brezinio_nr", "projektas__pavadinimas")
    inlines = [DetaleSpecifikacijaInline, PavirsiuDangosInline]


@admin.register(Uzklausa)
class UzklausaAdmin(ReadonlyTimestampsMixin, admin.ModelAdmin):
    list_display = ("id", "klientas", "projektas", "detale", "data", "created", "updated")
    list_filter = ("klientas", "projektas", "data")
    search_fields = ("id", "klientas__vardas", "projektas__pavadinimas", "detale__pavadinimas", "detale__brezinio_nr")


# --- Kainos ---
def make_selected_active(modeladmin, request, queryset):
    # žymim kaip aktualias; senas uždarysit per savo servisą/operaciją, šis action tik greitam „rankiniam“ pažymėjimui
    queryset.update(yra_aktuali=True, galioja_iki=None)
make_selected_active.short_description = "Pažymėti kaip AKTUALIAS"


def make_selected_inactive(modeladmin, request, queryset):
    from django.utils.timezone import localdate
    queryset.update(yra_aktuali=False, galioja_iki=localdate())
make_selected_inactive.short_description = "Pažymėti kaip SENAS"


@admin.register(Kaina)
class KainaAdmin(ReadonlyTimestampsMixin, admin.ModelAdmin):
    list_display = (
        "id", "uzklausa", "detale",
        "suma", "valiuta",
        "yra_aktuali", "galioja_nuo", "galioja_iki",
        "pakeite", "created", "updated",
    )
    # ⬇️ čia buvo 'busena' – pakeista į 'yra_aktuali' ir kiti realūs laukai
    list_filter = ("yra_aktuali", "valiuta", "galioja_nuo", "uzklausa", "detale")
    search_fields = ("uzklausa__id", "detale__pavadinimas", "detale__brezinio_nr")
    date_hierarchy = "galioja_nuo"
    actions = [make_selected_active, make_selected_inactive]


# --- Kainodara (jei naudoji) ---
class KainosPartijaiInline(admin.TabularInline):
    model = KainosPartijai
    extra = 1


@admin.register(Kainodara)
class KainodaraAdmin(ReadonlyTimestampsMixin, admin.ModelAdmin):
    list_display = ("id", "uzklausa", "pavadinimas", "created", "updated")
    list_filter = ("uzklausa",)
    inlines = [KainosPartijaiInline]


@admin.register(KainosPartijai)
class KainosPartijaiAdmin(ReadonlyTimestampsMixin, admin.ModelAdmin):
    list_display = ("id", "kainodara", "kiekis_nuo", "kiekis_iki", "suma", "valiuta", "created", "updated")
    list_filter = ("kainodara", "valiuta")
    search_fields = ("kainodara__pavadinimas", "kainodara__uzklausa__id")
