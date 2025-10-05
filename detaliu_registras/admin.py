"""
Admin su django-simple-history palaikymu.

KĄ PRIDĖJAU:
- SimpleHistoryAdmin vietoj admin.ModelAdmin
- Automatiškai atsirado "History" mygtukas
- Matomas kas, kada ir ką keitė

NAUDOJIMAS:
- Atidarykite Detale admin'e
- Viršuje dešinėje matote "History" mygtuką
- Spauskite ir matysite visus keitimus
"""

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin  # NAUJAS IMPORT
from .models import (
    Klientas,
    Projektas,
    Detale,
    DetaleSpecifikacija,
    PavirsiuDangos,
    Uzklausa,
    Kaina,
    Kainodara,
    KainosPartijai
)


# =====================================================================
# INLINE ADMIN'AI
# =====================================================================

class DetaleSpecifikacijaInline(admin.StackedInline):
    model = DetaleSpecifikacija
    extra = 0
    can_delete = True


class PavirsiuDangosInline(admin.StackedInline):
    model = PavirsiuDangos
    extra = 0
    can_delete = True


class KainaInline(admin.TabularInline):
    model = Kaina
    extra = 0
    readonly_fields = ('created', 'updated', 'pakeite')
    fields = (
        'suma', 'valiuta', 'kainos_matas',
        'yra_fiksuota', 'fiksuotas_kiekis',
        'kiekis_nuo', 'kiekis_iki',
        'galioja_nuo', 'galioja_iki', 'yra_aktuali',
        'keitimo_priezastis', 'pakeite'
    )


class KainosPartijaiInline(admin.TabularInline):
    model = KainosPartijai
    extra = 1


# =====================================================================
# MAIN ADMIN CLASSES
# =====================================================================

@admin.register(Klientas)
class KlientasAdmin(admin.ModelAdmin):
    list_display = ('vardas', 'created', 'updated')
    search_fields = ('vardas',)
    ordering = ('vardas',)


@admin.register(Projektas)
class ProjektasAdmin(admin.ModelAdmin):
    list_display = ('pavadinimas', 'klientas', 'uzklausos_data', 'created')
    list_filter = ('klientas', 'created')
    search_fields = ('pavadinimas', 'klientas__vardas')
    ordering = ('-created',)
    date_hierarchy = 'created'


@admin.register(Detale)
class DetaleAdmin(SimpleHistoryAdmin):  # PAKEISTA IŠ admin.ModelAdmin
    """
    Detale admin su istorijos palaikymu.
    Viršuje dešinėje matote "History" mygtuką.
    """
    list_display = (
        'pavadinimas',
        'brezinio_nr',
        'projektas',
        'kiekis_metinis',
        'created'
    )
    list_filter = ('projektas', 'created')
    search_fields = ('pavadinimas', 'brezinio_nr', 'projektas__pavadinimas')
    ordering = ('-created',)

    inlines = [DetaleSpecifikacijaInline, PavirsiuDangosInline]

    fieldsets = (
        ('Pagrindinė informacija', {
            'fields': ('projektas', 'pavadinimas', 'brezinio_nr')
        }),
        ('Nuorodos', {
            'fields': ('nuoroda_brezinio', 'nuoroda_pasiulymo'),
            'classes': ('collapse',)
        }),
        ('Kiekiai', {
            'fields': (
                'kiekis_metinis', 'kiekis_menesis',
                'kiekis_partijai', 'kiekis_per_val'
            ),
            'classes': ('collapse',)
        }),
        ('Matmenys', {
            'fields': (
                'ilgis_mm', 'plotis_mm', 'aukstis_mm',
                'skersmuo_mm', 'storis_mm'
            ),
            'classes': ('collapse',)
        }),
        ('Kabinimas', {
            'fields': (
                'kabinimo_budas', 'kabliuku_kiekis',
                'kabinimo_anga_mm', 'kabinti_per'
            ),
            'classes': ('collapse',)
        }),
        ('Pakuotė', {
            'fields': (
                'pakuotes_tipas', 'vienetai_dezeje',
                'vienetai_paleje', 'pakuotes_pastabos'
            ),
            'classes': ('collapse',)
        }),
        ('Testai ir dokumentai', {
            'fields': (
                'testai_druskos_rukas_val', 'testas_adhezija',
                'testas_storis_mikronai', 'testai_kita',
                'ppap_dokumentai', 'priedai_info'
            ),
            'classes': ('collapse',)
        }),
    )

    # Istorijos nustatymai
    history_list_display = ['changed_fields', 'history_user']

    def changed_fields(self, obj):
        """Rodo kurie laukai pasikeitė."""
        if obj.prev_record:
            delta = obj.diff_against(obj.prev_record)
            return ', '.join([change.field for change in delta.changes])
        return 'Sukurta'

    changed_fields.short_description = 'Pakeisti laukai'


@admin.register(Uzklausa)
class UzklausaAdmin(admin.ModelAdmin):
    list_display = ('id', 'klientas', 'projektas', 'detale', 'data', 'created')
    list_filter = ('klientas', 'data')
    search_fields = (
        'klientas__vardas',
        'projektas__pavadinimas',
        'detale__pavadinimas'
    )
    ordering = ('-created',)
    date_hierarchy = 'data'

    inlines = [KainaInline]

    fieldsets = (
        ('Užklausos informacija', {
            'fields': ('klientas', 'projektas', 'detale', 'pastabos')
        }),
        ('Laiko žymos', {
            'fields': ('data', 'created', 'updated'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created', 'updated')


@admin.register(Kaina)
class KainaAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'uzklausa',
        'detale',
        'suma',
        'valiuta',
        'yra_aktuali',
        'galioja_nuo',
        'galioja_iki',
        'pakeite'
    )
    list_filter = ('yra_aktuali', 'valiuta', 'galioja_nuo')
    search_fields = ('uzklausa__id', 'detale__pavadinimas')
    ordering = ('-galioja_nuo', '-id')
    date_hierarchy = 'galioja_nuo'

    fieldsets = (
        ('Ryšiai', {
            'fields': ('uzklausa', 'detale')
        }),
        ('Kaina', {
            'fields': ('suma', 'valiuta', 'kainos_matas')
        }),
        ('Kiekiai', {
            'fields': (
                'yra_fiksuota', 'fiksuotas_kiekis',
                'kiekis_nuo', 'kiekis_iki'
            ),
            'classes': ('collapse',)
        }),
        ('Galiojimas', {
            'fields': ('galioja_nuo', 'galioja_iki', 'yra_aktuali')
        }),
        ('Audit', {
            'fields': ('keitimo_priezastis', 'pakeite', 'created', 'updated'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created', 'updated', 'pakeite')

    def save_model(self, request, obj, form, change):
        """Automatiškai įrašo kas pakeitė kainą."""
        if not obj.pk or change:
            obj.pakeite = request.user
        super().save_model(request, obj, form, change)


@admin.register(Kainodara)
class KainodaraAdmin(admin.ModelAdmin):
    list_display = ('id', 'uzklausa', 'pavadinimas', 'created')
    list_filter = ('created',)
    search_fields = ('pavadinimas', 'uzklausa__id')
    ordering = ('-created',)

    inlines = [KainosPartijaiInline]


# DetaleSpecifikacija ir PavirsiuDangos registruojame tik jei reikia atskirai redaguoti
# Kitaip jie rodomi kaip inline'ai Detale admin'e
admin.site.register(DetaleSpecifikacija)
admin.site.register(PavirsiuDangos)