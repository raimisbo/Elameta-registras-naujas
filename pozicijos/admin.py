# pozicijos/admin.py
from django.contrib import admin

from .models import Pozicija, PozicijosBrezinys, KainosEilute
from .services.previews import regenerate_missing_preview


@admin.register(Pozicija)
class PozicijaAdmin(admin.ModelAdmin):
    list_display = ("poz_kodas", "poz_pavad", "klientas", "projektas", "brez_count", "created")
    search_fields = ("poz_kodas", "poz_pavad", "klientas", "projektas")
    list_filter = ("klientas", "projektas")
    ordering = ("-created",)

    @admin.display(description="Brėžiniai")
    def brez_count(self, obj: Pozicija) -> int:
        # jei related_name kitas – čia pataisyti į tavo realų (dažniausiai "breziniai")
        return obj.breziniai.count()


@admin.action(description="Regeneruoti peržiūras (PNG) pasirinktiems")
def regenerate_previews_action(modeladmin, request, queryset):
    ok, total = 0, 0
    for b in queryset:
        total += 1
        res = regenerate_missing_preview(b)
        # suderinam su abiem variantais: res gali būti bool arba objektas su .ok
        ok_flag = getattr(res, "ok", bool(res))
        if ok_flag:
            ok += 1
    modeladmin.message_user(request, f"Sėkmingai: {ok}/{total}")


@admin.register(PozicijosBrezinys)
class PozicijosBrezinysAdmin(admin.ModelAdmin):
    list_display = ("id", "pozicija", "pavadinimas", "failo_pav", "uploaded")
    search_fields = ("pavadinimas", "failas__icontains")
    list_filter = ("uploaded",)
    date_hierarchy = "uploaded"
    actions = [regenerate_previews_action]

    @admin.display(description="Failas")
    def failo_pav(self, obj: PozicijosBrezinys):
        return getattr(obj.failas, "name", "")


@admin.register(KainosEilute)
class KainosEiluteAdmin(admin.ModelAdmin):
    list_display = (
        "pozicija",
        "kaina",
        "matas",
        "yra_fiksuota",
        "fiksuotas_kiekis",
        "kiekis_nuo",
        "kiekis_iki",
        "busena",
        "galioja_nuo",
        "galioja_iki",
        "created",
    )
    list_filter = ("matas", "yra_fiksuota", "busena")
    search_fields = ("pozicija__poz_kodas", "pozicija__poz_pavad", "pastaba")
    ordering = ("-created",)
