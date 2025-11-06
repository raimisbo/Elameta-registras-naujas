from django.contrib import admin
from .models import Pozicija


@admin.register(Pozicija)
class PozicijaAdmin(admin.ModelAdmin):
    list_display = ("poz_kodas", "poz_pavad", "klientas", "projektas", "spalva", "kaina_eur", "updated")
    search_fields = ("poz_kodas", "poz_pavad", "klientas", "projektas", "spalva")
    list_filter = ("klientas", "projektas", "spalva")
    ordering = ("-updated",)
