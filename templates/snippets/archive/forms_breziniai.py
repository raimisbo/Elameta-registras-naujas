# pozicijos/forms_breziniai.py
from django import forms
from pozicijos.models import PozicijosBrezinys


class PozicijosBrezinysForm(forms.ModelForm):
    class Meta:
        model = PozicijosBrezinys
        fields = ["failas", "pavadinimas"]
