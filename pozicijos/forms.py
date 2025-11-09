# pozicijos/forms.py
from django import forms
from django.forms import inlineformset_factory

from .models import Pozicija, PozicijosKaina


class PozicijaForm(forms.ModelForm):
    class Meta:
        model = Pozicija
        fields = [
            "klientas",
            "projektas",
            "poz_kodas",
            "poz_pavad",
            "metalas",
            "plotas",
            "svoris",
            "kabinimo_budas",
            "kabinimas_reme",
            "detaliu_kiekis_reme",
            "faktinis_kiekis_reme",
            "paruosimas",
            "padengimas",
            "padengimo_standartas",
            "spalva",
            "maskavimas",
            "atlikimo_terminas",
            "testai_kokybe",
            "pakavimas",
            "instrukcija",
            "pakavimo_dienos_norma",
            "pak_po_ktl",
            "pak_po_milt",
            "kaina_eur",
            "pastabos",
        ]


class PozicijosKainaForm(forms.ModelForm):
    class Meta:
        model = PozicijosKaina
        fields = [
            "suma",
            "kainos_matas",
            "busena",
            "yra_fiksuota",
            "kiekis_nuo",
            "kiekis_iki",
            "fiksuotas_kiekis",
        ]


PozicijosKainaFormSet = inlineformset_factory(
    Pozicija,
    PozicijosKaina,
    form=PozicijosKainaForm,
    extra=1,
    can_delete=True,
)
