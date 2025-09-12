from django.contrib import admin
from .models import Klientas, Projektas, Detale, Kaina, Uzklausa

class KlientasAdmin(admin.ModelAdmin):
    list_display = ('vardas', 'adresas', 'telefonas', 'el_pastas')

class ProjektasAdmin(admin.ModelAdmin):
    list_display = ('pavadinimas', 'uzklausos_data', 'pasiulymo_data')

class DetaleAdmin(admin.ModelAdmin):
    list_display = ('pavadinimas', 'plotas', 'svoris', 'kiekis_metinis', 'kiekis_menesis', 'kiekis_partijai', 'ppap_dokumentai')
    filter_horizontal = ('danga',)  # Pridedame daugiaslankstę dangų pasirinkimo galimybę

class KainaAdmin(admin.ModelAdmin):
    list_display = ('detalė', 'busena', 'suma', 'yra_fiksuota', 'kiekis_nuo', 'kiekis_iki', 'fiksuotas_kiekis', 'kainos_matas')

class UzklausaAdmin(admin.ModelAdmin):
    list_display = ('klientas', 'projektas', 'detale')

admin.site.register(Klientas, KlientasAdmin)
admin.site.register(Projektas, ProjektasAdmin)
admin.site.register(Detale, DetaleAdmin)
admin.site.register(Kaina, KainaAdmin)
admin.site.register(Uzklausa, UzklausaAdmin)
